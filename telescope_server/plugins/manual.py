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
import numpy as np

# First party
from telescope_server.gpio import GPIO


class Manual(object):
    def __init__(self, controller):
        self.controller = controller
        self._pins_args = {
            # define the gpio pins and arguments for controller call
            22: (0, False),  # left
            27: (0, True),  # right
            11: (1, False),  # up
            9: (1, True),  # down
        }
        self._pins = list(self._pins_args.keys())
        self._set_angle_pin = 10

        # motor control
        for pin in list(self._pins_args.keys()):
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        # set object angle control
        GPIO.setup(self._set_angle_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # start two threads
        _thread.start_new_thread(self._motor_control, ())
        _thread.start_new_thread(self._set_angle, ())

    def _motor_control(self):
        # start and stop motors depending on button press
        running = np.zeros(4, dtype=np.int)
        while True:
            current = np.array([GPIO.input(pin) for pin in self._pins])
            change = np.where(np.logical_xor(current, running))[0]
            if len(change):
                for index in change:
                    motor, direction = self._pins_args[self._pins[index]]
                    self.controller.start_stop_motor(motor, False, True)
                    if current[index]:
                        logging.debug(
                            "manual start stop motor/direction: %s / %s",
                            motor,
                            direction,
                        )
                        self.controller.start_stop_motor(motor, True, direction)
                running = current
            sleep(0.05)

    def _set_angle(self):
        # set the angle for the object selected by the gui-client
        while True:
            GPIO.wait_for_edge(self._set_angle_pin, GPIO.FALLING)
            logging.debug("manual calibration")
            self.controller.apply_object()
            sleep(0.5)
