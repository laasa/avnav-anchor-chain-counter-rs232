# avnav-anchor-chain-counter-rs232
counts the anchor chain pulses via inputs DSR and CTS on serial line

![grafik](https://user-images.githubusercontent.com/98450191/153689785-2802730f-096a-490d-aaaf-1e5c5fca7244.png)

# General

The plugin reads pulses from a reed relais on the anchor winch.
Addtionally it need the Up/Down information anchor winch relais.

It is widely based on the
- seatalk remote plugin (https://github.com/wellenvogel/avnav-seatalk-remote-plugin),
- more nmea plugin      (https://github.com/kdschmidt1/avnav-more-nmea-plugin) and
- Seatalk1 to NMEA 0183 (https://github.com/MatsA/seatalk1-to-NMEA0183/blob/master/STALK_read.py).

# Parameter

- device: e.g. '/dev/ttyUSB0'
- usbid: as alternative for devive name
- circumference: circumference of anchor winch
- debuglevel: debug level

# Details

# Hardware needs
It is recommended to use optocoupler between board voltage level and RS232.

An example for such an circuit is suggested here: https://pysselilivet.blogspot.com/2020/06/seatalk1-to-nmea-0183-converter-diy.html

First tests are made with th module BUCCK_817_4_V1.0.
![grafik](https://user-images.githubusercontent.com/98450191/153611941-e6ed298a-06d5-4a33-b4ed-b8fbda8201ec.png)

The reed relais is a brought one:
![grafik](https://user-images.githubusercontent.com/98450191/153611712-e395b9f1-18e5-4b43-8a93-baecb4d1e036.png)

# Software installation

To install this plugin please 
- create directory '/usr/lib/avnav/plugins/avnav-anchor-chain-counter-rs232' and 
- copy the file plugin.py to this directory.

# Using in anvav

![grafik](https://user-images.githubusercontent.com/98450191/153686644-1ca811d5-7fd9-44b8-9f00-423363ef2640.png)

# TODOs
- only tested with linux

# Helpers
Setup the serial devices by their serial numbers
- Label your first USB serial device (e.g SeatalkOut)
- Connect the first USB serial device to the PC
- Get the vendorID, deviceID and serial number of the tty device (here "/dev/ttyUSB0")
   udevadm info -a -n /dev/ttyUSB0 | grep {idVendor} | head -n1  => ATTRS{idVendor}=="0403" 
   udevadm info -a -n /dev/ttyUSB0 | grep {bcdDevice} | head -n1 => ATTRS{bcdDevice}=="0600"
   udevadm info -a -n /dev/ttyUSB0 | grep {serial} | head -n1    => ATTRS{serial}=="A10KKBM3"
- creates an udev rule
  mcedit sudo mcedit /etc/udev/rules.d/10-local.rules
   SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A10KKBM3", MODE="0666", SYMLINK+="ttyUSB_SeatalkOut"
- Continue with the next devices
- at the end the file /etc/udev/rules.d/10-local.rules may look like that
    SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A10KKF9V", MODE="0666", SYMLINK+="ttyUSB_SeatalkInp"
    SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A10KKBM3", MODE="0666", SYMLINK+="ttyUSB_SeatalkOut"
- Use this names in avnav (e.g: "/dev/ttyUSB_SeatalkInp")
