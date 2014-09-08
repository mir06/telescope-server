# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
plugin to handle a the manual control
"""

from telescope.server.gpio import GPIO

class Manual(object):
    def __init__(self, controller):
        self.controller = controller
        self._motor_pins_dirs = {
            # define the gpio-pins and arguments for controller call
            'left': (22, 0, True),
            'right': (27, 0, False),
            'up': (9, 1, True),
            'down': (11, 1, False),
        }
        self._set_angle_pin = 10
        GPIO.setmode(GPIO.BCM)
        for name, pin in self._motor_pins_dirs.iteritems():
            GPIO.setup(pin[0], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.add_event_detect(pin[0], GPIO.RISING, 
                                  callback=lambda x: self._start(x), bouncetime=100)    
            GPIO.add_event_detect(pin[0], GPIO.FALLING, 
                                  callback=lambda x: self._stop(x), bouncetime=100)    
        GPIO.setup(self._set_angle_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(self._set_angle_pin, GPIO.RISING, 
                              callback=self._set_angle, bouncetime=500)

    def _start(self, what):
        # start the motor
        self.controller._start_motor(self._motor_pins_dirs[what][1], self._motor_pins_dirs[what][2])

    def _stop(self, what):
        # stop the motor
        self.controller._stop_motors([self._motor_pins_dirs[what][1]])

    def _set_angle(self):
        # set the angle for the object selected by the gui-client
        self.controller.apply_object()
