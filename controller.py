from basecontroller import BaseController
from motor import Motor

import ephem
import ephem.stars

from numpy import median

from threading import Thread
from datetime import datetime
from time import sleep
from itertools import combinations

class Controller(BaseController):
    """
    this class implements the telescope control by two motors
    for the azimuthal and altitudinal rotation

    the motors are connected to the stepper motor driver DM420
    and controlled via GPIO on a raspberry pi (Motor class)
    """

    az_pins = [15,14,19]
    alt_pins = [18,20,19]

    def __init__(self):
        # initialize the motors
        self.motors = [
            Motor("Azimuth", self.az_pins),
            Motor("Altitude", self.alt_pins, min_angle=0., max_angle=90.)
        ]

        # initialize observer and target
        self._observer = ephem.Observer()
        self._target = ephem.FixedBody()

        # insteresting objects in our solar system and main stars
        self._sky_objects = [
            ephem.Sun(), ephem.Moon(), ephem.Mercury(), ephem.Venus(), ephem.Mars(),
            ephem.Jupiter(), ephem.Saturn() ]
        for star in sorted([ x.split(',')[0] for x in ephem.stars.db.split('\n') if x ]):
            self._sky_objects.append( ephem.star(star))

        # set boolean variable indicating tracking
        self._is_tracking = False

        # initialize angles/steps lists for calibration
        self._angles_steps = [[], []]

        ######################## test #####################
        self._observer.lon = "16:00"
        self._observer.lat = "47:23"
        self._observer.elev = 360

        self.motors[0].steps_per_rev = 4000
        self.motors[1].steps_per_rev = 4000


    @property
    def location(self):
        return "%s / %s / %s" % (self._observer.lon, self._observer.lat, self._observer.elev)

    @property
    def target(self):
        try:
            return "%s / %s" % (self._target.ra, self._target.dec)
        except:
            return "no target selected"

    @property
    def azimuth(self):
        return ephem.degrees("%f" % self.motors[0].angle)

    @property
    def altitude(self):
        return ephem.degrees("%f" % self.motors[1].angle)

    @property
    def calibrated(self):
        return all([ m.calibrated for m in self.motors ])

    def _stop_motors(self):
        """
        stop the motors if they are running
        """
        for m in self.motors:
            m.stop = True

    def _move_to(self, az, alt):
        """
        move to the position given by azimuth and altitude in degrees
        if there are other running moves wait till they are finished
        """
        try:
            for t in self._motor_threads:
                t.join()
        except:
            pass
        zipped = zip(self.motors, [az,alt])
        self._motor_threads = [ Thread(target=x[0].move, args=[x[1]]) for x in zipped ]

        for t in self._motor_threads:
            t.start()

    def _step_to(self, az_steps, alt_steps):
        """
        make threaded steps with both motors
        """
        try:
            for t in self._motor_threads:
                t.join()
        except:
            pass
        zipped = zip(self.motors, [az_steps, alt_steps])
        self._motor_threads = [ Thread(target=x[0].step, args=[abs(x[1]), x[1]>0]) for x in zipped ]

        for t in self._motor_threads:
            t.start()

    def _start_tracking(self):
        """
        start the tracking thread
        """
        self._is_tracking = True
        self._tracking_thread = Thread(target=self._do_tracking)
        self._tracking_thread.start()

    def _stop_tracking(self):
        """
        stop the tracking thread
        """
        try:
            self._stop_motors()
            self._is_tracking = False
            self._tracking_thread.join()
            self._stop_motors()
        except:
            pass

    def _do_tracking(self):
        """
        run a loop and recalculate
        """
        while self._is_tracking:
            try:
                self._observer.date = datetime.utcnow()
                self._target.compute(self._observer)
                self._move_to(self._target.az/ephem.degree, self._target.alt/ephem.degree)
                sleep(.1)
            except:
                self._is_tracking = False

    def _visible_objects(self):
        """
        return list of visible objects
        """
        ret = []
        self._observer.date = datetime.utcnow()
        for i in xrange(len(self._sky_objects)):
            obj = self._sky_objects[i]
            obj.compute(self._observer)
            if obj.alt > 0:
                ret.append("%d-%s" % (i, obj.name))
        return ','.join(ret)

    def goto(self, ra, dec):
        """
        implenetation of the goto function

        get the ra and dec from stellarium, set the current time
        stop/start tracking
        """
        self._target._ra = "%f" % ra
        self._target._dec = "%f" % dec
        self._observer.date = datetime.utcnow()
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
            self.motors[0].angle * ephem.degree,
            self.motors[1].angle * ephem.degree
            )
        return ra/(15.*ephem.degree), dec/ephem.degree

    def set_observer(self, lon, lat, alt):
        """
        implementation of set_observer

        set lon/lat/alt of the ephem observer (must be converted to radians)
        """
        self._observer.lon = lon * ephem.degree
        self._observer.lat = lat * ephem.degree
        self._observer.elev = alt
        return "OK"

    def start_calibration(self):
        """
        implementation of start_calibration

        reset the angles/steps lists for both motors
        set _is_calibrated to False
        reset the angles, steps and steps_per_rev of both motors
        """
        self._angles_steps = [[], []]
        for motor in self.motors:
            motor.angle = 0
            motor.steps = 0
            motor.steps_per_rev = 0
        return "OK"

    def stop_calibration(self):
        """
        implementation of stop calibration

        calculate steps per revolution for both motors by
        meaning the steps/degree for all pairs in the _angles_steps
        list.
        if this is successful set the steps_per_rev for the motors
        """
        for i in xrange(2):
            steps_list = []
            for comb in combinations(xrange(len(self._angles_steps[i])), 2):
                steps_diff = self._angles_steps[i][comb[1]][1]-self._angles_steps[i][comb[0]][1]
                angles_diff = self._angles_steps[i][comb[1]][0]-self._angles_steps[i][comb[0]][0]
                # check if both have same sign: if not add/subtract one round to the angles
                if steps_diff * angles_diff < 0:
                    angles_diff += (steps_diff > 0) and 360 or -360

                try:
                    steps_per_rev = 360 * steps_diff / angles_diff
                    steps_list.append(steps_per_rev)
                except:
                    pass

            try:
                self.motors[i].steps_per_rev = int(median(steps_list))
            except:
                pass
        return "OK"

    def make_step(self, az_steps, alt_steps):
        """
        implementation of make_steps

        move the motors about the given steps (not threaded),
        if motors are already calibrated and there is an active target
        correct the ra/dec for this target
        """
        restart = self._is_tracking
        self._stop_tracking()
        self.motors[0].step(abs(az_steps), az_steps>0)
        self.motors[1].step(abs(alt_steps), alt_steps>0)
        if self.calibrated:
            self._observer.date = datetime.utcnow()
            self._target.compute(self._observer)
            self._target._ra, self._target._dec = \
              self._observer.radec_of(
                  self._target.az + \
                  az_steps*ephem.twopi/self.motors[0].steps_per_rev,
                  self._target.alt + \
                  alt_steps*ephem.twopi/self.motors[1].steps_per_rev
                  )

        if restart:
            self._start_tracking()
        return "OK"


    def set_object(self, object_id):
        """
        implementation of set_object

        calculate position of given object, set the motors to
        the respective azimuthal and altitudinal angles and update
        the angles_steps lists
        """
        try:
            obj = self._sky_objects[object_id]
            self._observer.date = datetime.utcnow()
            obj.compute(self._observer)
            self.motors[0].angle = obj.az / ephem.degree
            self.motors[1].angle = obj.alt / ephem.degree
            for i in xrange(2):
                self._angles_steps[i].append((self.motors[i].angle, self.motors[i].steps))
        except:
            pass
        return "OK"

    def toggle_tracking(self):
        """
        implementation of toggle_tracking
        """
        toggle = self._is_tracking
        if toggle:
            self._stop_tracking()
            ret = "stopped tracking"
        else:
            self._start_tracking()
            ret = "started tracking"
        return ret

    def get_status(self, status_code):
        """
        implentation of get status

        see code what is returned
        """
        if status_code == 1:
            return self.location
        elif status_code == 2:
            return self.target
        elif status_code == 3:
            return "%s / %s" % (self.azimuth, self.altitude)
        elif status_code == 4:
            return "calibrated: %s" % (self.calibrated and "YES" or "NO")
        elif status_code == 5:
            return "tracking: %s" % (self._is_tracking and "YES" or "NO")
        elif status_code == 10:
            return "steps per revolution (az/alt): %d/%d" % tuple([m.steps_per_rev for m in self.motors])
        elif status_code == 11:
            return "angles/steps list for azimuth motor: %s" % self._angles_steps[0]
        elif status_code == 12:
            return "angles/steps list for altitude motor: %s" % self._angles_steps[1]
        elif status_code == 20:
            return "current steps (az/alt): %d/%d" % (self.motors[0].steps, self.motors[1].steps)
        elif status_code == 30:
            return self._visible_objects()
        else:
            return "status code %d not defined" % status_code
