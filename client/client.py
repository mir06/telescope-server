#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
the client for controlling the telescope server manually (extenstion to the stellarium features)
"""

import os
import sys
try:
    from gi.repository import Gtk
except:
    sys.exit(1)

import socket
from bitstring import ConstBitStream

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

    def get_location(self):
        print "get location"


class Client(object):
    """
    The GUI to the Telescope-client
    """


    def __init__(self):
        """
        initialize the gui
        """
        # set the glade file
        self.gladefile = os.path.join("ui", "client.glade")
        self.glade = Gtk.Builder()
        self.glade.add_from_file(self.gladefile)

        # connect signals
        self.glade.connect_signals(self)

        # show images on buttons
        settings = Gtk.Settings.get_default()
        settings.props.gtk_button_images = True

        # show the main window
        # main_window = self.glade.get_object("main_window")
        # main_window.set_title("Telescope Control")
        # main_window.show_all()
        self.glade.get_object("main_window").show_all()

    def check_toolbar_buttons(self):
        conn_button = self.glade.get_object("connection")
        loc_button = self.glade.get_object("location")
        cal_button = self.glade.get_object("calibration")

        try:
            print self.connection()
 #           location = self.connection.get_location()
            icon = self.glade.get_object("connected_icon")
        except:
            # set disconnected connection icon
            # disable location and calibration icon
            icon = self.glade.get_object("disconnected_icon")
            loc_button.set_sensitive(False)
            cal_button.set_sensitive(False)

        conn_button.set_icon_widget(icon)



    def onDeleteWindow(self, widget, data=None):
        Gtk.main_quit()

    def onConnectionDialog(self, widget, data=None):
        dialog = self.glade.get_object("connection_dialog")
        response = dialog.run()
        if response == 0:
            button = self.glade.get_object("connection")
            # some values have been given check connection
            try:
                hostname = self.glade.get_object("hostname").get_text()
                port = int(self.glade.get_object("port").get_value())
                self.connection = Connector(hostname, port)
            except:
                pass

        # check the toolbar buttons and hide the dialog
        self.check_toolbar_buttons()
        dialog.hide()



    def onConnectionCancel(self, widget, data=None):
        print widget

    def onConnectionConnect(self, widget, data=None):
        print widget

if __name__ == "__main__":
    client = Client()
    Gtk.main()
