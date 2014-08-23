#! /usr/bin/env python
# -*- encoding: utf-8 -*-


"""
the client for controlling the telescope server manually
"""

import os
import sys
import subprocess
from time import sleep
from math import sqrt, ceil
import socket
from bitstring import ConstBitStream

from threading import Thread
import thread 

os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
sys.path.append("../common")
from protocol import status, command


try:
    import RPi.GPIO as GPIO
except:
    class gpio:
        OUT = 0
        IN = 0
        BCM = 0
        PUD_UP = 0
        PUD_DOWN = 1
        FALLING=0
        RISING=1
        def setmode(self, i):
            pass
        def setwarnings(self, b):
            pass
        def setup(self, p, i, pull_up_down):
            pass
        def output(self, p, b):
            pass
        def input(self, p):
            pass    
        def add_event_detect(self, p, i, callback, bouncetime):
            pass
        def wait_for_edge(self, p, i ):
            while True:
               sleep(0.1)
            pass        
        def cleanup(self):
            pass        

    GPIO = gpio()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pin_left=22
pin_right=27
pin_up=9
pin_down=11

pin_apply=10


hostname="localhost"
port=10000

class Connector(object):
    """
    connection class to the telescope server
    """
    def __init__(self, hostname, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((hostname, port))
            sock.close()
            self.hostname = hostname
            self.port = port
        except:
            raise ValueError

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "%s:%d" % (self.hostname, self.port)

    def _make_connection(self, data):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.hostname, self.port))
        data += ConstBitStream('int:%d=0' % (160-data.len))
        try:
            sock.sendall(data.tobytes())
            response = sock.recv(1024)
            return response
        finally:
            sock.close()

    def get_status(self, status_code):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.STATUS)
        data += ConstBitStream('intle:16=%d' % status_code)
        response = self._make_connection(data)
        return response

    def get_location(self):
        return self.get_status(status.LOCATION)

    def get_radec(self):
        return self.get_status(status.RADEC)

    def get_azalt(self):
        return self.get_status(status.AZALT)

    def get_calibration_status(self, boolean=True):
        response = self.get_status(status.CALIBRATED)
        if boolean:
            return response.endswith("YES")
        else:
            return response.split()[-1]

    def get_tracking_status(self, boolean=True):
        response = self.get_status(status.TRACKING)
        if boolean:
            return response.endswith("YES")
        else:
            return response.split()[-1]

    def get_spr(self):
        response = self.get_status(status.SPR)
        return response.split(':')[-1]

    def get_visible_objects(self):
        response = self.get_status(status.VISIBLE_OBJ)
        return response.split(',')

    def get_number_of_sighted_objects(self):
        response = self.get_status(status.SIGHTED_OBJ)
        return response

    def start_stop_motor(self, motor_id, action, direction=True):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.START_MOT)
        data += ConstBitStream('intle:16=%d' % motor_id)
        data += ConstBitStream('intle:16=%d' % action)
        data += ConstBitStream('intle:16=%d' % direction)
        tmp = self._make_connection(data)

    def make_step(self, motor_id, direction):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.MAKE_STEP)
        data += ConstBitStream('intle:16=%d' % (2*(motor_id==0) * (direction-.5)))
        data += ConstBitStream('intle:16=%d' % (2*(motor_id==1) * (direction-.5)))
        tmp = self._make_connection(data)
        
    def apply_object(self):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.APPLY_OBJECT)
        tmp = self._make_connection(data)

class IOClient(object):
    motor=False
    def __init__(self):
    
        # start thread that looks if tracking is active or not
        self.connection = Connector(hostname, port)
 
        GPIO.setup(pin_left, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  
        GPIO.setup(pin_right, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  
        GPIO.setup(pin_up, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  
        GPIO.setup(pin_down, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  
        GPIO.setup(pin_apply, GPIO.IN, pull_up_down=GPIO.PUD_UP)  

        def motorthread_az():
            motorrun_az=False
            while True:
                if ((GPIO.input(pin_left) or GPIO.input(pin_right)) and not(motorrun_az)):
                    if (GPIO.input(pin_left)):
                        self.connection.start_stop_motor(0, True, True)
                        motorrun_az=True
                    else:
                        self.connection.start_stop_motor(0, True, False)
                        motorrun_az=True 
                elif (not(GPIO.input(pin_left)) and not(GPIO.input(pin_right))and motorrun_az):
                    self.connection.start_stop_motor(0, False)
                    motorrun_az=False
                sleep(0.05)
                
        def motorthread_alt():
            motorrun_alt=False
            while True:
                if ((GPIO.input(pin_up) or GPIO.input(pin_down)) and not(motorrun_alt)):
                    if not(GPIO.input(pin_up)):
                        self.connection.start_stop_motor(1, True, True)
                        motorrun_alt=True
                    else:
                        self.connection.start_stop_motor(1, True, False)
                        motorrun_alt=True 
                elif (not(GPIO.input(pin_up)) and not(GPIO.input(pin_down))and motorrun_alt):
                    self.connection.start_stop_motor(1, False)
                    motorrun_alt=False
                sleep(0.05)                        

        try:
            thread.start_new_thread(motorthread_az,())
            thread.start_new_thread(motorthread_alt,())
            while True:  
                GPIO.wait_for_edge(pin_apply, GPIO.FALLING)
                self.connection.apply_object()
                sleep(0.5)  
        except KeyboardInterrupt:  
            GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
        GPIO.cleanup()           # clean up GPIO on normal exit  
if __name__ == "__main__":
    ioclient = IOClient()
