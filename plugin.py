import serial, time, socket, signal, sys, threading, queue
import errno
import fcntl
import os
import select
import struct
import sys
import termios

class Plugin:
  FILTER = []
  PATHACV = "gps.anchorChainValue"
  CONFIG=[
    {
      'name': 'device',
      'description': 'set to the device path (alternative to usbid)',
      'default': '/dev/ttyUSB_SeatalkInp'
    },
    {
      'name': 'usbid',
      'description': 'set to the usbid of the device (alternative to device)',
      'default': ''
    },
    {
      'name': 'debuglevel',
      'description': 'set to the debuglevel',
      'default': '0'
    },
    {
      'name': 'circumference',
      'description': 'Define the circumference of anchor winch im [mm] (default: 30)',
      'default': '0.30'
    },
  ]
  @classmethod
  def pluginInfo(cls):
    """
    the description for the module
    @return: a dict with the content described below
            parts:
               * description (mandatory)
               * data: list of keys to be stored (optional)
                 * path - the key - see AVNApi.addData, all pathes starting with "gps." will be sent to the GUI
                 * description
    """
    return {
      'description': 'anchor chain pulse reader',
      'config': cls.CONFIG,
      'data': [
        {
          'path': cls.PATHACV,
          'description': 'anchor chain value',
        },
      ]
    }

  def __init__(self,api):
    """
        initialize a plugins
        do any checks here and throw an exception on error
        do not yet start any threads!
        @param api: the api to communicate with avnav
        @type  api: AVNApi
    """
    self.api = api # type: AVNApi
    #we register an handler for API requests
    self.lastReceived=0
    self.isConnected=False
    self.fd = None
    self.device=None
    self.debuglevel=None
    self.circumference=0.30
    self.anchorChainValue = 0.0
    self.isBusy=False
    self.condition=threading.Condition()
    if hasattr(self.api,'registerEditableParameters'):
      self.api.registerEditableParameters(self.CONFIG,self._changeConfig)
    if hasattr(self.api,'registerRestart'):
      self.api.registerRestart(self._apiRestart)
    self.changeSequence=0
    self.startSequence=0

    self.queue = queue.Queue()

  def _apiRestart(self):
    self.startSequence+=1
    self.changeSequence+=1

  def _changeConfig(self,newValues):
    self.api.saveConfigValues(newValues)
    self.changeSequence+=1

  def getConfigValue(self,name):
    defaults=self.pluginInfo()['config']
    for cf in defaults:
      if cf['name'] == name:
        return self.api.getConfigValue(name,cf.get('default'))
    return self.api.getConfigValue(name)

  def run(self):
    startSequence=self.startSequence
    while startSequence == self.startSequence:
      try:
        #only AvNav after 20210224
        self.api.deregisterUsbHandler()
      except:
        pass
      self.runInternal()

  def runInternal(self):
    """
    the run method
    this will be called after successfully instantiating an instance
    this method will be called in a separate Thread
    The plugin sends every 10 seconds the depth value via seatalk
    @return:
    """
    changeSequence=self.changeSequence
    seq=0
    self.api.log("started")
    self.api.setStatus('STARTED', 'running')
    enabled=self.getConfigValue('enabled')
    if enabled is not None and enabled.lower()!='true':
      self.api.setStatus("INACTIVE", "disabled by config")
      return
    usbid=None
    try:
      self.device=self.getConfigValue('device')
      self.debuglevel=self.getConfigValue('debuglevel')
      usbid=self.getConfigValue('usbid')
      if usbid == '':
        usbid=None
      if self.device == '':
        self.device=None
      if self.device is None and usbid is None:
        raise Exception("missing config value device or usbid")

      if self.device is not None and usbid is not None:
        raise Exception("only one of device or usbid can be set")
    except Exception as e:
      self.api.setStatus("ERROR", "config error %s "%str(e))
      while changeSequence == self.changeSequence:
        time.sleep(0.5)
      return
    if usbid is not None:
      self.api.registerUsbHandler(usbid,self.deviceConnected)
      self.api.setStatus("STARTED", "using usbid %s, baud=4800" % (usbid))
    else:
      self.api.setStatus("STARTED","using device %s, baud=4800"%(self.device))
    connectionHandler=threading.Thread(target=self.handleConnection, name='seatalk-remote-connection')
    connectionHandler.setDaemon(True)
    connectionHandler.start()

    lastAnchorChainValue = -1.0

    while changeSequence == self.changeSequence:
      #if not self.isConnected:
        #return {'status': 'not connected'}
      source='internal'

      try:
        if (lastAnchorChainValue != self.anchorChainValue):
          self.api.addData(self.PATHACV, self.anchorChainValue, source=source)
        lastAnchorChainValue = self.anchorChainValue

      except Exception as e:
        self.anchorChainValue = 0.0
        self.api.addData(self.PATHACV, self.anchorChainValue, source=source)
        pass

      time.sleep(0.2)

  def handleConnection(self):
    changeSequence=self.changeSequence
    errorReported=False
    lastDevice=None
    while changeSequence == self.changeSequence:
      if self.device is not None:
        if self.device != lastDevice:
          self.api.setStatus("STARTED", "trying to connect to %s at 4800" % (self.device))
          lastDevice=self.device
        #on windows we would need an integer as device...
        try:
          pnum = int(self.device)
        except:
          pnum = self.device
        self.isConnected=False
        self.isBusy=False
        try:
          self.fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)

          self.api.setStatus("NMEA","connected to %s at 4800"%(self.device))
          self.api.log("connected to %s at 4800" % (self.device))
          self.isConnected=True
          errorReported=False

          p = struct.pack('I', 0)
          lastFlags = fcntl.ioctl(self.fd, termios.TIOCMGET, p)
          lastFlags = struct.unpack('I', lastFlags)[0]
          penalty = 0


          while True:
            p = struct.pack('I', 0)
            flags = fcntl.ioctl(self.fd, termios.TIOCMGET, p)
            flags = struct.unpack('I', flags)[0]

            if ( flags & termios.TIOCM_DSR ):
              if ( (lastFlags & termios.TIOCM_DSR) == 0):
                  # 250 ms panalty (50*0.005) 
                if(int(self.debuglevel) > 0):
                  self.api.log("DSR rising edge")
                if ( flags & termios.TIOCM_CTS ):
                  self.anchorChainValue += float(self.circumference)
                else:
                  self.anchorChainValue -= float(self.circumference)
                  if (self.anchorChainValue < 0):
                    self.anchorChainValue = 0

            lastFlags = flags

            time.sleep(0.005)

        except Exception as e:
          if not errorReported:
            self.api.setStatus("ERROR","unable to connect/connection lost to %s: %s"%(self.device, str(e)))
            self.api.error("unable to connect/connection lost to %s: %s" % (self.device, str(e)))
            errorReported=True
          self.isConnected=False
          time.sleep(1)
      time.sleep(1)
