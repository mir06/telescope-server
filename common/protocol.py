# -*- encoding: utf-8 -*-

"""
the protocol codes
"""

class command:
    STELLARIUM   = 0
    LOCATION     = 1
    START_CAL    = 2
    STOP_CAL     = 3
    MAKE_STEP    = 4
    START_MOT    = 5
    SET_ANGLE    = 6
    TOGGLE_TRACK = 7
    STATUS       = 99

class status:
    LOCATION    = 1
    RADEC       = 2
    AZALT       = 3
    CALIBRATED  = 4
    TRACKING    = 5
    SPR         = 10
    AZ_ANGLES   = 11
    ALT_ANGLES  = 12
    CURR_STEPS  = 20
    VISIBLE_OBJ = 30

