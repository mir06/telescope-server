# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

from distutils.core import setup

setup(
    name='telescope',
    version="1.0",
    url="https://github.com/mir06/telescope",
 
    author='Armin Leuprecht',
    author_email='mir@mur.at',
    description='Telescope server and client programs',
    long_description="""
A telescope server that runs on the RaspberryPi

The server can be used by the Stellarium Telescope Control plugin for the goto-control
and other clients, e.g. for calibration of the telescope.

The server uses a controller class that actually cummunicates with the two motors that
move the telescope as well as a listener for manual control.

This distribution also contains a client program written in gtk for moving and calibrating
the telescope easily.
""",
    keywords=['stellarium', 'telescope', 'raspberry pi',],
    license='GPL v3',
    maintainer='Armin Leuprecht',
    maintainer_email='mir@mur.at',
    packages=['telescope', 'telescope.server', 'telescope.client', 'telescope.common'],
    package_dir={'telescope.client': 'telescope/client'},
    package_data={'telescope.client': ['ui/telescope-client.glade',
                                       'ui/*.png', 'ui/*.gif']},
    data_files=[
        # server files
        ('/usr/local/sbin', ['telescope-server']),
        ('/etc/init.d', ['telescope/server/init.d/telescoped']),
        ('/usr/local/etc/default', ['telescope/server/default/telescoped']),
        # client files
        ('/usr/local/share/applications',
         ['telescope/client/desktop/telescope-client.desktop']),
        ('/usr/local/share/icons/hicolor/256x256', ['telescope/client/ui/telescope-client.png'])
    ],
    scripts = ['telescope-client'],
)



