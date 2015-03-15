# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to halt raspberry pi on button press
"""

import subprocess
from telescope.server.gpio import GPIO

class Halt(object):
    def __init__(self, controller):
        halt_pin = 4
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(halt_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(halt_pin, GPIO.RISING, callback=self._halt, bouncetime=500)

    def _halt(self, channel):
        """
        that's the callback function that actually halts the raspberry pi
        """
        subprocess.call(['halt'], shell=True)
