from basecontroller import BaseController
from motor import Motor

import ephem
import ephem.stars

from threading import Thread
from datetime import datetime
from time import sleep


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
        return "%s / %s" % (self._target.ra, self._target.dec)

    @property
    def azimuth(self):
        az = ephem.hours(self.motors[0].angle)
        print self.motors[0].angle, az
        return "%s" % az

    @property
    def altitude(self):
        alt = ephem.degrees(self.motors[1].angle)
        print self.motors[1].angle, alt
        return "%s" % alt

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
            # try:
                self._observer.date = datetime.utcnow()
                self._target.compute(self._observer)
                self._move_to(self._target.az/ephem.degree, self._target.alt/ephem.degree)
                sleep(.1)
            # except:
            #     self._is_tracking = False

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
        else:
            return "status code %d not defined"
