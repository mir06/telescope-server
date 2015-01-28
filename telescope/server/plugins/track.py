# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to toggle tracking
"""

from telescope.server.gpio import GPIO

class Track(object):
    def __init__(self, controller):
        track_pin = 17
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(track_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(track_pin, GPIO.RISING, callback=self._toggle_track, bouncetime=500)

    def _toggle_track(self, channel):
        """
        that's the callback function that toggles tracking
        """
        self.controller.toggle_tracking()
