# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to handle a the manual control
"""

# Standard Library
import _thread
import logging

from time import sleep

# Third party
from gpiozero import Button


class Manual(object):
    def __init__(self, controller):
        self.controller = controller
        self.logger = logging.getLogger(__name__)

        # motor control
        self.left = Button(22, pull_up=False)
        self.right = Button(27, pull_up=False)
        self.up = Button(11, pull_up=False)
        self.down = Button(9, pull_up=False)

        self.motor_control = {0: (self.right, self.left), 1: (self.down, self.up)}

        self.set_angle = Button(10)

        # start two threads
        _thread.start_new_thread(self._motor_control, ())
        _thread.start_new_thread(self._set_angle, ())

    def _motor_control(self):
        def _get_current(b1, b2):
            """
            Check which of the two given buttons are pressed

            Returns:

                A tuple of two booleans; the first indicates if motors shall
                run, the second is the direction (True for the first, False
                if second button is pressed)
            """
            running = b1.is_pressed != b2.is_pressed
            direction = None
            if running:
                direction = b1.is_pressed
            return (running, direction)

        # start and stop motors depending on button press
        current = {0: (False, None), 1: (False, None)}
        while True:
            for motor, buttons in self.motor_control.items():
                c = _get_current(*buttons)
                if c != current[motor]:
                    # stop and eventually start in the opposite direction
                    current[motor] = c
                    self.controller.start_stop_motor(motor, False, True)
                    self.logger.debug(f"stop motor {motor}")
                    if c[0]:
                        self.controller.start_stop_motor(motor, True, c[1])
                        self.logger.debug(f"start in direction {c[1]}")

            sleep(0.05)

    def _set_angle(self):
        # set the angle for the object selected by the gui-client
        while True:
            self.set_angle.wait_for_press()
            self.logger.debug("manual calibration")
            self.controller.apply_object()
            sleep(0.5)
