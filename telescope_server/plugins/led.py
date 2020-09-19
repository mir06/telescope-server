# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to handle a led
"""
# Standard Library
import _thread
import fcntl
import logging
import socket
import struct

from time import sleep

# Third party
from gpiozero import LED


class Led(object):
    def __init__(self, controller):
        self.controller = controller
        self.logger = logging.getLogger(__name__)
        self.status_pin = 2
        self._blink_delayshort = 5
        self._blink_delaylong = 5
        self.led = LED(2)

        _thread.start_new_thread(self._blinking, ())
        _thread.start_new_thread(self._check_status, ())

    def _blinking(self):
        # running forever with the current blink rate
        while True:
            self.led.off()
            sleep(self._blink_delayshort)
            self.led.on()
            sleep(self._blink_delayshort)
            self.led.off()
            sleep(self._blink_delayshort)
            self.led.on()
            sleep(self._blink_delayshort)
            self.led.off()
            sleep(self._blink_delaylong)
            self.led.on()
            sleep(self._blink_delaylong)

    def _check_status(self):
        # check if some client is connected and if so
        # check if object is tracked and adjust blinking speed
        self.logger.debug(
            "blink rate: %f / %f", self._blink_delayshort, self._blink_delaylong
        )
        while True:
            self.logger.debug(
                "blink rate: %f / %f", self._blink_delayshort, self._blink_delaylong
            )
            try:
                if self.controller._is_tracking:
                    self._blink_delayshort = 0.125
                    self._blink_delaylong = 0.5
                elif self.controller.is_motor_on:
                    self._blink_delayshort = 0.125
                    self._blink_delaylong = 0.125
                elif not self.controller.client_connected:
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        ipnummer = socket.inet_ntoa(
                            fcntl.ioctl(
                                s.fileno(),
                                0x8915,  # SIOCGIFADDR
                                struct.pack("256s", "wlan0"[:15]),
                            )[20:24]
                        )
                        self.logger.debug(f"ipnummer {ipnummer}")
                        self._blink_delayshort = 1
                        self._blink_delaylong = 1
                    except Exception:
                        self._blink_delayshort = 1.5
                        self._blink_delaylong = 3
                else:
                    self._blink_delayshort = 0.5
                    self._blink_delaylong = 0.5
            except Exception:
                self._blink_delayshort = 3
                self._blink_delaylong = 3
            self.logger.debug(
                "blink rate: %f / %f", self._blink_delayshort, self._blink_delaylong
            )
            sleep(2)

    @property
    def blink_delayshort(self):
        return self._blink_delayshort

    @blink_delayshort.setter
    def blink_delayshort(self, delayshort):
        self._blink_delayshort = delayshort

    @property
    def blink_delaylong(self):
        return self._blink_delaylong

    @blink_delaylong.setter
    def blink_delaylong(self, delaylong):
        self._blink_delaylong = delaylong
