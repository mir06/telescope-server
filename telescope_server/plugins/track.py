# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to toggle tracking
"""
# Standard Library
import _thread
import logging

from time import sleep

# Third party
from gpiozero import Button


class Track(object):
    def __init__(self, controller):
        self.controller = controller
        self.logger = logging.getLogger(__name__)
        track_pin = 17
        self.button = Button(track_pin)
        _thread.start_new_thread(self._toggle_track, ())

    def _toggle_track(self):
        """
        that's the callback function that toggles tracking
        """
        while True:
            self.button.wait_for_press()
            self.logger.debug("toggle tracking")
            self.controller.toggle_tracking()
            sleep(0.5)
