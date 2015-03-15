# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to handle a led
"""
import socket
import fcntl
import struct
import thread
from time import sleep
from telescope.server.gpio import GPIO

import logging

class Led(object):
    def __init__(self, controller):
        self.controller = controller
        self.status_pin = 2
        self._blink_delay = 5
        GPIO.setup(self.status_pin, GPIO.OUT)
        thread.start_new_thread(self._blinking, ())
        thread.start_new_thread(self._check_status, ())

    def _blinking(self):
        # running forever with the current blink rate
        while True:
            GPIO.output(self.status_pin, False)
            sleep(self._blink_delay)
            GPIO.output(self.status_pin, True)        
            sleep(self._blink_delay)

    def _check_status(self):
        # check if some client is connected and if so
        # check if object is tracked and adjust blinking speed
        while True:
            logging.debug("blink rate: %f", self._blink_delay)
            try:
                if self.controller._is_tracking:
                     self._blink_delay = .5
                elif not self.controller.client_connected:
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        ipnummer=socket.inet_ntoa(fcntl.ioctl(
                            s.fileno(),
                            0x8915,  # SIOCGIFADDR
                            struct.pack('256s', 'wlan0'[:15])
                            )[20:24])
                        self._blink_delay = 1
                    except:
                        self._blink_delay =.125
                else:
                    self._blink_delay = 2
            except:
                self._blink_delay = 5 
            sleep(2)

    @property
    def blink_delay(self):
        return self._blink_delay

    @blink_delay.setter
    def blink_delay(self, delay):
        self._blink_delay = delay
