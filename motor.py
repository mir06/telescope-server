import time

# if not running on raspberry just ignore
# the actual control of the motors
try:
    import RPi.GPIO as GPIO
except:
    class gpio:
        OUT = 0
        BCM = 0
        def setmode(self, i):
            pass
        def setwarnings(self, b):
            pass
        def setup(self, p, i):
            pass
        def output(self, p, b):
            pass

    GPIO = gpio()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

class Motor(object):
    def __init__(self, name, pins, min_angle=0, max_angle=360):
        self.name = name
        self.PUL, self.DIR, self.ENBL = pins
        self._steps_per_rev = 0
        self._enabled = True
        self._angle = None
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._steps = 0
        self._stop = False
        for p in pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, True)

    def __str__(self):
        return self.name

    @property
    def steps_per_rev(self):
        return self._steps_per_rev

    @steps_per_rev.setter
    def steps_per_rev(self, value):
        self._steps_per_rev = value

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
        self._angle = value % 360

    @property
    def calibrated(self):
        return (self._angle != None) and (self._steps_per_rev>0)

    @property
    def stop(self):
        return self._stop

    @stop.setter
    def stop(self, value):
        self._stop = value

    def step(self, steps, direction):
        self._stop = False
        GPIO.output(self.DIR, direction)
        for step in xrange(steps):
            if self._stop:
                break
            GPIO.output(self.PUL, True)
            GPIO.output(self.PUL, False)
            self._steps += 2*(direction-.5)
            if self._angle != None and self._steps_per_rev:
                self._angle += (direction-.5)*(720./self._steps_per_rev)
            time.sleep(.05)

    def move(self, angle):
        angle = angle % 360
        if self._angle != None and self._steps_per_rev and self._enabled:
            angle_to_move = (angle - self._angle) % 360
            if angle_to_move > 180:
                angle_to_move = - (360.-angle_to_move)
            steps = self._steps_per_rev * angle_to_move / 360
            self.step(int(abs(round(steps))), steps>0)

