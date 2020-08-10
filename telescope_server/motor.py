# -*- encoding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

# Standard Library
import logging
import time

from math import cos, pi, pow

# Local imports
from .gpio import GPIO


class Motor(object):
    def __init__(
        self,
        name,
        pins,
        min_angle=-5,
        max_angle=365,
        positive=1,
        vend=4500,
        vstart=20,
        skewness=0.75,
        # accel_steps=4000,
        accel_steps=500,
        skewnessbra=0.9,
        bra_steps=500,
    ):
        def _accel_velocity(x):
            """
            calculate the acceleration/deceleration velocity in the interval [0,1]
            """
            return (0.5 - 0.5 * cos(x * pi)) * (vend - vstart) + vstart

        def _accel_skewing(x):
            """
            skew the velocity cosine by a parabolic function
            """
            return pow(x, skewness) / pow(accel_steps, skewness)

        def _bra_skewing(x):
            """
            skew the velocity cosine by a parabolic function
            """
            return pow(x, skewnessbra) / pow(bra_steps, skewnessbra)

        self.name = name
        self.PUL, self.DIR, self.ENBL = pins
        self._steps_per_rev = 0
        self._enabled = True
        self._angle = 0
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._steps = 0
        self._stop = True
        self._delay = 1.0 / vend
        self._positive = positive
        self._brake_steps = accel_steps
        for p in pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, False)

        self._accel_curve = [
            1.0 / _accel_velocity(_accel_skewing(x)) for x in range(accel_steps)
        ]
        # self._accel_curve = np.linspace(.05, 1./vend, bra_steps)
        self._bra_curve = [
            1.0 / _accel_velocity(_bra_skewing(x)) for x in range(bra_steps)
        ]
        # self._bra_curve = np.linspace(.05, 1./vend, bra_steps)

    def __str__(self):
        return self.name

    @property
    def steps_per_rev(self):
        return self._steps_per_rev

    @steps_per_rev.setter
    def steps_per_rev(self, value):
        self._steps_per_rev = value
        try:
            self._minimum = self._min_angle + 360.0 / value * self._brake_steps
            self._maximum = self._max_angle - 360.0 / value * self._brake_steps
        except Exception:
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

    def brake(self, current_delay, direction):
        self._stop = False
        accel_index = min(
            list(range(len(self._bra_curve))),
            key=lambda i: abs(self._bra_curve[i] - current_delay),
        )
        logging.debug("braking down within %d steps", accel_index)
        for step in range(accel_index):
            step_delay = self._bra_curve[accel_index - step]
            GPIO.output(self.PUL, True)
            GPIO.output(self.PUL, False)
            self._steps += 2 * (direction - 0.5) * self._positive
            if self._steps_per_rev > 0:
                self._angle += (direction - 0.5) * (
                    self._positive * 720.0 / self._steps_per_rev
                )
                self._angle %= 360
            time.sleep(step_delay)
        self.step(accel_index, not direction)
        self._stop = True

    def step(self, steps, direction):
        if steps:
            logging.debug(
                "INPUT -- %s: actual_step/steps/direction: %d / %d / %d",
                self.name,
                self._steps,
                steps,
                direction,
            )
            self._stop = False
            GPIO.output(self.DIR, direction)
            for step in range(steps):
                try:
                    step_delay = self._accel_curve[min(step, abs(step - (steps - 1)))]
                except Exception:
                    step_delay = self._delay

                if (
                    self._stop
                    or (self._angle <= self._minimum and not direction)
                    or (self._angle >= self._maximum and direction)
                ):
                    logging.debug(
                        "BREAK -- %s: actual_step/steps/direction: %d / %d / %d",
                        self.name,
                        self._steps,
                        steps,
                        direction,
                    )
                    self.brake(step_delay, direction)
                    break

                GPIO.output(self.PUL, True)
                GPIO.output(self.PUL, False)
                self._steps += 2 * (direction - 0.5) * self._positive
                if self._steps_per_rev > 0:
                    self._angle += (direction - 0.5) * (
                        self._positive * 720.0 / self._steps_per_rev
                    )
                    self._angle %= 360
                time.sleep(step_delay)
            logging.debug(
                "END -- %s: actual_step/steps/direction: %d / %d / %d",
                self.name,
                self._steps,
                steps,
                direction,
            )

    def move(self, angle):
        angle = angle % 360
        if (self._steps_per_rev > 0) and self._enabled:
            angle_to_move = (angle - self._angle) % 360
            if angle_to_move > 180:
                angle_to_move = -(360.0 - angle_to_move)
            steps = self._steps_per_rev * angle_to_move / 360.0
            self.step(int(abs(round(steps))), self._positive * steps > 0)
