#!/usr/bin/env python3
""" Phillips Hue Node Server for ISY """

from converters import id_2_addr
try:
    from httplib import BadStatusLine  # Python 2.x
except ImportError:
    from http.client import BadStatusLine  # Python 3.x
import polyinterface as polyglot
from node_types import HueDimmLight, HueWhiteLight, HueColorLight, HueEColorLight, HueGroup
import sys
import socket
import phue
import logging

LOGGER = polyglot.LOGGER

class Control(polyglot.Controller):
    """ Phillips Hue Node Server """
    
    def __init__(self, poly):
        super().__init__(poly)
        self.name = 'Hue Bridge'
        self.address = 'huebridge'
        self.primary = self.address
        self.discovery = False
        self.hub = None
        self.lights = None
        self.groups = None
        self.bridge_ip = None
        self.bridge_user = None
        LOGGER.info('Started Hue Protocol')
                        
    def start(self):
        """ Initial node setup. """
        # define nodes for settings
        if 'debug' not in self.polyConfig['customParams']:
            LOGGER.setLevel(logging.INFO)
        self.connect()
        self.discover()

    def stop(self):
        LOGGER.info('Hue NodeServer is stopping')

    def shortPoll(self):
        self.updateNodes()

    def connect(self):
        custom_data_ip = False
        custom_data_user = False
        """ Connect to Phillips Hue Hub """
        # pylint: disable=broad-except
        # get hub settings
        if 'customData' in self.polyConfig:
            if 'bridge_ip' in self.polyConfig['customData']:
                self.bridge_ip = self.polyConfig['customData']['bridge_ip']
                custom_data_ip = True
                LOGGER.info('Bridge IP found in the Database: {}'.format(self.bridge_ip))
            if 'bridge_user' in self.polyConfig['customData']:
                self.bridge_user = self.polyConfig['customData']['bridge_user']
                custom_data_user = True
                LOGGER.info('Bridge Username found in the Database.')
        else:
            LOGGER.info('Custom Data is not found in the DB')

        if 'ip' in self.polyConfig['customParams'] and self.bridge_ip is None:
            self.bridge_ip = self.polyConfig['customParams']['ip']
            LOGGER.info('Custom Bridge IP address specified: {}'.format(self.bridge_ip))
        if 'username' in self.polyConfig['customParams'] and self.bridge_user is None:
            self.bridge_user = self.polyConfig['customParams']['username']
            LOGGER.info('Custom Bridge Username specified: {}'.format(self.bridge_user))

        try:
            self.hub = phue.Bridge( self.bridge_ip, self.bridge_user )
        except phue.PhueRegistrationException:
            LOGGER.error('IP Address OK. Node Server not registered.')
            self.addNotice('Please press the button on the Hue Bridge and restart the node server within 30 seconds')
            return False
        except Exception:
            LOGGER.error('Cannot find Hue Bridge')
            return False  # bad ip Address:
        else:
            # ensure hub is connectable
            self.lights = self._get_lights()

            if self.lights:
                LOGGER.info('Connection OK')
                self.removeNoticesAll()
                if custom_data_ip == False or custom_data_user == False:
                    LOGGER.debug('Saving access credentials to the Database')
                    data = { 'bridge_ip': self.hub.ip, 'bridge_user': self.hub.username }
                    self.saveCustomData(data)
                return True
            else:
                LOGGER.error('Connect: Failed to read Lights from the Hue Bridge')
                self.hub = None
                return False

    def discover(self, command=None):
        """ Poll Hue for new lights/existing lights' statuses """
        if self.hub is None or self.discovery == True:
            return True
        self.discovery = True
        LOGGER.info('Starting Hue discovery...')

        self.lights = self._get_lights()
        if not self.lights:
            LOGGER.error('Discover: Failed to read Lights from the Hue Bridge')
            self.discovery = False
            return False
        
        LOGGER.info('{} bulbs found. Checking status and adding to ISY if necessary.'.format(len(self.lights)))

        for lamp_id, data in self.lights.items():
            address = id_2_addr(data['uniqueid'])
            name = data['name']
            
            if not address in self.nodes:
                if data['type'] == "Extended color light":
                    LOGGER.info('Found Extended Color Bulb: {}({})'.format(name, address))
                    self.addNode(HueEColorLight(self, self.address, address, name, lamp_id, data))
                elif data['type'] == "Color light":
                    LOGGER.info('Found Color Bulb: {}({})'.format(name, address))
                    self.addNode(HueColorLight(self, self.address, address, name, lamp_id, data))
                elif data['type'] == "Color temperature light":
                    LOGGER.info('Found White Ambiance Bulb: {}({})'.format(name, address))
                    self.addNode(HueWhiteLight(self, self.address, address, name, lamp_id, data))
                elif data['type'] == "Dimmable light":
                    LOGGER.info('Found Dimmable Bulb: {}({})'.format(name, address))
                    self.addNode(HueDimmLight(self, self.address, address, name, lamp_id, data))
                else:
                    LOGGER.info('Found Unsupported {} Bulb: {}({})'.format(data['type'], name, address))
        
        self.groups = self._get_groups()
        if not self.groups:
            LOGGER.error('Discover: Failed to read Groups from the Hue Bridge')
            self.discovery = False
            return False
        
        LOGGER.info('{} groups found. Checking status and adding to ISY if necessary.'.format(len(self.lights)))

        for group_id, data in self.groups.items():
            address = 'huegrp'+group_id
            if group_id == '0':
                name = 'All Lights'
            else:
                name = data['name']
            
            if 'lights' in data and len(data['lights']) > 0:
                if not address in self.nodes:
                    LOGGER.info("Found {} {} with {} light(s)".format(data['type'], name, len(data['lights'])))
                    self.addNode(HueGroup(self, self.address, address, name, group_id, data))
            else:
                if address in self.nodes:
                    LOGGER.info("{} {} does not have any lights in it, removing a node".format(data['type'], name))
                    self.delNode(address)
        
        LOGGER.info('Discovery complete')
        self.discovery = False
        return True

    def updateNodes(self):
        if self.hub is None or self.discovery == True:
            return True
        self.lights = self._get_lights()
        self.groups = self._get_groups()
        for node in self.nodes:
            self.nodes[node].updateInfo()
        return True

    def updateInfo(self):
        pass

    def _get_lights(self):
        if self.hub is None:
            return None
        try:
            lights = self.hub.get_light()
        except BadStatusLine:
            LOGGER.error('Hue Bridge returned bad status line.')
            return None
        except phue.PhueRequestTimeout:
            LOGGER.error('Timed out trying to connect to Hue Bridge.')
            return None
        except socket.error:
            LOGGER.error("Can't contact Hue Bridge. " +
                         "Network communication issue.")
            return None
        return lights

    def _get_groups(self):
        if self.hub is None:
            return None
        try:
            groups = self.hub.get_group()
        except BadStatusLine:
            LOGGER.error('Hue Bridge returned bad status line.')
            return None
        except phue.PhueRequestTimeout:
            LOGGER.error('Timed out trying to connect to Hue Bridge.')
            return None
        except socket.error:
            LOGGER.error("Can't contact Hue Bridge. " +
                         "Network communication issue.")
            return None
        return groups

    drivers = [{ 'driver': 'ST', 'value': 0, 'uom': 2 }]
    commands = {'DISCOVER': discover}
    id = 'HUEBR'


if __name__ == "__main__":
    try:
        """
        Grab the "HUE" variable from the .polyglot/.env file. This is where
        we tell it what profile number this NodeServer is.
        """
        poly = polyglot.Interface("Hue")
        poly.start()
        hue = Control(poly)
        hue.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
