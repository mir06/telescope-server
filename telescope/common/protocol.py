# -*- encoding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

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
    APPLY_OBJECT = 8
    STATUS       = 99

class status:
    LOCATION    = 1
    RADEC       = 2
    AZALT       = 3
    CALIBRATED  = 4
    TRACKING    = 5
    MOTORRUN    = 6
    SPR         = 10
    AZ_ANGLES   = 11
    ALT_ANGLES  = 12
    SIGHTED_OBJ = 13
    CURR_STEPS  = 20
    VISIBLE_OBJ = 30

