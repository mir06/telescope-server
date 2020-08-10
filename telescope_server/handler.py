# -*- encoding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmx.de>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
Implements a telescope server that can handle Stellarium Telescope control (goto/send
current position) plus a manual control for calibrating physical equipment.

You have to implement a controller class that actually manages that
physical equipment. This class shall be derived from BaseController
(basecontroller.py) and you will overwrite the necessary member functions
"""

# Standard Library
import logging
import socketserver
import subprocess

# from string import replace
from time import sleep, time

# Third party
from bitstring import ConstBitStream

# First party
from telescope_server.protocol import command


class TelescopeRequestHandler(socketserver.BaseRequestHandler):
    def _stellarium2coords(self, ra_uint, dec_int):
        return (ra_uint * 12.0 / 2147483648, dec_int * 90.0 / 1073741824)

    def _coords2stellarium(self, ra, dec):
        return (int(ra * (2147483648 / 12.0)), int(dec * (1073741824 / 90.0)))

    def _unpack_stellarium(self, data):
        """
        unpack goto data sent by stellarium
        """
        # time
        data.read("intle:64")
        # ra
        ant_pos = data.bitpos
        data.read("hex:32")
        data.bitpos = ant_pos
        ra_uint = data.read("uintle:32")
        # dec
        ant_pos = data.bitpos
        data.read("hex:32")
        data.bitpos = ant_pos
        dec_int = data.read("intle:32")

        return self._stellarium2coords(ra_uint, dec_int)

    def _pack_stellarium(self, ra, dec):
        """
        pack given ra (h), dec (degree) together with current time
        for sending to stellarium
        """
        ra_s, dec_s = self._coords2stellarium(ra, dec)
        msize = "0x1800"
        mtype = "0x0000"
        localtime = ConstBitStream(f"int:64={int(1e6*time())}")
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
        while True:
            data0 = ""
            # set the socket time-out
            # if nothing is received within this time just send data to the
            # stellarium server
            self.request.settimeout(0.01)
            try:
                data0 = self.request.recv(160)
                logging.debug("Input")
                logging.debug(data0)
                data = ConstBitStream(bytes=data0, length=160)
                logging.debug(data)
                data.read("intle:16")
                mtype = data.read("intle:16")
                logging.debug("mtype: %s ", mtype)
                if mtype == command.STELLARIUM:
                    # stellarium telescope client
                    ra, dec = self._unpack_stellarium(data)
                    self.server.controller.goto(ra, dec)

                elif mtype == command.LOCATION:
                    # set observer lon/lat/alt given as three floats
                    lon, lat, alt = self._unpack_data(data, ["floatle:32"] * 3)
                    try:
                        self.server.controller.set_observer(lon, lat, alt)
                    except Exception:
                        logging.error("could not set location")
                    break

                elif mtype == command.START_CAL:
                    # start calibration
                    try:
                        self.server.controller.start_calibration()
                    except Exception:
                        logging.error("cannot start calibration")
                    break

                elif mtype == command.STOP_CAL:
                    # stop calibration
                    try:
                        self.server.controller.stop_calibration()
                    except Exception:
                        logging.error("cannot stop calibration")
                    break

                elif mtype == command.MAKE_STEP:
                    # make steps (azimuthal/altitudal steps given as two small integers)
                    azimuth_steps, altitude_steps = self._unpack_data(
                        data, ["intle:16"] * 2
                    )
                    try:
                        self.server.controller.make_step(azimuth_steps, altitude_steps)
                    except Exception:
                        logging.error("cannot make steps")
                    break

                elif mtype == command.START_MOT:
                    # start or stop motor
                    motor_id, action, direction = self._unpack_data(
                        data, ["intle:16"] * 3
                    )
                    self.server.controller.start_stop_motor(motor_id, action, direction)
                    break

                elif mtype == command.SET_ANGLE:
                    # set the angle of the motors to given object_id (small integer)
                    # this shall be defined in the controller class
                    object_id = self._unpack_data(data, "intle:16")
                    try:
                        self.server.controller.set_object(object_id)
                    except Exception:
                        logging.error("cannot set controller to given object")
                    break

                elif mtype == command.TOGGLE_TRACK:
                    # toggle tracking (earth rotation compensation)
                    try:
                        self.server.controller.toggle_tracking()
                    except Exception:
                        logging.error("cannot toggle tracking")
                    break

                elif mtype == command.APPLY_OBJECT:
                    # apply the angle of the motors to given object_id (small integer)
                    # this shall be defined in the controller class
                    try:
                        self.server.controller.apply_object()
                    except Exception:
                        logging.error("cannot apply controller to given object")
                    break

                elif mtype == command.RAS_SHUTDOWN:
                    # Shutdown Rasberry
                    try:
                        subprocess.run("halt", shell=True)
                    except Exception:
                        logging.error("cannot shutdown rasberry")
                    break

                elif mtype == command.RAS_RESTART:
                    # Reboot Rasberry
                    try:
                        subprocess.run("reboot", shell=True)
                    except Exception:
                        logging.error("cannot restart rasberry")
                    break

                elif mtype == command.TEL_RESTART:
                    # Reboot Rasberry
                    try:
                        subprocess.run(
                            "systemctl restart telescoped.service", shell=True
                        )
                    except Exception:
                        logging.error("cannot restart telescope-server")
                    break

                elif mtype == command.STATUS:
                    # get the status of the controller by status_code (small integer)
                    status_code = self._unpack_data(data, "intle:16")
                    try:
                        response = self.server.controller.get_status(status_code)
                        logging.debug("response: %s ", response)
                        self.request.sendall(response.encode())
                        sleep(0.01)
                    except Exception as exc:
                        logging.error(f"{exc} cannot get status of controller")
                    break

            except Exception:
                # no data received
                # send current position
                ra, dec = self.server.controller.current_pos()
                sdata = self._pack_stellarium(ra, dec)
                try:
                    self.request.send(sdata.bytes)
                except Exception:
                    pass
                sleep(0.5)


class TelescopeServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # Ctrl-C will cleanly kill all spawned threads
    daemon_threads = True
    # much faster rebinding
    allow_reuse_address = True

    def __init__(self, server_address, controller, RequestHandler):
        socketserver.TCPServer.__init__(self, server_address, RequestHandler)
        self.controller = controller
