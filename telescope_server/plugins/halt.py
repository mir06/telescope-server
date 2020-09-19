# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to halt raspberry pi on button press
"""

# Standard Library
import subprocess

# Third party
from gpiozero import Button


class Halt(object):
    def __init__(self, controller):
        halt_pin = 4
        self.button = Button(halt_pin, bouncetime=0.5)
        self.button.when_released = self._halt

    def _halt(self, channel):
        """
        that's the callback function that actually halts the raspberry pi
        """
        subprocess.run(["sudo", "poweroff"])
