#! /usr/bin/env python
# -*- encoding: utf-8 -*-

"""
Implements a telescope server that can handle Stellarium Telescope control (goto/send current position)
plus a manual control for calibrating physical equipment.

You have to implement a controller class that actually manages that physical equipment. This class shall
be derived from BaseController (basecontroller.py) and you will overwrite the necessary member functions
"""

import SocketServer
import sys
import argparse
import logging
from string import replace
from time import time, sleep
from bitstring import ConstBitStream

def getopts():
    parser = argparse.ArgumentParser(description="Telescope Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--controller", default="controller",
                        help="module name that implements the Controller class")
    parser.add_argument("--log-level", default="DEBUG",
                        help="set logging level")
    args = parser.parse_args(sys.argv[1:])
    return vars(args)

class TelescopeRequestHandler(SocketServer.BaseRequestHandler):
    def _stellarium2coords(self, ra_uint, dec_int):
        return (ra_uint*12./2147483648, dec_int*90./1073741824)

    def _coords2stellarium(self, ra, dec):
        return (int(ra*(2147483648/12.0)), int(dec*(1073741824/90.0)))

    def _unpack_stellarium(self, data):
        """
        unpack goto data sent by stellarium
        """
        # time
        mtime = data.read('intle:64')
        # ra
        ant_pos = data.bitpos
        ra = data.read('hex:32')
        data.bitpos = ant_pos
        ra_uint = data.read('uintle:32')
        # dec
        ant_pos = data.bitpos
        dec = data.read('hex:32')
        data.bitpos = ant_pos
        dec_int = data.read('intle:32')

        return self._stellarium2coords(ra_uint, dec_int)

    def _pack_stellarium(self, ra, dec):
        """
        pack given ra (h), dec (degree) together with current time for sending to stellarium
        """
        ra_s, dec_s = self._coords2stellarium(ra, dec)
        msize = '0x1800'
        mtype = '0x0000'
        localtime = ConstBitStream(replace('int:64=%r' % time(), '.', ''))
        sdata = ConstBitStream(msize) + ConstBitStream(mtype)
        sdata += ConstBitStream(intle=localtime.intle, length=64)
        sdata += ConstBitStream(uintle=ra_s, length=32)
        sdata += ConstBitStream(intle=dec_s, length=32)
        sdata += ConstBitStream(intle=0, length=32)
        return sdata

    def _unpack_data(self, data, format):
        """
        return unpacked data of type described by format
        if format is a simple string one value is returned
        if format is an iteratable a tuple of values is returned
        """
        if isinstance(format, str):
            ret = data.read(format)
        else:
            ret = []
            for f in format:
                ret.append(data.read(f))
            ret = tuple(ret)
        return ret

    def handle(self):
        """
        handle requests
        """
        logging.debug("connection established from %s", self.client_address[0])
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
                    ra, dec = self._unpack_stellarium(data)
                    logging.info("goto ra: %12s, dec: %12s", ra, dec)
                    self.server.controller.goto(ra, dec)

                elif mtype == 1:
                    # set observer lon/lat/alt given as three floats
                    lon, lat, alt = self._unpack_data(data, ['floatle:32']*3)
                    logging.debug("location: %f / %f / %f", lon, lat, alt)
                    try:
                        response = self.server.controller.set_observer(lon, lat, alt)
                        self.request.sendall(response)
                    except:
                        logging.error("could not set location")
                    break

                elif mtype == 2:
                    # start calibration
                    logging.debug("start calibration")
                    try:
                        response = self.server.controller.start_calibration()
                        self.request.sendall(response)
                    except:
                        logging.error("cannot start calibration")
                    break

                elif mtype == 3:
                    # stop calibration
                    logging.debug("stop calibration")
                    try:
                        response = self.server.controller.stop_calibration()
                        self.request.sendall(response)
                    except:
                        logging.error("cannot stop calibration")
                    break

                elif mtype == 4:
                    # make steps (azimuthal/altitudal steps given as two small integers)
                    azimuth_steps, altitude_steps = self._unpack_data(data, ['intle:16']*2)
                    logging.debug("az/alt-steps: %d / %d", azimuth_steps, altitude_steps)
                    try:
                        response = self.server.controller.make_step(azimuth_steps, altitude_steps)
                        self.request.sendall(response)
                    except:
                        logging.error("cannot make steps")
                    break

                elif mtype == 5:
                    # set the angle of the motors to given object_id (small integer)
                    # this shall be defined in the controller class
                    object_id = self._unpack_data(data, 'intle:16')
                    logging.debug("set controller to object: %d", object_id)
                    try:
                        response = self.server.controller.set_object(object_id)
                        self.request.sendall(response)
                    except:
                        logging.error("cannot set controller to given object")
                    break

                elif mtype == 6:
                    # toggle tracking (earth rotation compensation)
                    logging.debug("toggle tracking")
                    try:
                        response = self.server.controller.toggle_tracking()
                        self.request.sendall(response)
                    except:
                        logging.error("cannot toggle tracking")
                    break

                elif mtype == 99:
                    # get the status of the controller by status_code (small integer)
                    status_code = self._unpack_data(data, 'intle:16')
                    logging.debug("get status of controller, status code: %d", status_code)
                    # try:
                    response = self.server.controller.get_status(status_code)
                    self.request.sendall(response)
                    # except:
                    #     logging.error('cannot get status of controller')
                    # break


            else:
                # send current position
                ra, dec = self.server.controller.current_pos()
                sdata = self._pack_stellarium(ra, dec)
                logging.info("sending data: ra: %12s, dec: %12s", ra, dec)
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

    def __init__(self, server_address, controller, RequestHandler):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandler)
        self.controller = controller

if __name__ == "__main__":
    args = getopts()

    # set logging level
    numeric_level = getattr(logging, args["log_level"].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logging.basicConfig(filename="telescope.log",
                        level=numeric_level,
                        format="%(levelname)s: %(asctime)s %(message)s",
                        datefmt='%Y-%m-%d %H:%M:%S')

    controller_module = __import__(args['controller'])
    controller = controller_module.Controller()

    server = TelescopeServer((args["host"], args["port"]), controller, TelescopeRequestHandler)

    # terminate with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
