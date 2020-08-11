# -*- encoding: utf-8  -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

# if not running on raspberry just ignore
# the actual control of the motors
try:
    # Third party
    import RPi.GPIO as GPIO
except ImportError:
    # Standard Library
    from time import sleep

    class gpio:
        BCM = 0
        OUT = 0
        IN = 0
        BOTH = 0
        PUD_DOWN = 0
        PUD_UP = 0
        RISING = 0
        FALLING = 0

        def setmode(self, mode):
            pass

        def setwarnings(self, bool):
            pass

        def setup(self, pin, in_out, pull_up_down=PUD_DOWN):
            pass

        def input(self, pin):
            return True

        def output(self, pin, bool):
            pass

        def add_event_detect(self, pin, edge, callback=None, bouncetime=None):
            pass

        def wait_for_edge(self, pin, edge):
            # just sleep forever
            while True:
                sleep(600)

    GPIO = gpio()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
