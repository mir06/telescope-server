# -*- coding: utf-8 -*-
# Copyright: Armin Leuprecht <mir@mur.at> and Stephan Burger <stephan101@gmail.com>
# License: GNU GPL version 3; http://www.gnu.org/licenses/gpl.txt

"""
the client classes for controlling the telescope server manually
"""

import os
import sys
from time import sleep
from math import sqrt, ceil

try:
    from gi.repository import Gtk
    from gi.repository import Gdk
except:
    sys.exit(1)

import socket
from bitstring import ConstBitStream

from lxml import etree
from threading import Thread

# append search path
from telescope.common.protocol import status, command

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
        sock.settimeout(1.0)
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
    
    def get_curr_steps(self):
        response = self.get_status(status.CURR_STEPS)
        return response.split(':')[-1]
        
       
    def get_visible_objects(self):
        response = self.get_status(status.VISIBLE_OBJ)
        return response.split(',')

    def get_number_of_sighted_objects(self):
        response = self.get_status(status.SIGHTED_OBJ)
        return response

    def set_location(self, lon, lat, alt):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.LOCATION)
        data += ConstBitStream('floatle:32=%f' % lon)
        data += ConstBitStream('floatle:32=%f' % lat)
        data += ConstBitStream('floatle:32=%f' % alt)
        tmp = self._make_connection(data)

    def start_calibration(self):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.START_CAL)
        tmp = self._make_connection(data)

    def stop_calibration(self):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.STOP_CAL)
        tmp = self._make_connection(data)

    def start_stop_motor(self, motor_id, action, direction=True):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.START_MOT)
        data += ConstBitStream('intle:16=%d' % motor_id)
        data += ConstBitStream('intle:16=%d' % action)
        data += ConstBitStream('intle:16=%d' % direction)
        tmp = self._make_connection(data)

    def make_step(self, motor_id, direction, steps_per_click):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.MAKE_STEP)
        data += ConstBitStream('intle:16=%d' % (2*(motor_id==0) * (direction-.5) * steps_per_click))
        data += ConstBitStream('intle:16=%d' % (2*(motor_id==1) * (direction-.5) * steps_per_click))
        tmp = self._make_connection(data)

    def set_object(self, obj_id):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.SET_ANGLE)
        data += ConstBitStream('intle:16=%d' % int(obj_id))
        tmp = self._make_connection(data)
        
    def apply_object(self):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.APPLY_OBJECT)
        tmp = self._make_connection(data)

    def toggle_tracking(self):
        data = ConstBitStream('0x1400')
        data += ConstBitStream('intle:16=%d' % command.TOGGLE_TRACK)
        tmp = self._make_connection(data)

class GtkClient(object):
    """
    The GUI to the Telescope-client
    """
    conffile = os.path.join(os.path.expanduser("~"), "telescope.xml")

    def __init__(self):
        """
        initialize the gui
        """
        # set the glade file
        self.gladefile = os.path.join(os.path.dirname(__file__), "ui", "telescope-client.glade")
        self.glade = Gtk.Builder()
        self.glade.add_from_file(self.gladefile)

        # connect signals
        self.glade.connect_signals(self)

        # set the window icon
        self.glade.get_object("main_window").set_icon_from_file(
            os.path.join(os.path.dirname(__file__), "ui", "telescope-client.png"))

        # show images on buttons
        settings = Gtk.Settings.get_default()
        settings.props.gtk_button_images = True

        self.navigation = self.glade.get_object("navigation")
        self.conn_button = self.glade.get_object("connection")
        self.loc_button = self.glade.get_object("location")
        self.cal_button = self.glade.get_object("calibration")
        self.info_button = self.glade.get_object("telescope_info")

        self.location_store = self.glade.get_object("liststore_location")
        self.location_tree = self.glade.get_object("treeview_location")

        self.tracking_switch = self.glade.get_object("tracking_switch")
        self.steps_per_click = self.glade.get_object("steps_per_click")
        
        # connect signals with userdata
        for ind, col in enumerate(self.location_tree.get_columns()):
            col.get_cells()[0].connect("edited", self.onEditCell, (self.location_store, ind))

        # load preferences
        self.read_preferences()

        # show the main window
        self.glade.get_object("main_window").show_all()

        # images / animations for buttons
        self.navigation_buttons = {}
        self.button_images = {}
        for direction in ['right', 'left', 'up', 'down']:
            # buttons
            self.navigation_buttons[direction] = \
                self.glade.get_object("main_%s" % (direction))

            # images (fixed and animated icons)
            im = Gtk.Image()
            im.set_from_file(os.path.join(os.path.dirname(__file__), 
                                          "ui", "%s-animated.gif" % direction))
            im.show()
            self.button_images[direction] = dict()
            self.button_images[direction]["stopped"] = \
                self.glade.get_object("main_%s_arrow" % (direction))
            self.button_images[direction]["started"] = im

        # initialize state variables
        self.movement = [ "", "" ]
        self.direction_key = {
            'right': Gdk.KEY_Right, 'left': Gdk.KEY_Left,
            'up': Gdk.KEY_Up, 'down': Gdk.KEY_Down }
        self.key_direction = {value:key for key, value in self.direction_key.iteritems()}
        
        # start thread that looks if tracking is active or not
        self.tracking_thread = Thread(target=self.check_tracking)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()

        # define css for the object-buttons
        css = """
        GtkButton.selected {
          background-color: red;
          background: red;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


    def check_tracking(self):
        """
        check if telescope server is tracking
        and set the switch accordingly
        """
        while True:
            try:
                tracking = self.connection.get_tracking_status()
                self.tracking_switch.set_active(tracking)
                sleep(1)
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
            self.glade.get_object("steps_per_click").set_value(1)
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
        try:
            for loc in locations.findall("location"):
                # ensure uniqueness
                name = loc.attrib['name']
                lon = float(loc.attrib['lon'])
                lat = float(loc.attrib['lat'])
                alt = float(loc.attrib['alt'])
                if name not in name_list:
                    self.location_store.append([name, lon, lat, alt])
                    if name == self.active_location:
                        # try to set the location (if there is no server just leave it)
                        try:
                            self.connection.set_location(lon, lat, alt)
                            self._location = self.connection.get_location()
                        except:
                            pass
                        # set the active row (must be last line of name_list at this moment)
                        self.location_tree.set_cursor(len(name_list))
                    name_list.append(name)
        except:
            pass

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
    def run(self):
        """
	      Startet die zentrale Warteschleife von Gtk
	      """
        try:
            Gtk.main()
        except KeyboardInterrupt:
            pass
            
    def onDeleteWindow(self, widget, data=None):
        self.write_preferences()
        try:
            Gtk.main_quit()
        except KeyboardInterrupt:
            pass


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
            # some values have been given check connection
            try:
                hostname = self.glade.get_object("hostname").get_text()
                port = int(self.glade.get_object("port").get_value())
                self.connection = Connector(hostname, port)
                label = "connected to %s" % self.connection
            except:
                self.connection = None
                label = "could not connect to server"

        # check the toolbar buttons and hide the dialog
        self.check_widgets()
        dialog.hide()

    def onLocationDialog(self, widget, data=None):
        dialog = self.glade.get_object("location_dialog")
        response = dialog.run()
        if response == 0:
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
                self._location = loc
                label = "set location: %s" % loc
            except:
                label = "could not set location"


        # check the toolbar buttons and hide the dialog
        self.check_widgets()
        dialog.hide()

    def onCalibrationStart(self, button):
        self.connection.start_calibration()
        self._calibrated = False
        self.glade.get_object("apply_object").set_sensitive(False)

    def onCalibrationStop(self, button):
        self.connection.stop_calibration()
        self._calibrated = True
        self._update_spr()
        
    def onApplyObject(self, button):
        """
        add the currently selected object to the list of sighted objects
        """
        self.connection.apply_object()
        # reset all the object buttons
        for btn in self.glade.get_object("object_buttons").get_children():
            ctx = btn.get_style_context()
            ctx.remove_class('selected')
        

    def _update_spr(self):
        spr = self.connection.get_spr()
        self._spr = spr

    def onClickObject(self, button, *data):
        # set the background color of the button to red
        # and all others to gray
        for btn in button.get_parent().get_children():
            ctx = btn.get_style_context()
            if btn == button:
                ctx.add_class('selected')
            else:
                ctx.remove_class('selected')

        obj_id = data[0]
        obj_name = data[1]
        self.connection.set_object(obj_id)
        self.glade.get_object("apply_object").set_sensitive(True)

    def onCalibrationDialog(self, widget, data=None):
        # stop eventually running motors
        self._start_stop_motor('right', force_stop=True)
        self._start_stop_motor('up', force_stop=True)

        # stop tracking
        if self.connection.get_tracking_status():
            self.connection.toggle_tracking()

        # fill the objects' box with visible objects
        visible_objects = self.connection.get_visible_objects()
        n = int(ceil(sqrt(len(visible_objects))))
        nrows = 2*n
        ncols = int(ceil(n/2))
        button_container = self.glade.get_object("object_buttons")
        for nr, obj in enumerate(visible_objects):
            col, row = divmod(nr, ncols)
            obj_id, obj_name = obj.split("-")
            button = Gtk.Button(label=obj_name)
            button.connect("clicked", self.onClickObject, obj_id, obj_name)
            button.show()
            button.set_focus_on_click(True)
            button_container.attach(button, row, col, 1, 1)


        # reveal the calibration box
        revealer = self.glade.get_object("calibration_revealer")
        if revealer.get_reveal_child():
            revealer.set_reveal_child(False)
        else:
            revealer.set_reveal_child(True)
            # also reveal the info box (if it's not already)
            info_revealer = self.glade.get_object("info_revealer")
            if not info_revealer.get_reveal_child():
                self.onInfoDialog(None)


    def _get_info(self, revealer):
        """
        thread that polls info as long as info revealer is shown
        """
        while revealer.get_reveal_child():
            # get information from the server
            try:
                location = self._location
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
                nr = self.connection.get_number_of_sighted_objects()
                self.glade.get_object("calibration_start").set_sensitive(int(nr)>0)
                self.glade.get_object("calibration_stop").set_sensitive(int(nr)>1)
            except:
                nr = "na"

            try:
                spr = self._spr
            except:
                spr = "na/na"

            try:
                curr_steps = self.connection.get_curr_steps()
            except:
                curr_steps = "na/na"

            self.glade.get_object("info_location").set_text(location)
            self.glade.get_object("info_radec").set_text(radec)
            self.glade.get_object("info_azalt").set_text(azalt)
            self.glade.get_object("info_calibrated").set_text(calibrated)
            self.glade.get_object("info_sighted_objects").set_text(nr)
            self.glade.get_object("info_spr").set_text(spr)
            self.glade.get_object("info_curr_steps").set_text(curr_steps)
            sleep(1)
            
    def onInfoDialog(self, widget, data=None):
        """
        toggle infomartion revelaer
        """
        info_revealer = self.glade.get_object("info_revealer")
        # get the current steps per revolution
        spr = self.connection.get_spr()
        self._spr = spr
        if info_revealer.get_reveal_child():
            info_revealer.set_reveal_child(False)
            try:
                self._info_thread.join()
            except:
                pass
        else:
            info_revealer.set_reveal_child(True)
            self._info_thread = Thread(target=self._get_info, args=[info_revealer])
            self._info_thread.daemon = True
            self._info_thread.start()


    def onToggleTracking(self, switch, gparam):
        """
        toggle tracking
        """
        tracking = self.connection.get_tracking_status()
        if switch.get_active() != tracking:
            self.connection.toggle_tracking()


    def _translate_direction(self, direction):
        """
        return tuple to a given direction containing:
        index (0-azimuthal, 1-altitudinal), direction as True,False and the opposite direction
        """
        az = [ "left", "right" ]
        alt = [ "up", "down" ]
        try:
            return 0, direction=="right", az[az.index(direction)-1]
        except:
            return 1, direction=="down", alt[alt.index(direction)-1]

    def _start_stop_motor(self, direction, force_stop=False, cont=False):
        """
        start and stop motors depending on current state
        can be overruled by optional paramters
        and set the according images on the buttons
        parameters:
          force_stop: stop motor if it's running
          cont:       do not stop motor if it's already running in this direction
        """
        # translate simple direction into motor-number, boolean direction
        # and the opposite direction
        index, bool_dir, other_dir = self._translate_direction(direction)

        # stop a motor if it's running
        if force_stop:
            if self.movement[index] != "":
                self.movement[index] = ""
                self.navigation_buttons[direction].set_image(
                    self.button_images[direction]['stopped']
                )
                self.navigation_buttons[other_dir].set_image(
                    self.button_images[other_dir]['stopped']
                )
                self.connection.start_stop_motor(index, False)
                return True
            else:
                return False

        # start or stop a motor depending on the direction it is currently running
        if self.movement[index] != direction:
            self.movement[index] = direction
            self.navigation_buttons[direction].set_image(
                self.button_images[direction]['started']
            )
            self.navigation_buttons[other_dir].set_image(
                self.button_images[other_dir]['stopped']
            )
            self.connection.start_stop_motor(index, True, bool_dir)
        else:
            if not cont:
                self.movement[index] = ""
                self.navigation_buttons[direction].set_image(
                    self.button_images[direction]['stopped']
                )
                self.connection.start_stop_motor(index, False)
        return True


    def onNavigation(self, button, event):
        """
        control the motors manually by button-clicks
        """
        window, direction = Gtk.Buildable.get_name(button).split('_')
        # right click starts/stops motor
        # left click does steps_per_click steps (and stops running motor)
        if event.button == 3:
            self._start_stop_motor(direction)

        elif event.button == 1:
            if not self._start_stop_motor(direction, force_stop=True):
                index, bool_dir, other_dir = self._translate_direction(direction)
                steps_per_click = int(self.glade.get_object("steps_per_click").get_value())
                self.connection.make_step(index, bool_dir, steps_per_click)
                sleep(0.01)

    def onCursorPressed(self, widget, event, data=None):
        """
        control motors by cursor keys (only react when navigation is enabled)
        """
        window = Gtk.Buildable.get_name(widget).split('_')[0]
        if self.navigation.get_sensitive():
            if event.keyval in self.direction_key.values():
                direction = self.key_direction[event.keyval]
                self._start_stop_motor(direction, cont=True)
        return True

    def onCursorReleased(self, widget, event, data=None):
        """
        stop motors when cursur keys are released
        """
        window = Gtk.Buildable.get_name(widget).split('_')[0]
        if self.navigation.get_sensitive():
            if event.keyval in self.direction_key.values():
                direction = self.key_direction[event.keyval]
                index = direction in ["right", "left"]
                self._start_stop_motor(direction)
        return True
