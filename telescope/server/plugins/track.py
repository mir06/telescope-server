# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to toggle tracking
"""
import thread
from telescope.server.gpio import GPIO

class Track(object):
    def __init__(self, controller):
        self._track_pin = 17
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._track_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        thread.start_new_thread(self._toggle_track, ())

    def _toggle_track(self):
        """
        that's the callback function that toggles tracking
        """
        while True:
            GPIO.wait_for_edge(self._track_pin, GPIO.FALLING)
            self.controller.toggle_tracking()
            sleep(.5)
