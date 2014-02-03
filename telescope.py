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
import ephem.stars
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

    def return_visible_objects(self):
        ret = []
        for obj in self.server.objects:
            obj.compute(self.server.observer)
            ret.append("%s:%d" % (obj.name, obj.alt > 0))
        self.request.sendall(','.join(ret))



    def handle_stellarium(self, data):
        if self.server.ready:
            logging.debug("stellarium goto command", extra=self.extra)

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

            self.server.target._ra = "%f" % ra
            self.server.target._dec = "%f" % dec
            self.server.observer.date = datetime.utcnow()

            self.server.target.compute(self.server.observer)

            dt = self.server.observer.date
            ra, dec = self.server.target.ra, self.server.target.dec
            az, alt = self.server.target.az, self.server.target.alt

            logging.debug("ra: %12s, dec: %12s, time: %20s", ra, dec, dt, extra=self.extra)
            logging.debug("az: %12s, alt: %12s, time: %20s", az, alt, dt, extra=self.extra)

            # start following the target
            self.set_following(ConstBitStream('0x00ff00ff'), False)

            # # move to target
            # self.server.move(az / ephem.degree, alt / ephem.degree)

        else:
            logging.info("telescope not calibrated", extra=self.extra)

    def set_observer(self, data):
        """
        set lon/lat/alt of observer
        return a list of visible objects in our solar system
        """
        self.server.observer.lon = data.read('floatle:32')
        self.server.observer.lat = data.read('floatle:32')
        self.server.observer.elev = data.read('floatle:32')
        logging.info("set observer: %s / %s / %s",
                        self.server.observer.lon,
                        self.server.observer.lat,
                        self.server.observer.elev,
                        extra=self.extra)
        self.return_visible_objects()

    def set_following(self, data, ret=True):
        """
        start/stop following fixed object
        """
        nr = data.read('intle:16')
        on = data.read('intle:16')

        # if following is active close it
        try:
            self.server.stop()
            self.server._follow = False
            self.server.following.join()
            self.server.stop()

            logging.debug("stop following %s", self.server.follow_object.name, extra=self.extra)
        except:
            pass

        try:
            self.server.follow_object = self.server.objects[nr]
        except:
            self.server.follow_object = self.server.target


        if on:
            self.server._follow = True
            self.server.following = Thread(target=self.server.follow)
            self.server.following.start()
            logging.debug("start following %s", self.server.follow_object.name, extra=self.extra)

        # return the visible objects if called from the client
        if ret:
            self.return_visible_objects()

    def make_step(self, data):
        """
        make steps with the motors
        """
        steps_az = data.read('intle:16')
        steps_alt = data.read('intle:16')
        self.server.motors["az"].step(abs(steps_az), steps_az>0)
        self.server.motors["alt"].step(abs(steps_alt), steps_alt>0)
        print "vorher  ", self.server.target._ra, self.server.target._dec
        self.server.target._ra, self.server.target._dec = \
            self.server.observer.radec_of(
                self.server.target.az + \
                steps_az*ephem.twopi/self.server.motors["az"].steps_per_rev,
                self.server.target.alt + \
                steps_alt*ephem.twopi/self.server.motors["alt"].steps_per_rev)
        print "nachher ", self.server.target._ra, self.server.target._dec
        self.return_visible_objects()

    def handle(self):
        self.extra = {'clientip': self.client_address[0]}
        logging.debug("connection established", extra=self.extra)
        while True:
            data0 = ''
            self.request.setblocking(0)
            try:
                data0 = self.request.recv(160)
            except SocketServer.socket.error, e:
                pass

            if data0:
                data = ConstBitStream(bytes=data0, length=160)
                msize = data.read('intle:16')
                mtype = data.read('intle:16')

                if mtype == 0:
                    # stellarium telescope client
                    self.handle_stellarium(data)
                elif mtype == 1:
                    # set observer and leave the endless loop
                    # LON (4 bytes), LAT (4 bytes), ALT (2 bytes)
                    self.set_observer(data)
                    break
                elif mtype == 2:
                    # start or stop tracking on current object
                    # object number (2 bytes): 0..len(self.objects) = solar system objects,
                    #                          everything else is fixed object
                    # on/off (2 bytes)
                    self.set_following(data)
                    break
                elif mtype == 3:
                    # make one step with the motors
                    # az motor steps (2 bytes): number of steps of azimutal motor
                    # alt motor steps (2 bytes): number of steps of altitudinal motor
                    self.make_step(data)
                    break

            else:
                if self.server.ready:
                    # send current position
                    self.server.observer.date = datetime.utcnow()
                    ra, dec = self.server.observer.radec_of(
                        self.server.motors["az"].angle * ephem.degree,
                        self.server.motors["alt"].angle * ephem.degree
                        )

                    ra_s, dec_s = self._coords2stellarium( ra/(15.*ephem.degree), dec/ephem.degree )
                    msize = '0x1800'
                    mtype = '0x0000'
                    localtime = ConstBitStream(replace('int:64=%r' % time(), '.', ''))
                    sdata = ConstBitStream(msize) + ConstBitStream(mtype)
                    sdata += ConstBitStream(intle=localtime.intle, length=64)
                    sdata += ConstBitStream(uintle=ra_s, length=32)
                    sdata += ConstBitStream(intle=dec_s, length=32)
                    sdata += ConstBitStream(intle=0, length=32)
                    logging.debug("sending data: ra: %12s, dec: %12s, time: %20s", ra, dec, ephem.now(), extra=self.extra)
                    try:
                        self.request.send(sdata.bytes)
                    except:
                        pass
                    sleep(.5)


class TelescopeServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    def __init__(self, server_address, motors, RequestHandler):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandler)
        self.motors = motors
        self.target = ephem.FixedBody()
        self.target.name = 'fixed object'
        self.observer = ephem.Observer()

        # testing
        self.observer.lon = '15:25:12.0'
        self.observer.lat = '47:4:48.01'
        self.observer.elev = 362

        for m in self.motors.values():
            m.angle=0
            m.steps_per_rev=4000



        # interesting objects in our solar system
        self.objects = [ ephem.Sun(), ephem.Moon(), ephem.Mercury(), ephem.Venus(), ephem.Mars(),
                         ephem.Jupiter(), ephem.Saturn(), ephem.Uranus(), ephem.Neptune(), ephem.Pluto(),
                         ephem.Phobos(), ephem.Deimos(), ephem.Io(), ephem.Europa(), ephem.Ganymede(),
                         ephem.Callisto(), ephem.Mimas(), ephem.Enceladus(), ephem.Tethys(), ephem.Dione(),
                         ephem.Rhea(), ephem.Titan(), ephem.Iapetus(), ephem.Hyperion(), ephem.Miranda(),
                         ephem.Ariel(), ephem.Umbriel(), ephem.Titania(), ephem.Oberon() ]

        # stars
        self.stars = sorted([ x.split(',')[0] for x in  ephem.stars.db.split() ])

        self._follow = False
        self._follow_object = False

    @property
    def ready(self):
        ret = True
        for motor in self.motors.values():
            ret = ret and motor.calibrated
        ret = ret and self.observer.lat != 0
        return ret

    def stop(self):
        """
        stop motors
        """
        for m in self.motors.values():
            m.stop = True

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

    def follow(self):
        while self._follow:
            self.observer.date = datetime.utcnow()
            self.follow_object.compute(self.observer)
            ra, dec = self.follow_object.ra, self.follow_object.dec
            az, alt = self.follow_object.az, self.follow_object.alt
            dt = self.observer.date

            # logging.debug("follow", extra={'clientip': 'localhost'})
            # logging.debug("ra: %12s, dec: %12s, time: %20s", ra, dec, dt, extra={'clientip': 'localhost'})
            # logging.debug("az: %12s, alt: %12s, time: %20s", az, alt, dt, extra={'clientip': 'localhost'})

            self.move(az / ephem.degree, alt / ephem.degree)
            sleep(.1)


if __name__ == "__main__":
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
