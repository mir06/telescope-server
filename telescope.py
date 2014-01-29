#! /usr/bin/env python
import SocketServer
import sys
import argparse
import logging
from datetime import datetime
from threading import Thread
from string import replace
from time import time, sleep
from bitstring import BitArray, BitStream, ConstBitStream
import ephem
import RPi.GPIO as GPIO
from motor import Motor

def getopts():
    parser = argparse.ArgumentParser(description="Telescope Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=10000)

    parser.add_argument("--azimuth-pins", default="15,14,19",
                        help="GPIO-Pins for azimuthal motor (PUL, DIR, ENBL)")
    parser.add_argument("--altitude-pins", default="18,20,22",
                        help="GPIO-Pins for altitudal motor (PUL, DIR, ENBL)")
    parser.add_argument("--log-level", default="DEBUG",
                        help="set logging level")
    args = parser.parse_args(sys.argv[1:])
    return vars(args)

class TelescopeRequestHandler(SocketServer.BaseRequestHandler):
    def _stellarium2coords(self, ra_uint, dec_int):
        return (ra_uint*12./2147483648, dec_int*90./1073741824)

    def _coords2stellarium(self, ra, dec):
        return (int(ra*(2147483648/12.0)), int(dec*(1073741824/90.0)))

    def handle_stellarium(self, data):
        if self.server.ready:
            # indicate other stellarium request to finish
            self.only_stellarium_request = False

            # time
            mtime = data.read('intle:64')

            # RA
            ant_pos = data.bitpos
            ra = data.read('hex:32')
            data.bitpos = ant_pos
            ra_uint = data.read('uintle:32')

            # DEC
            ant_pos = data.bitpos
            dec = data.read('hex:32')
            data.bitpos = ant_pos
            dec_int = data.read('intle:32')

            ra, dec = self._stellarium2coords(ra_uint, dec_int)
            logging.info("goto: ra: %f, dec: %f", ra, dec, extra=self.extra)

            self.server.target._ra = "%f" % ra
            self.server.target._dec = "%f" % dec
            self.server.observer.date = datetime.utcnow()

            self.server.target.compute(self.server.observer)
            az = self.server.target.az / ephem.degree
            alt = self.server.target.alt / ephem.degree
            logging.debug("time: %s", self.server.observer.date, extra=self.extra)
            logging.info("az: %f, alt: %f", az, alt, extra=self.extra)
            ra, dec = self.server.observer.radec_of(
                az ,
                alt
            )
            logging.info("ra: %f, dec: %f", ra, dec, extra=self.extra)

            # threaded motor move
            self.server.move(az, alt)

            # allow this stellarium request to run until another arrives
            self.only_stellarium_request = True
#            sleep(10)
#            for aa in xrange(10):
#            while self.only_stellarium_request:
            #     self.server.observer.date = datetime.utcnow()
            #     ra, dec = self.server.observer.radec_of(
            #         self.server.motors["az"].angle * ephem.degree,
            #         self.server.motors["alt"].angle * ephem.degree
            #         )
            #     ra_s, dec_s = self._coords2stellarium( ra, dec )
            #     msize = '0x1800'
            #     mtype = '0x0000'
            #     localtime = ConstBitStream(replace('int:64=%r' % time(), '.', ''))
            #     sdata = ConstBitStream(msize) + ConstBitStream(mtype)
            #     sdata += ConstBitStream(intle=localtime.intle, length=64)
            #     sdata += ConstBitStream(uintle=ra_uint, length=32)
            #     sdata += ConstBitStream(intle=dec_int, length=32)
            #     sdata += ConstBitStream(intle=0, length=32)
            #     logging.debug("sending data: ra: %f, dec: %f", ra, dec, extra=self.extra)
            #     self.request.send(sdata.bytes)
            #     # sleep(1)
            # logging.debug("motor az: %f, alt: %f", self.server.motors["az"].angle,
            #               self.server.motors["alt"].angle, extra=self.extra)
            # self.request.close()


        else:
            logging.info("telescope not calibrated", extra=self.extra)

    def set_observer(self, data):
        self.server.observer.lon = data.read('floatle:32')
        self.server.observer.lat = data.read('floatle:32')
        self.server.observer.elev = data.read('floatle:32')
        logging.info("set observer: %s / %s / %s",
                        self.server.observer.lon,
                        self.server.observer.lat,
                        self.server.observer.elev,
                        extra=self.extra)

    def handle(self):
        self.extra = {'clientip': self.client_address[0]}
        data0 = ''
        logging.debug("connection established", extra=self.extra)
        # self.request.setblocking(False)
        # try:
        #     data0 = self.request.recv(160)
        # except SocketServer.socket.error, e:
        #     print e

        if data0:
            data = ConstBitStream(bytes=data0, length=160)
            msize = data.read('intle:16')
            mtype = data.read('intle:16')

            logging.debug("client-type: %d", mtype, extra=self.extra)
            if mtype == 0:
                # stellarium telescope client
                self.handle_stellarium(data)
            elif mtype == 1:
                # set observer
                # LON (4 bytes), LAT (4 bytes), ALT (2 bytes)
                self.set_observer(data)
        else:
            # send current position
            logging.debug("no data received", extra=self.extra)
            self.server.observer.date = datetime.utcnow()
            ra, dec = self.server.observer.radec_of(
                self.server.motors["az"].angle * ephem.degree,
                self.server.motors["alt"].angle * ephem.degree
            )
            print ra, dec
            ra_s, dec_s = self._coords2stellarium( 10., 22. )
            msize = '0x1800'
            mtype = '0x0000'
            localtime = ConstBitStream(replace('int:64=%r' % time(), '.', ''))
            sdata = ConstBitStream(msize) + ConstBitStream(mtype)
            sdata += ConstBitStream(intle=localtime.intle, length=64)
            sdata += ConstBitStream(uintle=ra_s, length=32)
            sdata += ConstBitStream(intle=dec_s, length=32)
            sdata += ConstBitStream(intle=0, length=32)
            logging.debug("sending data: ra: %f, dec: %f", ra, dec, extra=self.extra)
            self.request.send(sdata.bytes)


        # for x in range(10):
        #     localtime = ConstBitStream(replace('int:64=%r' % time(), '.', ''))
        #     reply = ConstBitStream('0x1800') + ConstBitStream('0x0000')
        #     reply += ConstBitStream(intle=localtime.intle, length=64) + ConstBitStream(uintle=ra_uint, length=32)
        #     reply += ConstBitStream(intle=dec_int, length=32) + ConstBitStream(intle=0, length=32)
        #     print " sending"
        #     self.request.send(reply.bytes)
        #     sleep(.001)
        # self.request.close()



class TelescopeServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    def __init__(self, server_address, motors, RequestHandler):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandler)
        self.motors = motors
        self.target = ephem.FixedBody()
        self.observer = ephem.Observer()

        # testing
        self.observer.lon = '15:25:12.0'
        self.observer.lat = '47:4:48.01'
        self.observer.elev = 362

        for m in self.motors.values():
            m.angle=0
            m.steps_per_rev=800

    @property
    def ready(self):
        ret = True
        for motor in self.motors.values():
            ret = ret and motor.calibrated
        ret = ret and self.observer.lat != 0
        return ret

    def move(self, az, alt):
        # wait for motor moves if there are ones
        try:
            for t in self.threads:
                t.join()
        except:
            pass
        self.threads = [ Thread(target=self.motors["az"].move, args=[az]),
                         Thread(target=self.motors["alt"].move, args=[alt]) ]
        for t in self.threads:
            t.start()

if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    args = getopts()

    # set logging level
    numeric_level = getattr(logging, args["log_level"].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logging.basicConfig(filename="telescope.log",
                        level=numeric_level,
                        format="%(asctime)s %(clientip)s %(message)s",
                        datefmt='%Y-%m-%d %H:%M:%S')

    motors = {"az": Motor("Azimuth motor", map(int, args["azimuth_pins"].split(","))),
              "alt": Motor("Altitude motor", map(int, args["altitude_pins"].split(",")), max_angle=90)}
    server = TelescopeServer((args["host"], args["port"]), motors, TelescopeRequestHandler)

    # terminate with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
