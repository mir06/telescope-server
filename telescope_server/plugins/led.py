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

# First party
from telescope_server.gpio import GPIO


class Led(object):
    def __init__(self, controller):
        self.controller = controller
        self.logger = logging.getLogger(__name__)
        self.status_pin = 2
        self._blink_delayshort = 5
        self._blink_delaylongt = 5
        GPIO.setup(self.status_pin, GPIO.OUT)
        _thread.start_new_thread(self._blinking, ())
        _thread.start_new_thread(self._check_status, ())

    def _blinking(self):
        # running forever with the current blink rate
        while True:
            GPIO.output(self.status_pin, False)
            sleep(self._blink_delayshort)
            GPIO.output(self.status_pin, True)
            sleep(self._blink_delayshort)
            GPIO.output(self.status_pin, False)
            sleep(self._blink_delayshort)
            GPIO.output(self.status_pin, True)
            sleep(self._blink_delayshort)
            GPIO.output(self.status_pin, False)
            sleep(self._blink_delaylongt)
            GPIO.output(self.status_pin, True)
            sleep(self._blink_delaylongt)

    def _check_status(self):
        # check if some client is connected and if so
        # check if object is tracked and adjust blinking speed
        self.logger.debug(
            "blink rate: %f / %f", self._blink_delayshort, self._blink_delaylongt
        )
        while True:
            self.logger.debug(
                "blink rate: %f / %f", self._blink_delayshort, self._blink_delaylongt
            )
            try:
                try:
                    self.logger.debug("tracking: %s ", self.controller._is_tracking)
                    self.logger.debug("motor on: %s", self.controller.is_motor_on)
                    self.logger.debug(
                        "client connected %s", self.controller.client_connected
                    )
                except Exception as e:
                    self.logger.debug("Exeption: %s", e)
                if self.controller._is_tracking:
                    self._blink_delayshort = 0.125
                    self._blink_delaylongt = 0.5
                elif self.controller.is_motor_on:
                    self._blink_delayshort = 0.125
                    self._blink_delaylongt = 0.125
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
                        self._blink_delaylongt = 1
                    except Exception:
                        self._blink_delayshort = 1.5
                        self._blink_delaylongt = 3
                else:
                    self._blink_delayshort = 0.5
                    self._blink_delaylongt = 0.5
            except Exception:
                self._blink_delayshort = 3
                self._blink_delaylongt = 3
            self.logger.debug(
                "blink rate: %f / %f", self._blink_delayshort, self._blink_delaylongt
            )
            sleep(2)

    @property
    def blink_delayshort(self):
        return self._blink_delayshort

    @blink_delayshort.setter
    def blink_delayshort(self, delayshort):
        self._blink_delayshort = delayshort

    @property
    def blink_delaylongt(self):
        return self._blink_delaylongt

    @blink_delaylongt.setter
    def blink_delaylongt(self, delaylongt):
        self._blink_delaylongt = delaylongt
