# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to handle a led
"""

import thread
from time import sleep
from telescope.server.gpio import GPIO

class Led(object):
    def __init__(self, controller):
        self.controller = controller
        self.status_pin = 2
        self._blink_delay = 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.status_pin, GPIO.OUT)
        thread.start_new_thread(self._blinking, ())
        thread.start_new_thread(self._check_tracking, ())

    def _blinking(self):
        # running forever with the current blink rate
        while True:
            GPIO.output(self.status_pin, False)
            sleep(self._blink_delay)
            GPIO.output(self.status_pin, True)        
            sleep(self._blink_delay)

    def _check_tracking(self):
        # check if object is tracked and adjust blinking speed
        while True:
            try:
                if self.controller._is_tracking:
                    self._blink_delay = .5
                else:
                    self._blink_delay = 1
            except:
                self._blink_delay = 3
            sleep(3)

    @property
    def blink_delay(self):
        return self._blink_delay

    @blink_delay.setter
    def blink_delay(self, delay):
        self._blink_delay = delay
