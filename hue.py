#!/usr/bin/env python3
""" Phillips Hue Node Server for ISY """

from converters import id_2_addr
try:
    from httplib import BadStatusLine  # Python 2.x
except ImportError:
    from http.client import BadStatusLine  # Python 3.x
import polyinterface
from node_types import HueDimmLight, HueWhiteLight, HueColorLight, HueEColorLight, HueGroup
import sys
import socket
import phue
import logging
import json

LOGGER = polyinterface.LOGGER

class Control(polyinterface.Controller):
    """ Phillips Hue Node Server """
    
    def __init__(self, poly):
        super().__init__(poly)
        self.name = 'Hue Bridge'
        self.address = 'huebridge'
        self.primary = self.address
        self.discovery = False
        self.hub = {}
        self.lights = {}
        self.groups = {}
        self.scenes = {}
        self.scene_lookup = []
        self.ignore_second_on = False
        LOGGER.info('Started Hue Protocol')
                        
    def start(self):
        """ Initial node setup. """
        # define nodes for settings
        if 'debug' not in self.polyConfig['customParams']:
            LOGGER.setLevel(logging.INFO)
        if 'ignore_second_on' in self.polyConfig['customParams']:
            LOGGER.debug('DON will be ignored if already on')
            self.ignore_second_on = True
        self.connect()
        self.discover()

    def stop(self):
        LOGGER.info('Hue NodeServer is stopping')

    def shortPoll(self):
        for idx in self.hub.keys():
            self.updateNodes(idx)

    def connect(self):
        custom_data_ip = False
        custom_data_user = False
        save_needed = False
        bridges = {}
        bridges_list = None
        hub_list = []
        """ Connect to Phillips Hue Hub """
        # pylint: disable=broad-except
        # get hub settings
        if 'customData' in self.polyConfig:
            if 'bridge_ip' in self.polyConfig['customData']:
                bridge_ip = self.polyConfig['customData']['bridge_ip']
                custom_data_ip = True
                LOGGER.info('Bridge IP found in the Database: {}'.format(bridge_ip))
            if 'bridge_user' in self.polyConfig['customData']:
                bridge_user = self.polyConfig['customData']['bridge_user']
                custom_data_user = True
                LOGGER.info('Bridge Username found in the Database.')
            if 'bridges' in self.polyConfig['customData']:
                for idx, bridge in self.polyConfig['customData']['bridges'].items():
                    bridges[bridge['ip']] = bridge['user']
                LOGGER.info('Database has {} bridge(s) configuration'.format(len(bridges)))
            else:
                LOGGER.info('Saved bridges information is not found')
                if custom_data_ip and custom_data_user:
                    LOGGER.info('Old custom data found in the DB, converting')
                    data = {'0': {'ip': bridge_ip, 'user': bridge_user }}
                    bridges[bridge_ip] = bridge_user
                    self.saveCustomData({'bridges': data })

        else:
            LOGGER.info('Custom Data is not found in the DB')

        if 'bridges' in self.polyConfig['customParams']:
            try:
                hub_list = json.loads(self.polyConfig['customParams']['bridges'])
            except Exception as ex:
                LOGGER.error('Failed to read bridges variable {} {}'.format(self.polyConfig['customParams']['bridges'], ex))
                return
            LOGGER.info('Reading bridges configuration: {}'.format(hub_list))
        else:
            if len(bridges) > 0:
                for hub in bridges.keys():
                    hub_list.append(hub)
                    LOGGER.info('Adding existing bridge {}'.format(hub))
            else:
                LOGGER.info('No bridge configuration found, trying discovery...')
                hub_list = [ None ]

        for hub_ip in hub_list:
            ''' Initialize structures '''
            hub_user = None

            if hub_ip in bridges:
                LOGGER.info('Found username for bridge {} in the DB'.format(hub_ip))
                hub_user = bridges[hub_ip]
            else:
                save_needed = True

            try:
                hub_conn = phue.Bridge( hub_ip, hub_user )
            except phue.PhueRegistrationException:
                LOGGER.error('IP Address OK. Node Server not registered.')
                self.addNotice({'myNotice': 'Please press the button on the Hue Bridge(s) and restart the node server within 30 seconds'})
                continue
            except Exception:
                LOGGER.error('Cannot find Hue Bridge')
                continue  # bad ip Address:
            else:
                # ensure hub is connectable
                hub_ip = hub_conn.ip
                self.hub[hub_ip] = hub_conn
                self.lights[hub_ip] = self._get_lights(hub_ip)

                if self.lights[hub_ip]:
                    LOGGER.info('Connection OK')
                    self.removeNoticesAll()
                    hub_user = self.hub[hub_ip].username
                    bridges[hub_ip] = hub_user
                else:
                    LOGGER.error('Connect: Failed to read Lights from the Hue Bridge')
                    self.hub[hub_ip] = None
        if save_needed:
            idx = 0
            data = {}
            for hub_ip in bridges.keys():
                data[idx] = {'ip': hub_ip, 'user': bridges[hub_ip]}
                idx += 1
            if len(data) > 0:
                LOGGER.info('Saving usernames to DB')
                self.saveCustomData({'bridges': data })

    def discover(self, command=None):
        self.scene_lookup = []
        for idx in self.hub.keys():
            self._discover(idx)

    def _discover(self, hub_idx):
        """ Poll Hue for new lights/existing lights' statuses """
        if self.hub[hub_idx] is None or self.discovery == True:
            return True
        self.discovery = True
        LOGGER.info('Hub {} Starting Hue discovery...'.format(hub_idx))

        self.lights[hub_idx] = self._get_lights(hub_idx)
        if not self.lights[hub_idx]:
            LOGGER.error('Hub {} Discover: Failed to read Lights from the Hue Bridge'.format(hub_idx))
            self.discovery = False
            return False
        
        LOGGER.info('Hub {} {} bulbs found. Checking status and adding to ISY if necessary.'.format(hub_idx, len(self.lights[hub_idx])))

        for lamp_id, data in self.lights[hub_idx].items():
            address = id_2_addr(data['uniqueid'])
            name = data['name']
            
            if not address in self.nodes:
                if data['type'] == "Extended color light":
                    LOGGER.info('Hub {} Found Extended Color Bulb: {}({})'.format(hub_idx, name, address))
                    self.addNode(HueEColorLight(self, self.address, address, name, lamp_id, data, hub_idx))
                elif data['type'] == "Color light":
                    LOGGER.info('Hub {} Found Color Bulb: {}({})'.format(hub_idx, name, address))
                    self.addNode(HueColorLight(self, self.address, address, name, lamp_id, data, hub_idx))
                elif data['type'] == "Color temperature light":
                    LOGGER.info('Hub {} Found White Ambiance Bulb: {}({})'.format(hub_idx, name, address))
                    self.addNode(HueWhiteLight(self, self.address, address, name, lamp_id, data, hub_idx))
                elif data['type'] == "Dimmable light":
                    LOGGER.info('Hub {} Found Dimmable Bulb: {}({})'.format(hub_idx, name, address))
                    self.addNode(HueDimmLight(self, self.address, address, name, lamp_id, data, hub_idx))
                else:
                    LOGGER.info('Hub {} Found Unsupported {} Bulb: {}({})'.format(hub_idx, data['type'], name, address))

        self.scenes[hub_idx] = self._get_scenes(hub_idx)
        if not self.scenes[hub_idx]:
            LOGGER.error('Hub {} Discover: Failed to read Scenes from the Hue Bridge'.format(hub_idx))
        
        self.groups[hub_idx] = self._get_groups(hub_idx)
        if not self.groups[hub_idx]:
            LOGGER.error('Hub {} Discover: Failed to read Groups from the Hue Bridge'.format(hub_idx))
            self.discovery = False
            return False

        LOGGER.info('Hub {} {} groups found. Checking status and adding to ISY if necessary.'.format(hub_idx, len(self.groups[hub_idx])))

        for group_id, data in self.groups[hub_idx].items():
            scene_idx = 0
            if len(self.hub) > 1:
                address = 'huegrp'+hub_idx.split('.')[-1]+group_id
            else:
                address = 'huegrp'+group_id
            if group_id == '0':
                name = 'All Lights'
            else:
                name = data['name']
            
            if 'lights' in data and len(data['lights']) > 0:
                if not address in self.nodes:
                    LOGGER.info("Hub {} Found {} {} with {} light(s)".format(hub_idx, data['type'], name, len(data['lights'])))
                    self.addNode(HueGroup(self, self.address, address, name, group_id, data, hub_idx))
                    if self.scenes[hub_idx]:
                        for scene_id, scene_data in self.scenes[hub_idx].items():
                            if 'group' in scene_data:
                                if scene_data['group'] == group_id:
                                    self.scene_lookup.append({ "hub": hub_idx, "group": int(group_id), "idx": scene_idx, "id": scene_id, "name": scene_data['name']})
                                    LOGGER.debug(f"Hub {hub_idx} {data['type']} {name} {scene_data['type']} {scene_idx}:{scene_id}:{scene_data['name']}")
                                    scene_idx += 1
            else:
                if address in self.nodes:
                    LOGGER.info("Hub {} {} {} does not have any lights in it, removing a node".format(hub_idx, data['type'], name))
                    self.delNode(address)
        
        LOGGER.info('Hub {} Discovery complete'.format(hub_idx))
        self.discovery = False
        return True

    def updateNodes(self, hub_idx):
        if self.hub[hub_idx] is None or self.discovery == True:
            return True
        self.lights[hub_idx] = self._get_lights(hub_idx)
        self.groups[hub_idx] = self._get_groups(hub_idx)
        for node in self.nodes:
            self.nodes[node].updateInfo()
        return True

    def updateInfo(self):
        pass

    def _get_lights(self, hub_idx):
        if self.hub[hub_idx] is None:
            return None
        try:
            lights = self.hub[hub_idx].get_light()
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

    def _get_groups(self, hub_idx):
        if self.hub[hub_idx] is None:
            return None
        try:
            groups = self.hub[hub_idx].get_group()
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

    def _get_scenes(self, hub_idx):
        if self.hub[hub_idx] is None:
            return None
        try:
            scenes = self.hub[hub_idx].get_scene()
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
        return scenes

    drivers = [{ 'driver': 'ST', 'value': 1, 'uom': 2 }]
    commands = {'DISCOVER': discover}
    id = 'HUEBR'


if __name__ == "__main__":
    try:
        """
        Grab the "HUE" variable from the .polyglot/.env file. This is where
        we tell it what profile number this NodeServer is.
        """
        poly = polyinterface.Interface("Hue")
        poly.start()
        hue = Control(poly)
        hue.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
