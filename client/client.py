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

sys.path.append("../common")

import socket
from bitstring import ConstBitStream

from lxml import etree
from threading import Thread

from protocol import status, command
from time import sleep

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

    def _make_connection(self, data):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.hostname, self.port))
        data += ConstBitStream('int:%d=0' % (160-data.len))
        try:
            sock.sendall(data.tobytes())
            response = sock.recv(1024)
            return response
        finally:
            sock.close()

    def get_status(self, status_code):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.STATUS)
        data += ConstBitStream('intle:16=%d' % status_code)
        response = self._make_connection(data)
        return response

    def get_location(self):
        return self.get_status(status.LOCATION)

    def get_radec(self):
        return self.get_status(status.RADEC)

    def get_azalt(self):
        return self.get_status(status.AZALT)

    def get_calibration_status(self, boolean=True):
        response = self.get_status(status.CALIBRATED)
        if boolean:
            return response.endswith("YES")
        else:
            return response.split()[-1]

    def get_tracking_status(self, boolean=True):
        response = self.get_status(status.TRACKING)
        if boolean:
            return response.endswith("YES")
        else:
            return response.split()[-1]

    def get_spr(self):
        response = self.get_status(status.SPR)
        return response.split(':')[-1]

    def set_location(self, lon, lat, alt):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.LOCATION)
        data += ConstBitStream('floatle:32=%f' % lon)
        data += ConstBitStream('floatle:32=%f' % lat)
        data += ConstBitStream('floatle:32=%f' % alt)
        tmp = self._make_connection(data)

    def toggle_tracking(self):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.TOGGLE_TRACK)
        tmp = self._make_connection(data)

class Client(object):
    """
    The GUI to the Telescope-client
    """
    conffile = os.path.join(os.path.expanduser("~"), "telescope.xml")

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

        # reference some important wigdets
        self.statusbar = self.glade.get_object("statusbar")

        self.navigation = self.glade.get_object("navigation")
        self.conn_button = self.glade.get_object("connection")
        self.loc_button = self.glade.get_object("location")
        self.cal_button = self.glade.get_object("calibration")
        self.info_button = self.glade.get_object("telescope_info")

        self.location_store = self.glade.get_object("liststore_location")
        self.location_tree = self.glade.get_object("treeview_location")

        self.tracking_switch = self.glade.get_object("tracking_switch")

        # connect signals with userdata
        for ind, col in enumerate(self.location_tree.get_columns()):
            col.get_cells()[0].connect("edited", self.onEditCell, (self.location_store, ind))

        # load preferences
        self.read_preferences()

        # start thread that looks if tracking is active or not
        self.tracking_thread = Thread(target=self.check_tracking)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()

        # show the main window
        self.glade.get_object("main_window").show_all()


    def check_tracking(self):
        """
        check if telescope server is tracking
        and set the switch accordingly
        """
        while True:
            try:
                tracking = self.connection.get_tracking_status()
                self.tracking_switch.set_active(tracking)
                sleep(10)
            except:
                sleep(60)

    def write_preferences(self):
        """
        write the current configuration
        """
        root = etree.Element("config")
        server = etree.Element("server")
        root.append(server)
        try:
            server.set('hostname', self.connection.hostname)
            server.set('port', "%s" % self.connection.port)
        except:
            pass

        locations = etree.Element("locations")
        root.append(locations)
        for row in self.location_store:
            if row[0]:
                location = etree.Element("location")
                location.set("name", row[0])
                location.set("lon", "%f" % row[1])
                location.set("lat", "%f" % row[2])
                location.set("alt", "%f" % row[3])
                locations.append(location)

        try:
            active = self.active_location
            active_location = etree.Element("active_location")
            active_location.set("location", active)
            locations.append(active_location)
        except:
            pass

        string = etree.tostring(root, pretty_print=True)
        f = open(self.conffile, 'w')
        f.write(string)
        f.close()

    def read_preferences(self):
        """
        read the last configuration and apply it to the widgets
        """
        try:
            root = etree.parse(self.conffile).getroot()
        except:
            root = etree.Element("config")

        # server
        server = root.find("server")
        try:
            hostname = server.attrib['hostname']
            port = int(server.attrib['port'])
            self.connection = Connector(hostname, port)
            self.glade.get_object("hostname").set_text(hostname)
            self.glade.get_object("port").set_value(port)
        except:
            pass

        # get locations
        locations = root.find("locations")
        try:
            active = locations.find("active_location")
            self.active_location = active.attrib['location']
        except:
            self.active_location = ""

        name_list = []
        for loc in locations.findall("location"):
            # ensure uniqueness
            name = loc.attrib['name']
            lon = float(loc.attrib['lon'])
            lat = float(loc.attrib['lat'])
            alt = float(loc.attrib['alt'])
            if name not in name_list:
                self.location_store.append([name, lon, lat, alt])
                if name == self.active_location:
                    self.connection.set_location(lon, lat, alt)
                    # set the active row (must be last line of name_list at this moment)
                    self.location_tree.set_cursor(len(name_list))
                name_list.append(name)


        self.check_widgets()

    def check_widgets(self):
        try:
            location = self.connection.get_location()
            # connection to server thus enable location button
            self.loc_button.set_sensitive(True)
            self.info_button.set_sensitive(True)
            if location != "0:00:00.0 / 0:00:00.0 / 0.0":
                # location properly set thus enable calibration button
                self.cal_button.set_sensitive(True)
            else:
                self.cal_button.set_sensitive(False)

            # enable navigation
            calibrated = self.connection.get_calibration_status()
            if calibrated:
                self.navigation.set_sensitive(True)
            else:
                self.navigation.set_sensitive(False)

            # set connected button image to connected
            icon = "gtk-connect"
        except:
            # set disconnected connection icon
            # disable location and calibration icon and navigation area
            icon = "gtk-disconnect"
            self.loc_button.set_sensitive(False)
            self.cal_button.set_sensitive(False)
            self.info_button.set_sensitive(False)
            self.navigation.set_sensitive(False)

        self.conn_button.set_stock_id(icon)


    def onEditCell(self, widget, path, new_text, data):
        """
        edit text in cell
        """
        liststore, column = data

        # ensure uniqueness of name
        if column == 0:
            for i in xrange(len(liststore)):
                if i != path and new_text == liststore[i][column]:
                    return
            liststore[path][column] = new_text
            if new_text:
                # if there is a valid text reenable "add button"
                self.glade.get_object("location_add").set_sensitive(True)
        else:
            # the three other cells are floats
            try:
                liststore[path][column] = float(new_text)
            except ValueError:
                pass
        return

    def onDeleteWindow(self, widget, data=None):
        self.write_preferences()
        Gtk.main_quit()

    def onLocationAdd(self, button):
        """
        add a new location but only if all locations have a valid name
        (to ensure that not more than one new location is created)
        """
        for entry in self.location_store:
            if not entry[0]:
                return

        self.location_store.append()
        button.set_sensitive(False)

    def onLocationDelete(self, button):
        """
        delete the selected item (if any)
        """
        try:
            selection = self.location_tree.get_selection()
            model, treeiter = self.location_tree.get_selection().get_selected()
            model.remove(treeiter)
        except:
            pass
        return

    def onConnectionDialog(self, widget, data=None):
        dialog = self.glade.get_object("connection_dialog")
        response = dialog.run()
        if response == 0:
            context_id = self.statusbar.get_context_id("info")
            # some values have been given check connection
            try:
                hostname = self.glade.get_object("hostname").get_text()
                port = int(self.glade.get_object("port").get_value())
                self.connection = Connector(hostname, port)
                label = "connected to %s" % self.connection
            except:
                self.connection = None
                label = "could not connect to server"

            self.statusbar.push(context_id, label)

        # check the toolbar buttons and hide the dialog
        self.check_widgets()
        dialog.hide()

    def onLocationDialog(self, widget, data=None):
        dialog = self.glade.get_object("location_dialog")
        response = dialog.run()
        if response == 0:
            context_id = self.statusbar.get_context_id("info")
            try:
                model, treeiter = self.location_tree.get_selection().get_selected()
                self.active_location = model[treeiter][0]

                # send location to server
                self.connection.set_location(
                    model[treeiter][1],
                    model[treeiter][2],
                    model[treeiter][3])

                # get formatted location
                loc = self.connection.get_location()
                label = "set location: %s" % loc
            except:
                label = "could not set location"

            self.statusbar.push(context_id, label)

        # check the toolbar buttons and hide the dialog
        self.check_widgets()
        dialog.hide()

    def onCalibrationDialog(self, widget, data=None):
        pass

    def onInfoDialog(self, widget, data=None):
        dialog = self.glade.get_object("info_dialog")
        # get information from the server
        try:
            location = self.connection.get_location()
        except:
            location = "No location information"

        try:
            radec = self.connection.get_radec()
        except:
            radec = "na/na"

        try:
            azalt = self.connection.get_azalt()
        except:
            azalt = "na/na"

        try:
            calibrated = self.connection.get_calibration_status(False)
        except:
            calibrated = "na"

        try:
            tracking = self.connection.get_tracking_status(False)
        except:
            tracking = "na"

        try:
            spr = self.connection.get_spr()
        except:
            spr = "na/na"

        self.glade.get_object("info_location").set_text(location)
        self.glade.get_object("info_radec").set_text(radec)
        self.glade.get_object("info_azalt").set_text(azalt)
        self.glade.get_object("info_calibrated").set_text(calibrated)
        self.glade.get_object("info_tracking").set_text(tracking)
        self.glade.get_object("info_spr").set_text(spr)

        response = dialog.run()
        dialog.hide()

    def onToggleTracking(self, switch, gparam):
        """
        toggle tracking
        """
        tracking = self.connection.get_tracking_status()
        if switch.get_active() != tracking:
            self.connection.toggle_tracking()

if __name__ == "__main__":
    client = Client()
    Gtk.main()
