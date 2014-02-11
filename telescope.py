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
from itertools import combinations
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

    def _return_visible_objects(self):
        ret = []
        self.server._observer.date = datetime.utcnow()
        for i in xrange(len(self.server._sky_objects)):
            obj = self.server._sky_objects[i]
            obj.compute(self.server._observer)
            if obj.alt>0:
                ret.append("%d-%s" % (i, obj.name))
        self.request.sendall(','.join(ret))

    def _handle_stellarium(self, data):
        if self.server._ready:
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

            self.server._target._ra = "%f" % ra
            self.server._target._dec = "%f" % dec
            self.server._observer.date = datetime.utcnow()

            self.server._target.compute(self.server._observer)

            dt = self.server._observer.date
            ra, dec = self.server._target.ra, self.server._target.dec
            az, alt = self.server._target.az, self.server._target.alt

            logging.debug("ra: %12s, dec: %12s, time: %20s", ra, dec, dt, extra=self.extra)
            logging.debug("az: %12s, alt: %12s, time: %20s", az, alt, dt, extra=self.extra)

            # stop/start following the target
            self.server._follow_object = self.server._target
            self.server._stop_following(self.extra)
            self.server._start_following(self.extra)

        else:
            logging.info("telescope not calibrated", extra=self.extra)

    def _set_observer(self, data):
        """
        set lon/lat/alt of observer
        return a list of visible objects in our solar system
        """
        self.server._observer.lon = data.read('floatle:32')
        self.server._observer.lat = data.read('floatle:32')
        self.server._observer.elev = data.read('floatle:32')
        logging.info("set observer: %s / %s / %s",
                        self.server._observer.lon,
                        self.server._observer.lat,
                        self.server._observer.elev,
                        extra=self.extra)
        self._return_visible_objects()

    def _set_following(self, data):
        """
        start/stop following object
        """
        nr = data.read('intle:16')
        on = data.read('intle:16')

        # if following is active close it
        self.server._stop_following(self.extra)

        # set the object to be followed
        try:
            self.server._follow_object = self.server._solar_objects[nr]
        except:
            self.server._follow_object = self.server._target

        # if request was to start
        if on:
            self.server._start_following(self.extra)

        self._return_visible_objects()


    def _make_step(self, data):
        """
        make steps with the motors
        """
        restart = self.server._do_following
        self.server._stop_following(self.extra)

        steps_az = data.read('intle:16')
        steps_alt = data.read('intle:16')
        logging.debug("moving motors %d,%d", steps_az, steps_alt, extra=self.extra)
        self.server._motors["az"].step(abs(steps_az), steps_az>0)
        self.server._motors["alt"].step(abs(steps_alt), steps_alt>0)
        if self.server._ready:
            self.server._observer.date = datetime.utcnow()
            server._target.compute(server._observer)
            self.server._target._ra, self.server._target._dec = \
              self.server._observer.radec_of(
                  self.server._target.az + \
                  steps_az*ephem.twopi/self.server._motors["az"].steps_per_rev,
                  self.server._target.alt + \
                  steps_alt*ephem.twopi/self.server._motors["alt"].steps_per_rev)
            if restart:
                self.server._start_following(self.extra)

        self._return_visible_objects()

    def _set_coords_of_object(self, data):
        """
        set motors' angle to the given object's az/alt
        """
        obj_nr = data.read('intle:16')
        try:
            obj = self.server._sky_objects[obj_nr]
            self.server._observer.date = datetime.utcnow()
            obj.compute(self.server._observer)
            self.server._motors["az"].angle = obj.az / ephem.degree
            self.server._motors["alt"].angle = obj.alt / ephem.degree
            self.server._set_calibration_marker(self.extra)
        except:
            pass

        # return number of markers
        self.request.sendall("%d" % len(self.server.calibration_data["az"]))

    def _start_calibration(self):
        self.server._stop_following(self.extra)
        self.server._uncalibrate_motors(self.extra)
        if self.server._observer.lat == 0:
            self.request.sendall('set_location')
        else:
            self._return_visible_objects()

    def _stop_calibration(self):
        self.server._calibrate_motors()

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
                    self._handle_stellarium(data)
                elif mtype == 1:
                    # set observer and leave the endless loop
                    # LON (4 bytes), LAT (4 bytes), ALT (2 bytes)
                    self._set_observer(data)
                    break
                elif mtype == 2:
                    # start calibration: reset motors' steps per revision
                    self._start_calibration()
                    break
                elif mtype == 3:
                    self._stop_calibration()
                    break
                elif mtype == 4:
                    # make one step with the motors
                    # az motor steps (2 bytes): number of steps of azimutal motor
                    # alt motor steps (2 bytes): number of steps of altitudinal motor
                    self._make_step(data)
                    break
                elif mtype == 5:
                    # set the angle of the motors to given object (index in server sky_object list)
                    self._set_coords_of_object(data)
                    break
                elif mtype == 6:
                    # start or stop tracking on current object
                    # object number (2 bytes): 0..len(self.objects) = solar system objects,
                    #                          everything else is fixed object
                    # on/off (2 bytes)
                    self._set_following(data)
                    break


            else:
                if self.server._ready:
                    # send current position
                    self.server._observer.date = datetime.utcnow()
                    ra, dec = self.server._observer.radec_of(
                        self.server._motors["az"].angle * ephem.degree,
                        self.server._motors["alt"].angle * ephem.degree
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
#                    logging.debug("sending data: ra: %12s, dec: %12s, time: %20s", ra, dec, ephem.now(), extra=self.extra)
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
        self._motors = motors

        # do not follow any object at initialization
        self._do_following = False
        self._follow_object = False

        # initialize target and observer
        self._target = ephem.FixedBody()
        self._target.name = 'fixed object'
        self._observer = ephem.Observer()

        ################ testing
        self._observer.lon = '15:25:12.0'
        self._observer.lat = '47:4:48.01'
        self._observer.elev = 362

        for m in self._motors.values():
            m.angle=0
            m.steps_per_rev=4000 #51200
        ##################################

        # interesting objects in our solar system and main stars
        self._sky_objects = [
            ephem.Sun(), ephem.Moon(), ephem.Mercury(), ephem.Venus(), ephem.Mars(),
            ephem.Jupiter(), ephem.Saturn() ]
        # stars
        for star in sorted([ x.split(',')[0] for x in ephem.stars.db.split('\n') if x ]):
            self._sky_objects.append( ephem.star(star))


        # reset calibration of motors
        self._uncalibrate_motors()

    @property
    def _ready(self):
        ret = True
        for motor in self._motors.values():
            ret = ret and motor.calibrated
        ret = ret and self._observer.lat != 0
        return ret

    def _stop_motors(self):
        """
        stop motors
        """
        for m in self._motors.values():
            m.stop = True

    def _move_to(self, az, alt):
        # wait for motor moves if there are ones
        try:
            for t in self._motor_threads:
                t.join()
        except:
            pass
        self._motor_threads = [ Thread(target=self._motors["az"].move, args=[az]),
                                Thread(target=self._motors["alt"].move, args=[alt]) ]
        for t in self._motor_threads:
            t.start()

    def _start_following(self, extra={'clientip': 'localhost'}):
        self._do_following = True
        self._following_thread = Thread(target=self._following)
        self._following_thread.start()
        logging.debug("start following %s", self._follow_object.name, extra=extra)

    def _stop_following(self, extra={'clientip': 'localhost'}):
        try:
            self._stop_motors()
            self._do_following = False
            self._following_thread.join()
            self._stop_motors()
            logging.debug("stop following %s", self._follow_object.name, extra=extra)
        except:
            pass


    def _following(self):
        while self._do_following:
            self._observer.date = datetime.utcnow()
            self._follow_object.compute(self._observer)
            ra, dec = self._follow_object.ra, self._follow_object.dec
            az, alt = self._follow_object.az, self._follow_object.alt
            dt = self._observer.date

            # logging.debug("follow", extra={'clientip': 'localhost'})
            # logging.debug("ra: %12s, dec: %12s, time: %20s", ra, dec, dt, extra={'clientip': 'localhost'})
            # logging.debug("az: %12s, alt: %12s, time: %20s", az, alt, dt, extra={'clientip': 'localhost'})

            self._move_to(az / ephem.degree, alt / ephem.degree)
            sleep(.1)

    def _uncalibrate_motors(self, extra={'clientip': 'localhost'}):
        self.calibration_data = dict()
        for name, motor in self._motors.iteritems():
            motor.steps_per_rev = 0
            self.calibration_data[name] = []

    def _set_calibration_marker(self, extra={'clientip': 'localhost'}):
        for name, motor in self._motors.iteritems():
            self.calibration_data[name].append((motor.angle, motor.steps))
        logging.debug("calibration %s", self.calibration_data, extra=extra)

    def _calibrate_motors(self, extra={'clientip': 'localhost'}):
        for name, motor in self._motors.iteritems():
            steps_list =[]
            for comb in combinations(xrange(len(self.calibration_data[name])),2):
                try:
                    steps_per_rev = 360 * \
                    (self.calibration_data[name][comb[1]][1]-self.calibration_data[name][comb[0]][1]) / \
                    (self.calibration_data[name][comb[1]][0]-self.calibration_data[name][comb[0]][0])

                    steps_list.append(steps_per_rev)
                except:
                    pass
            try:
                motor.steps_per_rev = int(sum(steps_list)/len(steps_list))
                logging.debug("calibrated %s to steps per revolution: %d",
                              motor.name, motor.steps_per_rev, extra=extra)
            except:
                pass


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
              "alt": Motor("Altitude motor", map(int, args["altitude_pins"].split(",")),
                           min_angle=0., max_angle=90)}
    server = TelescopeServer((args["host"], args["port"]), motors, TelescopeRequestHandler)

    # terminate with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
