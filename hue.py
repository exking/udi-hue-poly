#!/usr/bin/env python3
""" Phillips Hue Node Server for ISY """

from converters import id_2_addr
try:
    from httplib import BadStatusLine  # Python 2.x
except ImportError:
    from http.client import BadStatusLine  # Python 3.x
import polyinterface as polyglot
from node_types import HueDimmLight, HueWhiteLight, HueColorLight, HueEColorLight
import sys
import phue

LOGGER = polyglot.LOGGER

class Control(polyglot.Controller):
    """ Phillips Hue Node Server """
    
    def __init__(self, poly):
        super().__init__(poly)
        self.name = 'Hue Bridge'
        self.address = 'huebridge'
        self.primary = self.address
        self.discovery = False
        self.started = False
        self.hub = None
        self.lights = None
        LOGGER.info('Started Hue Protocol')
                        
    def start(self):
        """ Initial node setup. """
        # define nodes for settings
        self.connect()
        self.discover()

    def shortPoll(self):
        self.updateNodes()

    def connect(self):
        """ Connect to Phillips Hue Hub """
        # pylint: disable=broad-except
        # get hub settings
        try:
            self.hub = phue.Bridge()
        except phue.PhueRegistrationException:
            LOGGER.error('IP Address OK. Node Server not registered.')
            return False
        except Exception:
            LOGGER.error('Cannot find Hue Bridge')
            return False  # bad ip Addressse:
        else:
            # ensure hub is connectable
            self.lights = self._get_lights()

            if self.lights:
                LOGGER.info('Connection OK')
                return True
            else:
                LOGGER.error('Connect: Failed to read Lights from the Hue Bridge')
                self.hub = None
                return False

    def discover(self, command = {}):
        """ Poll Hue for new lights/existing lights' statuses """
        if self.hub is None or self.discovery == True:
            return True
        self.discovery = True
        LOGGER.info('Starting Hue discovery...')

        self.lights = self._get_lights()
        if not self.lights:
            LOGGER.error('Discover: Failed to read Lights from the Hue Bridge')
            return False
        
        LOGGER.info('{} bulbs found. Checking status and adding to ISY if necessary.'.format(len(self.lights)))

        for lamp_id, data in self.lights.items():
            address = id_2_addr(data['uniqueid'])
            name = data['name']
            
            if not address in self.nodes:
                if data['type'] == "Extended color light":
                    LOGGER.info('Found Extended Color Bulb: {}({})'.format(name, address))
                    self.addNode(HueEColorLight(self, self.address, address, name, lamp_id, data))
                elif data['type'] == "Color Light":
                    LOGGER.info('Found Color Bulb: {}({})'.format(name, address))
                    self.addNode(HueColorLight(self, self.address, address, name, lamp_id, data))
                elif data['type'] == "Color temperature light":
                    LOGGER.info('Found White Ambiance Bulb: {}({})'.format(name, address))
                    self.addNode(HueWhiteLight(self, self.address, address, name, lamp_id, data))
                elif data['type'] == "Dimmable Light":
                    LOGGER.info('Found Dimmable Bulb: {}({})'.format(name, address))
                    self.addNode(HueDimmLight(self, self.address, address, name, lamp_id, data))
                else:
                    LOGGER.info('Found Unsupported {} Bulb: {}({})'.format(data['type'], name, address))
        
        LOGGER.info('Discovery complete')
        self.discovery = False
        return True

    def updateNodes(self):
        self.lights = self._get_lights()
        for node in self.nodes:
            self.nodes[node].updateInfo()

    def updateInfo(self):
        pass

    def _get_lights(self):
        try:
            lights = self.hub.get_light()
        except BadStatusLine:
            LOGGER.error('Hue Bridge returned bad status line.')
            return False
        except phue.PhueRequestTimeout:
            LOGGER.error('Timed out trying to connect to Hue Bridge.')
            return False
        except socket.error:
            LOGGER.error("Can't contact Hue Bridge. " +
                         "Network communication issue.")
            return False
        return lights

    def long_poll(self):
        """ Save configuration every 30 seconds. """
        self.update_config(self.hub_queried)

    drivers = [{ 'driver': 'ST', 'value': 0, 'uom': 2 }]
    """ Driver Details:
    GV1: Connected
    """
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
