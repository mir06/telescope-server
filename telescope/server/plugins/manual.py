# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to handle a the manual control
"""

from time import sleep
from telescope.server.gpio import GPIO

class Manual(object):
    def __init__(self, controller):
        self.controller = controller
	self._pins_args = {
	    # define the gpio pins and arguments for controller call
	    22: (0, True),     # left
	    27: (0, False),    # right
	     9: (1, True),     # up
   	    11: (1, False),    # down
	}
	self._set_angle_pin = 10
	GPIO.setmode(GPIO.BCM)
	# motor control
	for pin in self._pins_args.keys():
	    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	    GPIO.add_event_detect(pin, GPIO.BOTH, self._action, bouncetime=100)

	# set object angle control
	GPIO.setup(self._set_angle_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	GPIO.add_event_detect(self._set_angle_pin, GPIO.RISING,
			      callback=self._set_angle, bouncetime=250)

    def _action(self, pin):
        # start or stop the motor
        motor, direction = self._pins_args[pin]
        # to be sure about the input signal wait a little longer
        # than the bouncing time is
        sleep(.1)
        if GPIO.input(pin):
            self.controller._start_motor(motor, direction)
            logging.info("start motor by manual control")
        else:
            self.controller._stop_motors([motor])
            logging.info("stop motor by manual control")

    def _set_angle(self, pin):
        # set the angle for the object selected by the gui-client
        self.controller.apply_object()
