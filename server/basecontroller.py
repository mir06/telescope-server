# -*- encoding: utf-8  -*-
"""
"""

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
        return ""

    def start_calibration(self):
        return ""

    def stop_calibration(self):
        return ""

    def make_step(self, az, alt):
        return ""

    def set_object(self, object_id):
        return ""

    def toggle_tracking(self):
        return ""

    def get_status(self, status_code):
        return "everything's fine"
