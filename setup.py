# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

from distutils.core import setup
import platform

# check if this is windows --> no data-files installation
data_files = platform.system() == 'Windows' and [] or \
             [
                 # server files
                 ('/usr/local/sbin', ['telescope-server']),
                 ('/etc/init.d', ['telescope/server/init.d/telescoped']),
                 ('/usr/local/etc/default', ['telescope/server/default/telescoped']),

                 # client files
                 ('/usr/local/share/applications',
                  ['telescope/client/desktop/telescope-client.desktop']),
                 ('/usr/local/share/icons/hicolor/256x256/apps',
                  ['telescope/client/icons/256x256/telescope-client.png']),
                 ('/usr/local/share/icons/hicolor/128x128/apps',
                  ['telescope/client/icons/128x128/telescope-client.png']),
                 ('/usr/local/share/icons/hicolor/64x64/apps',
                  ['telescope/client/icons/64x64/telescope-client.png']),
                 ('/usr/local/share/icons/hicolor/48x48/apps',
                  ['telescope/client/icons/48x48/telescope-client.png']),
                 ('/usr/local/share/icons/hicolor/32x32/apps',
                  ['telescope/client/icons/32x32/telescope-client.png']),
                 ('/usr/local/share/icons/hicolor/24x24/apps',
                  ['telescope/client/icons/24x24/telescope-client.png']),
             ]

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
    download_url = 'https://github.com/mir06/telescope/tarball/1.0',
    maintainer='Armin Leuprecht',
    maintainer_email='mir@mur.at',
    packages=['telescope', 'telescope.server', 'telescope.server.plugins',
              'telescope.client', 'telescope.common'],
    package_dir={'telescope.client': 'telescope/client'},
    package_data={'telescope.client': ['ui/telescope-client.glade',
                                       'ui/*.png', 'ui/*.gif']},
    scripts = ['telescope-client'],
    data_files = data_files,
)



