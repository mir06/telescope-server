#! /usr/bin/env python
# -*- encoding: utf-8 -*-


"""
´shut down Raspbery
"""

import os
import sys
import subprocess
from time import sleep
import logging
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
import socket;
from bitstring import ConstBitStream
from threading import Thread
import thread
sys.path.append("../common")
from protocol import status, command

hostname="10.0.0.17"
port=10000

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
        def setup(self, p, i, pull_up_down=0):
            pass
        def output(self, p, b):
            pass
        def input(self, p):
            pass    
        def add_event_detect(self, p, i, callback, bouncetime):
            pass
        def wait_for_edge(self, p, i):
            while True:
               sleep(0.1)
            pass        
        def cleanup(self):
            print "Ende"
            pass        

    GPIO = gpio()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
pin_shutdown=4
pin_status=2

GPIO.setup(pin_shutdown, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
GPIO.setup(pin_status, GPIO.OUT)
blink_delay=5 

def status_led():
    while True:
        GPIO.output(pin_status, False)
        sleep(blink_delay)
        GPIO.output(pin_status, True)        
        sleep(blink_delay)



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
        
def programm_check():
    global hostname
    global port
    global blink_delay
    connection = Connector(hostname, port)
    while True:
        try:
            if connection.get_tracking_status():
                print "Tracking"
                blink_delay=0.50
            else:
                print "stop"
                blink_delay=1
        except:
            blink_delay=3
        sleep(3)       

class Raspberry_halt(object):
    def __init__(self):
        try:
            thread.start_new_thread(status_led,())
            thread.start_new_thread(programm_check,())
            GPIO.wait_for_edge(pin_shutdown, GPIO.RISING)
            sleep(2)
            GPIO.cleanup()           # clean up GPIO on normal exit  
            subprocess.call(['shutdown -h now "System halted by GPIO action"'], shell=True)
        except KeyboardInterrupt:  
            GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
        GPIO.cleanup()           # clean up GPIO on normal exit
if __name__ == "__main__":
    raspberry_halt = Raspberry_halt()
