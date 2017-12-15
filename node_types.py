""" Node classes used by the Hue Node Server. """

from converters import RGB_2_xy, color_xy, bri2st, kel2mired
from functools import partial
import json
import polyinterface as polyglot

LOGGER = polyglot.LOGGER

""" Hue Default transition time is 400ms """
DEF_TRANSTIME = 400

class HueDimmLight(polyglot.Node):
    """ Node representing Hue Dimmable Light """

    def __init__(self, parent, primary, address, name, lamp_id, device):
        super().__init__(parent, primary, address, name)
        self.lamp_id = int(lamp_id)
        self.name = name
        self.on = None
        self.st = None
        self.brightness = None
        self.saved_brightness = None
        self.alert = None
        self.transitiontime = DEF_TRANSTIME
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

        self.setDriver('RR', self.transitiontime)
        return True

    def setBaseCtl(self, command):
        cmd = command.get('cmd')

        """ transition time for FastOn/Off"""
        if cmd == 'DFON' or cmd == 'DFOF':
            trans = 0
        else:
            trans = self.transitiontime

        if cmd == 'DON' or cmd == 'DFON':
            """ setting self.on to False to ensure that _send_command will add it """
            self.on = False
            hue_command = {}
            val = command.get('value')
            if val:
                onlevel = int(val)
                self.brightness = int(round(onlevel * 254 / 100))
                hue_command['bri'] = self.brightness
                self.setDriver('GV5', self.brightness)
            self.st = bri2st(self.brightness)
            result = self._send_command(hue_command, trans, True)
        elif cmd == 'DOF' or cmd == 'DFOF':
            self.on = False
            self.st = 0
            hue_command = { 'on': self.on }
            result = self._send_command(hue_command, trans, False)
            if trans != DEF_TRANSTIME:
                """
                Work around a known bug in Hue - setting the light off with transition time
                resets brightness to a random level, we'll attempt to re-set it here
                """
                self.saved_brightness = self.brightness
        elif cmd == 'BRT' or cmd == 'DIM' or cmd == 'FDUP' or cmd == 'FDDOWN' or cmd == 'FDSTOP':
            if cmd == 'BRT':
                increment = 10
                if self.brightness + increment > 254:
                    increment = 254 - self.brightness
            elif cmd == 'DIM':
                increment = -10
                if self.brightness + increment < 1:
                    increment = 1 - self.brightness
            elif cmd == 'FDUP':
                trans = 4000
                increment = 254 - self.brightness
            elif cmd == 'FDDOWN':
                trans = 4000
                increment = 1 - self.brightness
            else:
                """ FDSTOP """
                increment = 0
            self.brightness += increment
            self.st = bri2st(self.brightness)
            hue_command = { 'bri_inc': increment }
            self.setDriver('GV5', self.brightness)
            result = self._send_command(hue_command, trans, True)
        else:
            LOGGER.error('setBaseCtl received an unknown command: {}'.format(cmd))

        self.setDriver('ST', self.st)
        return result

    def setBrightness(self, command):
        self.brightness = int(command.get('value'))
        self.st = bri2st(self.brightness)
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        hue_command = { 'bri': self.brightness }
        return self._send_command(hue_command, self.transitiontime, True)

    def setTransition(self, command):
        self.transitiontime = int(command.get('value'))
        self.setDriver('RR', self.transitiontime)
        return True

    def _send_command(self, command, transtime, checkOn):
        """ generic method to send command to light """
        if transtime != DEF_TRANSTIME:
            command['transitiontime'] = int(round(transtime / 100))
        if checkOn and self.on != True:
            command['on'] = True
            self.on = True
            if self.saved_brightness:
                """ Attempt to restore saved brightness
                    xy or ct should take priority over bri
                """
                if 'bri' not in command:
                    command['bri'] = self.saved_brightness
                self.saved_brightness = None
        responses = self.parent.hub.set_light(self.lamp_id, command)
        return all(
            [list(resp.keys())[0] == 'success' for resp in responses[0]])

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV5', 'value': 0, 'uom': 56},
                {'driver': 'RR', 'value': 0, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': setBaseCtl, 'DOF': setBaseCtl, 'QUERY': query,
                   'DFON': setBaseCtl, 'DFOF': setBaseCtl, 'BRT': setBaseCtl,
                   'DIM': setBaseCtl, 'FDUP': setBaseCtl, 'FDDOWN': setBaseCtl,
                   'FDSTOP': setBaseCtl, 'SET_BRI': setBrightness, 'SET_DUR': setTransition
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
        hue_command = { 'ct': kel2mired(self.ct) }
        return self._send_command(hue_command, self.transitiontime, True)

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV5', 'value': 0, 'uom': 56},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 26},
                {'driver': 'RR', 'value': 0, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueDimmLight.setBaseCtl, 'DOF': HueDimmLight.setBaseCtl, 'QUERY': HueDimmLight.query,
                   'DFON': HueDimmLight.setBaseCtl, 'DFOF': HueDimmLight.setBaseCtl, 'BRT': HueDimmLight.setBaseCtl,
                   'DIM': HueDimmLight.setBaseCtl, 'FDUP': HueDimmLight.setBaseCtl, 'FDDOWN': HueDimmLight.setBaseCtl,
                   'FDSTOP': HueDimmLight.setBaseCtl, 'SET_BRI': HueDimmLight.setBrightness, 'SET_DUR': HueDimmLight.setTransition,
                   'SET_KEL': setCt
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
        transtime = int(query.get('D.uom42'))
        (self.color_x, self.color_y) = RGB_2_xy(color_r, color_g, color_b)
        hue_command = {'xy': [self.color_x, self.color_y]}
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command, transtime, True)

    def setColorXY(self, command):
        LOGGER.debug('Running: setColorXY')
        query = command.get('query')
        self.color_x = float(query.get('X.uom56'))
        self.color_y = float(query.get('Y.uom56'))
        transtime = int(query.get('D.uom42'))
        hue_command = {'xy': [self.color_x, self.color_y]}
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)            
        return self._send_command(hue_command, transtime, True)

    def setColor(self, command):
        LOGGER.debug('Running: setColor')
        c_id = int(command.get('value')) - 1
        (self.color_x, self.color_y) = color_xy(c_id)
        hue_command = {'xy': [self.color_x, self.color_y]}
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command, self.transitiontime, True)

    def setHue(self, command):
        LOGGER.debug('Running: setHue')
        self.hue = int(command.get('value'))
        self.setDriver('GV3', self.hue)
        hue_command = { 'hue': self.hue }
        return self._send_command(hue_command, self.transitiontime, True)

    def setSat(self, command):
        LOGGER.debug('Running: setSat')
        self.saturation = int(command.get('value'))
        self.setDriver('GV4', self.saturation)
        hue_command = { 'sat': self.saturation }
        return self._send_command(hue_command, self.transitiontime, True)

    def setColorHSB(self, command):
        LOGGER.debug('Running: setColorHSB')
        query = command.get('query')
        self.hue = int(query.get('H.uom56'))
        self.saturation = int(query.get('S.uom56'))
        self.brightness = int(query.get('B.uom56'))
        transtime = int(query.get('D.uom42'))
        self.st = bri2st(self.brightness)
        hue_command = {'hue': self.hue, 'sat': self.saturation, 'bri': self.brightness}
        self.setDriver('GV3', self.hue)
        self.setDriver('GV4', self.saturation)
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        return self._send_command(hue_command, transtime, True)

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
                   'DON': HueDimmLight.setBaseCtl, 'DOF': HueDimmLight.setBaseCtl, 'QUERY': HueDimmLight.query,
                   'DFON': HueDimmLight.setBaseCtl, 'DFOF': HueDimmLight.setBaseCtl, 'BRT': HueDimmLight.setBaseCtl,
                   'DIM': HueDimmLight.setBaseCtl, 'FDUP': HueDimmLight.setBaseCtl, 'FDDOWN': HueDimmLight.setBaseCtl,
                   'FDSTOP': HueDimmLight.setBaseCtl, 'SET_BRI': HueDimmLight.setBrightness, 'SET_DUR': HueDimmLight.setTransition,
                   'SET_COLOR': setColor, 'SET_HUE': setHue, 'SET_SAT': setSat, 'SET_HSB': setColorHSB,
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
        hue_command = { 'ct': kel2mired(self.ct) }
        return self._send_command(hue_command, self.transitiontime, True)

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
                   'DON': HueDimmLight.setBaseCtl, 'DOF': HueDimmLight.setBaseCtl, 'QUERY': HueDimmLight.query,
                   'DFON': HueDimmLight.setBaseCtl, 'DFOF': HueDimmLight.setBaseCtl, 'BRT': HueDimmLight.setBaseCtl,
                   'DIM': HueDimmLight.setBaseCtl, 'FDUP': HueDimmLight.setBaseCtl, 'FDDOWN': HueDimmLight.setBaseCtl,
                   'FDSTOP': HueDimmLight.setBaseCtl, 'SET_BRI': HueDimmLight.setBrightness, 'SET_DUR': HueDimmLight.setTransition,
                   'SET_COLOR': HueColorLight.setColor, 'SET_HUE': HueColorLight.setHue, 'SET_SAT': HueColorLight.setSat,
                   'SET_KEL': setCt, 'SET_HSB': HueColorLight.setColorHSB, 'SET_COLOR_RGB': HueColorLight.setColorRGB,
                   'SET_COLOR_XY': HueColorLight.setColorXY
               }

    id = 'ECOLOR_LIGHT'
