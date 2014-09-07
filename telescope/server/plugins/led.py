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
    def __init__(self):
        self.status_pin = 2
        self._blink_delay = 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.status_pin, GPIO.OUT)
        thread.start_new_thread(self._blinking, ())

    def _blinking(self):
        # running forever with the current blink rate
        while True:
            GPIO.output(self.status_pin, False)
            print "on"
            sleep(self._blink_delay)
            print "off"
            GPIO.output(self.status_pin, True)        
            sleep(self._blink_delay)

    @property
    def blink_delay(self):
        return self._blink_delay

    @blink_delay.setter
    def blink_delay(self, delay):
        self._blink_delay = delay
