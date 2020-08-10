#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt
"""
Implements a telescope server that can handle Stellarium Telescope control
(goto/send current position) plus a manual control for calibrating physical
equipment.

You have to implement a controller class that actually manages that
physical equipment. This class shall be derived from BaseController
(basecontroller.py) and you will overwrite the necessary member functions
"""

# Standard Library
import argparse
import importlib
import logging
import os
import pkgutil
import sys

# First party
import telescope_server.plugins as pl

from telescope_server import handler


def getargs():
    parser = argparse.ArgumentParser(description="Telescope Server")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=os.environ.get("PORT", 10000))
    parser.add_argument(
        "--controller",
        default=os.environ.get("CONTROLLER", "telescope_server.controller"),
        help="module name that implements the Controller class",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOGLEVEL", "Error"),
        help="set logging level",
    )
    parser.add_argument(
        "--log-file",
        default=os.environ.get("LOGFILE", "/var/log/telescoped.log"),
        help="set the log-filename",
    )
    args = parser.parse_args(sys.argv[1:])
    return vars(args)


def run(test=None):

    args = getargs()

    # set logging level
    numeric_level = getattr(logging, args["log_level"].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args['log_level']}")

    logging.basicConfig(
        filename=args["log_file"],
        level=numeric_level,
        format="%(levelname)s: %(asctime)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    controller_module = importlib.import_module(args["controller"])
    controller = controller_module.Controller()

    server = handler.TelescopeServer(
        (args["host"], args["port"]), controller, handler.TelescopeRequestHandler
    )

    # load plugins and generate instance with the controller
    plugins = {}
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=pl.__path__, prefix=pl.__name__ + "."
    ):
        module = importlib.import_module(modname)
        name = modname.split(".")[-1]
        try:
            plugins[name] = module.__getattribute__(name.capitalize())(controller)
            logging.info(f"plugin loaded: {name} ({module.__doc__.strip()})")
        except Exception:
            pass

    # terminate with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    run()
