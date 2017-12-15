""" Node classes used by the Hue Node Server. """

from converters import RGB_2_xy, color_xy, bri2st, kel2mired
from functools import partial
import json
import polyinterface as polyglot

LOGGER = polyglot.LOGGER

def myint(value):
    """ round and convert to int """
    return int(round(float(value)))

def myfloat(value, prec=4):
    """ round and return float """
    return round(float(value), prec)

class HueDimmLight(polyglot.Node):
    """ Node representing Hue Dimmable Light """

    def __init__(self, parent, primary, address, name, lamp_id, device):
        super().__init__(parent, primary, address, name)
        self.lamp_id = int(lamp_id)
        self.name = name
        self.on = None
        self.st = None
        self.brightness = None
        self.alert = None
        self.transitiontime = 0
        self.reachable = None

    def start(self):
        self.query()
        
    def query(self, command = None):
        self.updateInfo()
        
    def updateInfo(self):
        self.data = self.parent.hub.get_light(self.lamp_id)
        self.on = self.data['state']['on']
        self.brightness = self.data['state']['bri']
        self.st = bri2st(self.data['state']['bri'])
        self.reachable = self.data['state']['reachable']
        self.alert = self.data['state']['alert']
        
        self.setDriver('GV5', self.brightness)

        if self.reachable:
            self.setDriver('GV6', 1)
        else:
            self.setDriver('GV6', 0)

        if self.on:
            self.setDriver('ST', self.st)
        else:
            self.setDriver('ST', 0)

        return True

    def setOn(self, *args, **kwargs):
        LOGGER.debug('Running: setOn')
        command = {'on': True}
        result = self._send_command(command)
        self.setDriver('ST', self.st)
        return result

    def setOff(self, *args, **kwargs):
        LOGGER.debug('Running: setOff')
        command = {'on': False}
        result = self._send_command(command)
        self.setDriver('ST', 0)
        return result

    def setBrightness(self, command):
        LOGGER.debug('Running: setBrightness')
        self.brightness = int(command.get('value'))
        self.st = bri2st(self.brightness)
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        hue_command = self._checkOn( { 'bri': self.brightness } )
        return self._send_command(hue_command)

    def setTransition(self, command):
        LOGGER.debug('Running: setTransition')
        self.transitiontime = int(command.get('value'))
        self.setDriver('RR', self.transitiontime)
        return True

    def _send_command(self, command):
        """ generic method to send command to light """
        responses = self.parent.hub.set_light(self.lamp_id, command)
        return all(
            [list(resp.keys())[0] == 'success' for resp in responses[0]])

    def _checkOn(self, command):
        if self.on != True:
            command['on'] = True
        if self.transitiontime > 0:
            command['transitiontime'] = self.transitiontime
        return command

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV5', 'value': 0, 'uom': 56},
                {'driver': 'RR', 'value': 0, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': setOn, 'DOF': setOff, 'QUERY': query,
                   'SET_BRI': setBrightness, 'SET_DUR': setTransition
               }

    id = 'DIMM_LIGHT'

class HueWhiteLight(HueDimmLight):
    """ Node representing Hue Color Light """

    def __init__(self, parent, primary, address, name, lamp_id, device):
        super().__init__(parent, primary, address, name, lamp_id, device)
        self.ct = None

    def updateInfo(self):
        super().updateInfo()
        self.ct = kel2mired(self.data['state']['ct'])
        self.setDriver('CLITEMP', self.ct)
        return True

    def setCt(self, command):
        LOGGER.debug('Running: setCt')
        self.ct = int(command.get('value'))
        self.setDriver('CLITEMP', self.ct)
        hue_command = self._checkOn( { 'ct': kel2mired(self.ct) } )
        return self._send_command(hue_command)

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV5', 'value': 0, 'uom': 56},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 26},
                {'driver': 'RR', 'value': 0, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueDimmLight.setOn, 'DOF': HueDimmLight.setOff, 'QUERY': HueDimmLight.query,
                   'SET_BRI': HueDimmLight.setBrightness, 'SET_KEL': setCt,
                   'SET_DUR': HueDimmLight.setTransition
               }

    id = 'WHITE_LIGHT'

class HueColorLight(HueDimmLight):
    """ Node representing Hue Color Light """

    def __init__(self, parent, primary, address, name, lamp_id, device):
        super().__init__(parent, primary, address, name, lamp_id, device)
        self.hue = None
        self.saturation = None
        self.color_x = None
        self.color_y = None
        self.effect = None

    def updateInfo(self):
        super().updateInfo()
        self.effect = self.data['state']['effect']
        (self.color_x, self.color_y) = [round(float(val), 4)
                              for val in self.data['state'].get('xy',[0.0,0.0])]
        self.hue = self.data['state']['hue']
        self.saturation = self.data['state']['sat']
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        self.setDriver('GV3', self.hue)
        self.setDriver('GV4', self.saturation)
        return True

    def setColorRGB(self, command):
        LOGGER.debug('Running: setColorRGB')
        query = command.get('query')
        color_r = int(query.get('R.uom56'))
        color_g = int(query.get('G.uom56'))
        color_b = int(query.get('B.uom56'))
        (self.color_x, self.color_y) = RGB_2_xy(color_r, color_g, color_b)
        hue_command = self._checkOn({'xy': [self.color_x, self.color_y]})
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command)

    def setColorXY(self, command):
        LOGGER.debug('Running: setColorXY')
        query = command.get('query')
        self.color_x = int(query.get('X.uom56'))
        self.color_y = int(query.get('Y.uom56'))
        hue_command = self._checkOn({'xy': [self.color_x, self.color_y]})
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)            
        return self._send_command(hue_command)

    def setColor(self, command):
        LOGGER.debug('Running: setColor')
        c_id = int(command.get('value')) - 1
        (self.color_x, self.color_y) = color_xy(c_id)
        hue_command = self._checkOn({'xy': [self.color_x, self.color_y]})
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command)

    def setHue(self, command):
        LOGGER.debug('Running: setHue')
        self.hue = int(command.get('value'))
        self.setDriver('GV3', self.hue)
        hue_command = self._checkOn( { 'hue': self.hue } )
        return self._send_command(hue_command)

    def setSat(self, command):
        LOGGER.debug('Running: setSat')
        self.saturation = int(command.get('value'))
        self.setDriver('GV4', self.saturation)
        hue_command = self._checkOn( { 'sat': self.saturation } )
        return self._send_command(hue_command)

    def setColorHSB(self, command):
        LOGGER.debug('Running: setColorHSB')
        query = command.get('query')
        self.hue = int(query.get('H.uom56'))
        self.saturation = int(query.get('S.uom56'))
        self.brightness = int(query.get('B.uom56'))
        self.st = bri2st(self.brightness)
        hue_command = self._checkOn({'hue': self.hue, 'sat': self.saturation, 'bri': self.brightness})
        self.setDriver('GV3', self.hue)
        self.setDriver('GV4', self.saturation)
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        return self._send_command(hue_command)

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV1', 'value': 0, 'uom': 56},
                {'driver': 'GV2', 'value': 0, 'uom': 56},
                {'driver': 'GV3', 'value': 0, 'uom': 56},
                {'driver': 'GV4', 'value': 0, 'uom': 56},
                {'driver': 'GV5', 'value': 0, 'uom': 56},
                {'driver': 'RR', 'value': 0, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueDimmLight.setOn, 'DOF': HueDimmLight.setOff, 'QUERY': HueDimmLight.query,
                   'SET_COLOR': setColor, 'SET_HUE': setHue,
                   'SET_SAT': setSat, 'SET_BRI': HueDimmLight.setBrightness,
                   'SET_DUR': HueDimmLight.setTransition, 'SET_HSB': setColorHSB,
                   'SET_COLOR_RGB': setColorRGB, 'SET_COLOR_XY': setColorXY
               }

    id = 'COLOR_LIGHT'

class HueEColorLight(HueColorLight):
    """ Node representing Hue Color Light """

    def __init__(self, parent, primary, address, name, lamp_id, device):
        super().__init__(parent, primary, address, name, lamp_id, device)
        self.ct = None

    def updateInfo(self):
        super().updateInfo()
        self.ct = kel2mired(self.data['state']['ct'])
        self.setDriver('CLITEMP', self.ct)
        return True

    def setCt(self, command):
        LOGGER.debug('Running: setCt')
        self.ct = int(command.get('value'))
        self.setDriver('CLITEMP', self.ct)
        hue_command = self._checkOn( { 'ct': kel2mired(self.ct) } )
        return self._send_command(hue_command)

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV1', 'value': 0, 'uom': 56},
                {'driver': 'GV2', 'value': 0, 'uom': 56},
                {'driver': 'GV3', 'value': 0, 'uom': 56},
                {'driver': 'GV4', 'value': 0, 'uom': 56},
                {'driver': 'GV5', 'value': 0, 'uom': 56},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 26},
                {'driver': 'RR', 'value': 0, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueDimmLight.setOn, 'DOF': HueDimmLight.setOff, 'QUERY': HueDimmLight.query,
                   'SET_COLOR': HueColorLight.setColor, 'SET_HUE': HueColorLight.setHue,
                   'SET_SAT': HueColorLight.setSat, 'SET_BRI': HueDimmLight.setBrightness,
                   'SET_KEL': setCt, 'SET_DUR': HueDimmLight.setTransition,
                   'SET_HSB': HueColorLight.setColorHSB, 'SET_COLOR_RGB': HueColorLight.setColorRGB,
                   'SET_COLOR_XY': HueColorLight.setColorXY
               }

    id = 'ECOLOR_LIGHT'
