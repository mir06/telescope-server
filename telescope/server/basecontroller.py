# -*- encoding: utf-8  -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

class BaseController(object):
    """
    base controller class that implements all necessary functions
    """
    def __init__(self):
        self._ra = 0
        self._dec = 0

    def goto(self, ra, dec):
        """
        goto given ra [h] and dec [°]
        """
        self._ra, self._dec = ra, dec

    def current_pos(self):
        """
        return current ra [h] and dec [°]
        """
        return self._ra, self._dec

    def set_observer(self, lon, lat, alt):
        pass

    def start_calibration(self):
        pass

    def stop_calibration(self):
        pass

    def make_step(self, az, alt):
        pass

    def start_stop_motor(self, motor_id, action, direction):
        pass

    def set_object(self, object_id):
        pass

    def toggle_tracking(self):
        pass

    def get_status(self, status_code):
        return "everything's fine"
