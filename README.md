# telescope-server

A telescope server that runs on the RaspberryPi

The server can be used by the Stellarium Telescope Control plugin for the goto-control
and other clients, e.g. for calibration of the telescope.

The server uses a controller class that actually cummunicates with the two motors that
move the telescope as well as a listener for manual control.

This distribution also contains a client program written in gtk for moving and calibrating
the telescope easily.
