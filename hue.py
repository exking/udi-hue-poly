#!/usr/bin/env python3
""" Phillips Hue Node Server for ISY """

from converters import id_2_addr
try:
    from httplib import BadStatusLine  # Python 2.x
except ImportError:
    from http.client import BadStatusLine  # Python 3.x
import polyinterface as polyglot
from node_types import HueColorLight
import sys
import phue

LOGGER = polyglot.LOGGER

class Control(polyglot.Controller):
    """ Phillips Hue Node Server """
    
    def __init__(self, poly):
        super(Control, self).__init__(poly)    
        self.name = 'Hue Bridge'
        self.address = 'huebridge'
        self.primary = self.address
        self.discovery = False
        self.started = False
        self.hub = None
        LOGGER.info('Started Hue Protocol')
                        
    def start(self):
        """ Initial node setup. """
        # define nodes for settings
        self.connect()
        self.discover()

    def shortPoll(self):
        """
        Overridden shortPoll. It is imperative that you super this if you override it
        as the threading.Timer loop is in the parent method.
        """
        self.updateNodes()

    def connect(self):
        """ Connect to Phillips Hue Hub """
        LOGGER.debug('Connect method called')
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
            api = self._get_api()

            if api:
                self.setDriver('ST', 1)
                return True
            else:
                self.hub = None
                return False

    def discover(self, command = {}):
        """ Poll Hue for new lights/existing lights' statuses """
        if self.hub is None or self.discovery == True:
            return True
        self.discovery = True
        LOGGER.info('Starting Hue discovery...')

        api = self._get_api()
        if not api:
            return False
        devices = api['lights']
        
        LOGGER.info('{} bulbs found. Checking status and adding to ISY if necessary.'.format(len(devices)))

        for lamp_id, data in devices:
            address = id_2_addr(data['uniqueid'])
            name = data['name']
            
            if not address in self.nodes:
                if data['type'] == "Extended color light" or data['type'] == "Color Light":
                    LOGGER.debug('Type: {}'.format(data['type']))
                    LOGGER.info('Found Color Bulb: {}({})'.format(name, address))
                    self.addNode(HueColorLight(self, self.address, address, name, lamp_id, data))
                elif data['type'] == "Color temperature light":
                    LOGGER.info('Found White Ambiance Bulb: {}({})'.format(name, address))
                elif data['type'] == "Dimmable Light":
                    LOGGER.info('Found Dimmable Bulb: {}({})'.format(name, address))
                else:
                    LOGGER.info('Found Unsupported Bulb: {}({})'.format(name, address))
        
        LOGGER.info('Discovery complete')
        self.discovery = False
        return True

    def updateNodes(self):
        for node in self.nodes:
            self.nodes[node].updateInfo()

    def updateInfo(self):
        pass

    def _get_api(self):
        """ get hue hub api data. """
        try:
            api = self.hub.get_api()
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
        return api

    def long_poll(self):
        """ Save configuration every 30 seconds. """
        self.update_config(self.hub_queried)

    drivers = [{ 'driver': 'ST', 'value': 0, 'uom': 2 }]
    """ Driver Details:
    GV1: Connected
    """
    _commands = {'DISCOVER': discover}
    node_def_id = 'HUB'


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
