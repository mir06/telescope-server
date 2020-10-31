# -*- encoding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

# Standard Library
import logging

from datetime import datetime
from itertools import combinations
from statistics import median
from sys import maxsize
from threading import Thread, Timer
from time import sleep

# Third party
import ephem
import ephem.stars

# First party
from telescope_server.protocol import status

# Local imports
from .basecontroller import BaseController
from .motor import Motor


class Controller(BaseController):
    """
    this class implements the telescope control by two motors
    for the azimuthal and altitudinal rotation

    the motors are connected to the stepper motor driver DM420
    and controlled via GPIO on a raspberry pi (Motor class)
    """

    az_pins = [15, 14, 8]
    alt_pins = [23, 18, 7]

    def __init__(self):

        self.logger = logging.getLogger(__name__)

        # initialize the motors
        self.motors = [
            Motor("Azimuth", self.az_pins, positive=1),
            Motor("Altitude", self.alt_pins, positive=-1),
        ]

        # initialize observer and target
        self._observer = ephem.Observer()
        self._target = ephem.FixedBody()

        # insteresting objects in our solar system and main stars
        self._sky_objects = [
            ephem.Sun(),
            ephem.Moon(),
            ephem.Mercury(),
            ephem.Venus(),
            ephem.Mars(),
            ephem.Jupiter(),
            ephem.Saturn(),
        ]
        for star in sorted([x.split(",")[0] for x in ephem.stars.db.split("\n") if x]):
            self._sky_objects.append(ephem.star(star))

        # set boolean variable indicating tracking
        self._is_tracking = False
        self.restart = [False, False]
        self.running = [False, False]

        # initialize angles/steps lists for calibration
        self._angles_steps = [[], []]

        # initialize motor threads
        self._motor_threads = [None, None]

        az_default_spr = 1293009
        alt_default_spr = 1560660

        self.motors[0].steps_per_rev = az_default_spr
        self.motors[1].steps_per_rev = alt_default_spr

        # at startup no client is connected
        self._client_connected = False

    @property
    def location(self):
        return "%s / %s / %s" % (
            self._observer.lon,
            self._observer.lat,
            self._observer.elev,
        )

    @property
    def target(self):
        try:
            return "%s / %s" % (self._target._ra, self._target._dec)
        except Exception:
            return "no target selected"

    @property
    def azimuth(self):
        return ephem.degrees("%f" % self.motors[0].angle)

    @property
    def altitude(self):
        return ephem.degrees("%f" % self.motors[1].angle)

    @property
    def calibrated(self):
        return all([m.calibrated for m in self.motors])

    @property
    def is_tracking(self):
        return self._is_tracking()

    @property
    def is_motor_on(self):
        try:
            for t in self._motor_threads:
                self.logger.debug("on motor thread %s", t)
                if (t is not None) and t.isAlive():
                    self.logger.debug("isaliver %s", t)
                    return True
            self.logger.debug("isnotaliver %s", t)
            return False
        except Exception:
            self.logger.debug("isnotaliverexeption")
            return False

    @property
    def client_connected(self):
        return self._client_connected

    def _set_step_delay(self, motor_index, delay):
        """
        set the delay between motor steps
        """
        self.motors[motor_index].delay = delay

    def _start_motor(self, motor_index, direction):
        """
        start a motor with a given direction and infinite steps
        """
        self.logger.debug("start %s motor", self.motors[motor_index].name)
        try:
            self._motor_threads[motor_index].join()
        except Exception:
            pass

        self._motor_threads[motor_index] = Thread(
            target=self.motors[motor_index].step, args=[maxsize, direction]
        )
        self._motor_threads[motor_index].start()

    def _stop_motors(self, motors=[0, 1]):
        """
        stop the given motors if they are running
        """
        for m in motors:
            self.logger.debug("stop %s motor", self.motors[m].name)
            self.motors[m].stop = True

    def _move_to(self, az, alt):
        """
        move to the position given by azimuth and altitude in degrees
        if there are other running moves wait till they are finished
        """
        self.logger.debug("move to %f / %f", az, alt)
        try:
            for t in self._motor_threads:
                t.join()
        except Exception:
            pass
        zipped = list(zip(self.motors, [az, alt]))
        self._motor_threads = [Thread(target=x[0].move, args=[x[1]]) for x in zipped]

        for t in self._motor_threads:
            t.start()

    def _start_tracking(self):
        """
        start the tracking thread
        """
        if not self._is_tracking:
            self.logger.debug("start tracking")
            self._is_tracking = True
            self._tracking_thread = Thread(target=self._do_tracking)
            self._tracking_thread.start()

    def _stop_tracking(self):
        """
        stop the tracking thread
        """
        if self._is_tracking:
            self.logger.debug("stop tracking")
            try:
                self._stop_motors()
                self._is_tracking = False
                self._tracking_thread.join()
                # be sure that motors are really stopped
                self._stop_motors()
            except Exception:
                pass

    def _do_tracking(self):
        """
        run a loop and recalculate
        """
        while self._is_tracking:
            try:
                self._observer.date = datetime.utcnow()
                self._target.compute(self._observer)
                self._move_to(
                    self._target.az / ephem.degree, self._target.alt / ephem.degree
                )
                sleep(0.1)
            except Exception:
                self._is_tracking = False

    def _visible_objects(self):
        """
        return list of visible objects
        """
        ret = []
        self._observer.date = datetime.utcnow()
        for i in range(len(self._sky_objects)):
            obj = self._sky_objects[i]
            obj.compute(self._observer)
            if obj.alt > 0:
                ret.append("%d-%s" % (i, obj.name))
        return ",".join(ret)

    def _reset_client_connection(self):
        """
        reset the client connected flag
        """
        self._client_connected = False

    def goto(self, ra, dec):
        """
        implenetation of the goto function

        get the ra and dec from stellarium, set the current time
        stop/start tracking
        """
        self.logger.debug("goto: %f / %f", ra, dec)
        self._target._ra = "%f" % ra
        self._target._dec = "%f" % dec
        self._observer.date = datetime.utcnow()
        # self._stop_motors()
        self._stop_tracking()
        self._start_tracking()

    def current_pos(self):
        """
        implementation of current_pos

        return the ra and dec from the target
        ephem works with radians so ra must be converted to hours
        and dec must be converted to degrees
        """
        self._observer.date = datetime.utcnow()
        ra, dec = self._observer.radec_of(
            self.motors[0].angle * ephem.degree, self.motors[1].angle * ephem.degree
        )
        ra /= 15.0 * ephem.degree
        dec /= ephem.degree
        self.logger.debug("send: %f / %f", ra, dec)

        return ra, dec

    def set_observer(self, lon, lat, alt):
        """
        implementation of set_observer

        set lon/lat/alt of the ephem observer (must be converted to radians)
        """
        self._observer.lon = lon * ephem.degree
        self._observer.lat = lat * ephem.degree
        self._observer.elev = alt
        self.logger.debug(
            "set location %s / %s / %s",
            self._observer.lon,
            self._observer.lat,
            self._observer.elev,
        )

    def start_calibration(self):
        """
        implementation of start_calibration

        reset the angles/steps lists for both motors
        set _is_calibrated to False
        reset the angles, steps and steps_per_rev of both motors
        """
        self.logger.debug("start calibration")
        if self._is_tracking:
            self._stop_tracking()

        self._angles_steps = [[], []]
        for motor in self.motors:
            motor.angle = 0
            motor.steps = 0
            motor.steps_per_rev = 1300000

    def stop_calibration(self):
        """
        implementation of stop calibration

        calculate steps per revolution for both motors by
        meaning the steps/degree for all pairs in the _angles_steps
        list.
        if this is successful set the steps_per_rev for the motors
        """
        self.logger.debug("stop calibration")
        for i in range(2):
            steps_list = []
            for comb in combinations(range(len(self._angles_steps[i])), 2):
                steps_diff = (
                    self._angles_steps[i][comb[1]][1]
                    - self._angles_steps[i][comb[0]][1]
                )
                angles_diff = (
                    self._angles_steps[i][comb[1]][0]
                    - self._angles_steps[i][comb[0]][0]
                )
                # check if both have same sign: if not add/subtract
                # one round to the angles
                if steps_diff * angles_diff < 0:
                    angles_diff += (steps_diff > 0) and 360 or -360

                try:
                    steps_per_rev = 360 * steps_diff / angles_diff
                    steps_list.append(steps_per_rev)
                except Exception:
                    pass

            try:
                self.motors[i].steps_per_rev = int(median(steps_list))
            except Exception:
                pass
        self.logger.debug(
            "steps per revolution: %d / %d",
            self.motors[0].steps_per_rev,
            self.motors[1].steps_per_rev,
        )

    def make_step(self, az_steps, alt_steps):
        """
        implementation of make_steps

        move the motors about the given steps (not threaded),
        if motors are already calibrated and there is an active target
        correct the ra/dec for this target
        """
        self.logger.debug("az_steps/ alt_steps: %f / %f", az_steps, alt_steps)
        restart = self._is_tracking
        self._stop_tracking()
        self.logger.debug("step motors: %d / %d", az_steps, alt_steps)
        self.motors[0].step(abs(az_steps), az_steps > 0)
        self.motors[1].step(abs(alt_steps), alt_steps > 0)
        if self.calibrated:
            self._observer.date = datetime.utcnow()
            self._target._ra, self._target._dec = self._observer.radec_of(
                self.motors[0].angle * ephem.degree, self.motors[1].angle * ephem.degree
            )
            # restart tracking if it was active
            if restart:
                self._start_tracking()

    def start_stop_motor(self, motor_id, action, direction):
        """
        implementation of start_stop_motor

        motors will be started threaded and stopped by setting the stop-flag
        motor will always be stopped before starting it if action==True
        if tracking is on stop it and restart it afterwards
        """
        # if not self.calibrated:
        self._stop_motors([motor_id])
        self.running[motor_id] = False

        if action:
            # remember tracking state and start motor
            self.logger.debug("Action")
            self.restart[motor_id] = self._is_tracking
            self.running[motor_id] = True
            self._stop_tracking()
            self._start_motor(motor_id, direction)
        else:
            # recalculate target position (just in case of tracking)
            if self.calibrated:
                if not any(self.running):
                    # no motor is running anymore thus adjust target
                    self._observer.date = datetime.utcnow()
                    self._target._ra, self._target._dec = self._observer.radec_of(
                        self.motors[0].angle * ephem.degree,
                        self.motors[1].angle * ephem.degree,
                    )
                    # restart tracking if tracking was active
                    if any(self.restart):
                        self._start_tracking()

    def set_object(self, object_id):
        try:
            self.choose_object_id = object_id
            obj = self._sky_objects[self.choose_object_id]
            self._observer.date = datetime.utcnow()
            obj.compute(self._observer)
            self._target._ra, self._target._dec = obj.a_ra, obj.a_dec
            self.logger.debug(
                "choose %s %s %s", obj.name, self._target._ra, self._target._dec
            )
            return True
        except Exception:
            self.logger.debug(f"could not set coordinates of object nr. {object_id}")

    def apply_object(self):
        """
        implementation of apply_object

        calculate position of given object, set the motors to
        the respective azimuthal and altitudinal angles and update
        the angles_steps lists
        """
        try:
            obj = self._sky_objects[self.choose_object_id]
            self.logger.debug("set %s", obj.name)
            self._observer.date = datetime.utcnow()
            obj.compute(self._observer)
            self.motors[0].angle = obj.az / ephem.degree
            self.motors[1].angle = obj.alt / ephem.degree
            for i in range(2):
                self._angles_steps[i].append(
                    (self.motors[i].angle, self.motors[i].steps)
                )
        except Exception:
            self.logger.error("no object has been choosen")

    def toggle_tracking(self):
        """
        implementation of toggle_tracking
        """
        if self.calibrated:
            self.logger.debug("calibrated")
            toggle = self._is_tracking
            if toggle:
                self._stop_tracking()
            else:
                self._start_tracking()
        else:
            self.logger.error("cannot start tracking when not calibrated")

    def get_status(self, status_code):
        """
        implentation of get status

        see code what is returned
        """
        if status_code == status.LOCATION:
            return self.location
        elif status_code == status.RADEC:
            return self.target
        elif status_code == status.AZALT:
            return "%s / %s" % (self.azimuth, self.altitude)
        elif status_code == status.CALIBRATED:
            return "calibrated: %s" % (self.calibrated and "YES" or "NO")
        elif status_code == status.TRACKING:
            # tracking is checked every second so set a timer to indicate that
            # a client is connected
            try:
                self._conn_timer.cancel()
            except Exception:
                pass
            self._client_connected = True
            self._conn_timer = Timer(3, self._reset_client_connection)
            self._conn_timer.start()
            return "tracking: %s" % (self._is_tracking and "YES" or "NO")
        elif status_code == status.SPR:
            return "steps per revolution (az/alt): %d / %d" % tuple(
                [m.steps_per_rev for m in self.motors]
            )
        elif status_code == status.AZ_ANGLES:
            return "angles/steps list for azimuth motor: %s" % self._angles_steps[0]
        elif status_code == status.ALT_ANGLES:
            return "angles/steps list for altitude motor: %s" % self._angles_steps[1]
        elif status_code == status.SIGHTED_OBJ:
            return "%d" % len(self._angles_steps[0])
        elif status_code == status.CURR_STEPS:
            return "current steps (az/alt): %d / %d" % (
                self.motors[0].steps,
                self.motors[1].steps,
            )
        elif status_code == status.VISIBLE_OBJ:
            return self._visible_objects()
        # elif status_code == status.MOTORRUN:
        #     return "tracking: %s" % (self._is_motorrun and "YES" or "NO")
        else:
            return "status code %d not defined" % status_code
