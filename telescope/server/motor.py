# -*- encoding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

import time
import logging
from math import cos, pi, pow

from gpio import GPIO

class Motor(object):

    def __init__(self, name, pins, min_angle=-5, max_angle=365,
                 positive=1, vend=10000, vstart=20, skewness=.75, accel_steps=4000):
        def _accel_velocity(x):
            """
            calculate the acceleration/deceleration velocity in the interval [0,1]
            """
            return (.5-.5*cos(x*pi))*(vend-vstart)+vstart
            
        def _accel_skewing(x):
            """
            skew the velocity cosine by a parabolic function
            """
            return pow(x, skewness)/pow(accel_steps, skewness)

        self.name = name
        self.PUL, self.DIR, self.ENBL = pins
        self._steps_per_rev = 0
        self._enabled = True
        self._angle = 0
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._steps = 0
        self._stop = True
        self._delay = 1./vend
        self._positive = positive
        for p in pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, False)

        self._accel_curve = [ 1./_accel_velocity(_accel_skewing(x)) \
                              for x in xrange(accel_steps) ]

    def __str__(self):
        return self.name

    @property
    def steps_per_rev(self):
        return self._steps_per_rev

    @steps_per_rev.setter
    def steps_per_rev(self, value):
        self._steps_per_rev = value
        try:
            self._minimum = self._min_angle + 360./value
            self._maximum = self._max_angle - 360./value
        except:
            pass

    @property
    def enable(self):
        return self._enabled

    @enable.setter
    def enable(self, enabled=True):
        self._enabled = enabled
        GPIO.output(self.ENBL, enabled)

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        value %= 360
        if self._min_angle <= value <= self._max_angle:
            self._angle = value

    @property
    def steps(self):
        return self._steps

    @steps.setter
    def steps(self, value):
        self._steps = value


    @property
    def calibrated(self):
        return self._steps_per_rev > 0

    @property
    def stop(self):
        return self._stop

    @stop.setter
    def stop(self, value):
        self._stop = value

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, value):
        self._delay = value

    def step(self, steps, direction):
        if steps:
            delay = 0
            logging.debug("INPUT -- %s: actual_step/steps/direction: %d / %d / %d",
                          self.name, self._steps, steps, direction)
            self._stop = False
            GPIO.output(self.DIR, direction)
            for step in xrange(steps):
                try:
                    step_delay = self._accel_curve[min(step, abs(step-(steps-1)))]
                except:
                    step_delay = self._delay

                if self._stop or \
                   (self._angle <= self._minimum and not direction) or \
                   (self._angle >= self._maximum and direction):
                    logging.debug("BREAK -- %s: actual_step/steps/direction: %d / %d / %d",
                                  self.name, self._steps, steps, direction)
                    return
                    
                GPIO.output(self.PUL, True)
                GPIO.output(self.PUL, False)
                self._steps += 2*(direction-.5)*self._positive
                if self._steps_per_rev > 0:
                    self._angle += (direction-.5)*(self._positive*720./self._steps_per_rev)
                    self._angle %= 360
                time.sleep(step_delay)
            logging.debug("END -- %s: actual_step/steps/direction: %d / %d / %d",
                          self.name, self._steps, steps, direction)
         
    def move(self, angle):
        angle = angle % 360
        if (self._steps_per_rev > 0) and self._enabled:
            angle_to_move = (angle - self._angle) % 360
            if angle_to_move > 180:
                angle_to_move = - (360.-angle_to_move)
            steps = self._steps_per_rev * angle_to_move / 360.
            self.step(int(abs(round(steps))), self._positive*steps>0)

