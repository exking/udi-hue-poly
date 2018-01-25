""" Node classes used by the Hue Node Server. """

from converters import RGB_2_xy, color_xy, bri2st, kel2mired
import polyinterface as polyglot

LOGGER = polyglot.LOGGER

""" Hue Default transition time is 400ms """
DEF_TRANSTIME = 400
""" Increment for DIM and BRT commands """
DEF_INCREMENT = 10
""" Transition time for FadeUp/Down commands """
FADE_TRANSTIME = 4000

HUE_EFFECTS = ['none', 'colorloop']
HUE_ALERTS = ['none', 'select', 'lselect']

class HueBase(polyglot.Node):
    """ Base class for lights and groups """

    def __init__(self, parent, primary, address, name, element_id, element):
        super().__init__(parent, primary, address, name)
        self.name = name
        self.element_id = int(element_id)
        self.data = element
        self.on = None
        self.st = None
        self.brightness = None
        self.saved_brightness = None
        self.alert = None
        self.transitiontime = DEF_TRANSTIME
        self.ct = None
        self.hue = None
        self.saturation = None
        self.color_x = None
        self.color_y = None
        self.effect = None

    """ Basic On/Off and brightness controls """
    def setBaseCtl(self, command):
        cmd = command.get('cmd')

        """ transition time for FastOn/Off"""
        if cmd in [ 'DFON', 'DFOF' ]:
            trans = 0
        else:
            trans = self.transitiontime

        if cmd in ['DON', 'DFON']:
            """ setting self.on to False to ensure that _send_command will add it """
            self.on = False
            """ if this is a Hue Group class """
            if hasattr(self,'all_on'):
                self.all_on = False
            hue_command = {}
            val = command.get('value')
            if val:
                self.brightness = self._validateBri(int(val))
                hue_command['bri'] = self.brightness
                self.setDriver('GV5', self.brightness)
            elif cmd == 'DFON':
                ''' Go to full brightness on Fast On '''
                self.brightness = 254
                hue_command['bri'] = self.brightness
                self.setDriver('GV5', self.brightness)
            self.st = bri2st(self.brightness)
            result = self._send_command(hue_command, trans)
        elif cmd in ['DOF', 'DFOF']:
            self.on = False
            if hasattr(self,'all_on'):
                self.all_on = False
            self.st = 0
            hue_command = { 'on': self.on }
            result = self._send_command(hue_command, trans, False)
            if trans != DEF_TRANSTIME:
                """
                Work around a known bug in Hue - setting the light off with transition time
                resets brightness to a random level, we'll attempt to re-set it here
                """
                self.saved_brightness = self.brightness
        elif cmd in ['BRT', 'DIM', 'FDUP', 'FDDOWN', 'FDSTOP']:
            if cmd == 'BRT':
                increment = DEF_INCREMENT
                if self.brightness + increment > 254:
                    increment = 254 - self.brightness
            elif cmd == 'DIM':
                increment = -DEF_INCREMENT
                if self.brightness + increment < 1:
                    increment = 1 - self.brightness
            elif cmd == 'FDUP':
                trans = FADE_TRANSTIME
                increment = 254 - self.brightness
            elif cmd == 'FDDOWN':
                trans = FADE_TRANSTIME
                increment = 1 - self.brightness
            else:
                """ FDSTOP """
                increment = 0
            self.brightness += increment
            self.st = bri2st(self.brightness)
            hue_command = { 'bri_inc': increment }
            self.setDriver('GV5', self.brightness)
            result = self._send_command(hue_command, trans)
        else:
            LOGGER.error('setBaseCtl received an unknown command: {}'.format(cmd))
            result = None

        self.setDriver('ST', self.st)
        return result

    def setBrightness(self, command):
        self.brightness = self._validateBri(int(command.get('value')))
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        hue_command = { 'bri': self.brightness }
        return self._send_command(hue_command)

    def setTransition(self, command):
        self.transitiontime = int(command.get('value'))
        self.setDriver('RR', self.transitiontime)
        return True

    def setAlert(self, command):
        val = int(command.get('value')) - 1
        self.alert = HUE_ALERTS[val]
        hue_command = { 'alert': self.alert }
        return self._send_command(hue_command)

    def _validateBri(self, brightness):
        if brightness > 254:
            brightness = 254
        elif brightness < 1:
            brightness = 1
        self.st = bri2st(brightness)
        return brightness

    def setCt(self, command):
        self.ct = int(command.get('value'))
        self.setDriver('CLITEMP', self.ct)
        hue_command = { 'ct': kel2mired(self.ct) }
        return self._send_command(hue_command)

    def setCtBri(self, command):
        query = command.get('query')
        self.brightness = self._validateBri(int(query.get('BR.uom100')))
        self.ct = int(query.get('K.uom26'))
        self.setDriver('CLITEMP', self.ct)
        self.setDriver('ST', self.st)
        self.setDriver('GV5', self.brightness)
        hue_command = { 'ct': kel2mired(self.ct), 'bri': self.brightness }
        return self._send_command(hue_command)

    def setColorRGB(self, command):
        query = command.get('query')
        color_r = int(query.get('R.uom100'))
        color_g = int(query.get('G.uom100'))
        color_b = int(query.get('B.uom100'))
        transtime = int(query.get('D.uom42'))
        self.brightness = self._validateBri(int(query.get('BR.uom100')))
        (self.color_x, self.color_y) = RGB_2_xy(color_r, color_g, color_b)
        hue_command = {'xy': [self.color_x, self.color_y], 'bri': self.brightness}
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        return self._send_command(hue_command, transtime)

    def setColorXY(self, command):
        query = command.get('query')
        self.color_x = float(query.get('X.uom56'))
        self.color_y = float(query.get('Y.uom56'))
        transtime = int(query.get('D.uom42'))
        self.brightness = self._validateBri(int(query.get('BR.uom100')))
        hue_command = {'xy': [self.color_x, self.color_y], 'bri': self.brightness}
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)            
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        return self._send_command(hue_command, transtime)

    def setColor(self, command):
        c_id = int(command.get('value')) - 1
        (self.color_x, self.color_y) = color_xy(c_id)
        hue_command = {'xy': [self.color_x, self.color_y]}
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command)

    def setHue(self, command):
        self.hue = int(command.get('value'))
        self.setDriver('GV3', self.hue)
        hue_command = { 'hue': self.hue }
        return self._send_command(hue_command)

    def setSat(self, command):
        self.saturation = int(command.get('value'))
        self.setDriver('GV4', self.saturation)
        hue_command = { 'sat': self.saturation }
        return self._send_command(hue_command)

    def setColorHSB(self, command):
        query = command.get('query')
        self.hue = int(query.get('H.uom56'))
        self.saturation = int(query.get('S.uom100'))
        self.brightness = self._validateBri(int(query.get('BR.uom100')))
        transtime = int(query.get('D.uom42'))
        hue_command = {'hue': self.hue, 'sat': self.saturation, 'bri': self.brightness}
        self.setDriver('GV3', self.hue)
        self.setDriver('GV4', self.saturation)
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        return self._send_command(hue_command, transtime)

    def setEffect(self, command):
        val = int(command.get('value')) - 1
        self.effect = HUE_EFFECTS[val]
        hue_command = { 'effect': self.effect }
        return self._send_command(hue_command)

    def _send_command(self, command, transtime=None, checkOn=True):
        pass

    drivers = []
    commands = {}
    id = ''

class HueDimmLight(HueBase):
    """ Node representing Hue Dimmable Light """

    def __init__(self, parent, primary, address, name, element_id, device):
        super().__init__(parent, primary, address, name, element_id, device)
        self.reachable = None

    def start(self):
        try:
            self.transitiontime = int(self.getDriver('RR'))
        except:
            self.transitiontime = DEF_TRANSTIME
        self.updateInfo()
        
    def query(self, command=None):
        self.data = self.parent.hub.get_light(self.element_id)
        if self.data is None:
            return False
        self._updateInfo()
        self.reportDrivers()
        
    def updateInfo(self):
        if self.parent.lights is None:
            return False
        self.data = self.parent.lights[str(self.element_id)]
        self._updateInfo()

    def _updateInfo(self):
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

    def _send_command(self, command, transtime=None, checkOn=True):
        """ generic method to send command to light """
        if transtime is None:
            transtime = self.transitiontime
        if transtime != DEF_TRANSTIME:
            command['transitiontime'] = int(round(transtime / 100))
        if checkOn and self.on is False:
            command['on'] = True
            self.on = True
            if self.saved_brightness:
                """ Attempt to restore saved brightness """
                if 'bri' not in command:
                    command['bri'] = self.saved_brightness
                self.saved_brightness = None
        responses = self.parent.hub.set_light(self.element_id, command)
        return all(
            [list(resp.keys())[0] == 'success' for resp in responses[0]])

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV5', 'value': 0, 'uom': 100},
                {'driver': 'RR', 'value': 400, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueBase.setBaseCtl, 'DOF': HueBase.setBaseCtl, 'QUERY': query,
                   'DFON': HueBase.setBaseCtl, 'DFOF': HueBase.setBaseCtl, 'BRT': HueBase.setBaseCtl,
                   'DIM': HueBase.setBaseCtl, 'FDUP': HueBase.setBaseCtl, 'FDDOWN': HueBase.setBaseCtl,
                   'FDSTOP': HueBase.setBaseCtl, 'SET_BRI': HueBase.setBrightness, 'RR': HueBase.setTransition,
                   'SET_ALERT': HueBase.setAlert
               }

    id = 'DIMM_LIGHT'

class HueWhiteLight(HueDimmLight):
    """ Node representing Hue White Light """

    def _updateInfo(self):
        super()._updateInfo()
        self.ct = kel2mired(self.data['state']['ct'])
        self.setDriver('CLITEMP', self.ct)
        return True

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV5', 'value': 0, 'uom': 100},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 26},
                {'driver': 'RR', 'value': 400, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueBase.setBaseCtl, 'DOF': HueBase.setBaseCtl, 'QUERY': HueDimmLight.query,
                   'DFON': HueBase.setBaseCtl, 'DFOF': HueBase.setBaseCtl, 'BRT': HueBase.setBaseCtl,
                   'DIM': HueBase.setBaseCtl, 'FDUP': HueBase.setBaseCtl, 'FDDOWN': HueBase.setBaseCtl,
                   'FDSTOP': HueBase.setBaseCtl, 'SET_BRI': HueBase.setBrightness, 'RR': HueBase.setTransition,
                   'CLITEMP': HueBase.setCt, 'SET_ALERT': HueBase.setAlert, 'SET_CTBR': HueBase.setCtBri
               }

    id = 'WHITE_LIGHT'

class HueColorLight(HueDimmLight):
    """ Node representing Hue Color Light """

    def _updateInfo(self):
        super()._updateInfo()
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

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV1', 'value': 0, 'uom': 56},
                {'driver': 'GV2', 'value': 0, 'uom': 56},
                {'driver': 'GV3', 'value': 0, 'uom': 56},
                {'driver': 'GV4', 'value': 0, 'uom': 100},
                {'driver': 'GV5', 'value': 0, 'uom': 100},
                {'driver': 'RR', 'value': 400, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueBase.setBaseCtl, 'DOF': HueBase.setBaseCtl, 'QUERY': HueDimmLight.query,
                   'DFON': HueBase.setBaseCtl, 'DFOF': HueBase.setBaseCtl, 'BRT': HueBase.setBaseCtl,
                   'DIM': HueBase.setBaseCtl, 'FDUP': HueBase.setBaseCtl, 'FDDOWN': HueBase.setBaseCtl,
                   'FDSTOP': HueBase.setBaseCtl, 'SET_BRI': HueBase.setBrightness, 'RR': HueBase.setTransition,
                   'SET_COLOR': HueBase.setColor, 'SET_HUE': HueBase.setHue, 'SET_SAT': HueBase.setSat, 'SET_HSB': HueBase.setColorHSB,
                   'SET_COLOR_RGB': HueBase.setColorRGB, 'SET_COLOR_XY': HueBase.setColorXY, 'SET_ALERT': HueBase.setAlert,
                   'SET_EFFECT': HueBase.setEffect
               }

    id = 'COLOR_LIGHT'

class HueEColorLight(HueColorLight):
    """ Node representing Hue Color Light """

    def _updateInfo(self):
        super()._updateInfo()
        self.ct = kel2mired(self.data['state']['ct'])
        self.setDriver('CLITEMP', self.ct)
        return True

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV1', 'value': 0, 'uom': 56},
                {'driver': 'GV2', 'value': 0, 'uom': 56},
                {'driver': 'GV3', 'value': 0, 'uom': 56},
                {'driver': 'GV4', 'value': 0, 'uom': 100},
                {'driver': 'GV5', 'value': 0, 'uom': 100},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 26},
                {'driver': 'RR', 'value': 400, 'uom': 42},
                {'driver': 'GV6', 'value': 0, 'uom': 2}
              ]

    commands = {
                   'DON': HueBase.setBaseCtl, 'DOF': HueBase.setBaseCtl, 'QUERY': HueDimmLight.query,
                   'DFON': HueBase.setBaseCtl, 'DFOF': HueBase.setBaseCtl, 'BRT': HueBase.setBaseCtl,
                   'DIM': HueBase.setBaseCtl, 'FDUP': HueBase.setBaseCtl, 'FDDOWN': HueBase.setBaseCtl,
                   'FDSTOP': HueBase.setBaseCtl, 'SET_BRI': HueBase.setBrightness, 'RR': HueBase.setTransition,
                   'SET_COLOR': HueBase.setColor, 'SET_HUE': HueBase.setHue, 'SET_SAT': HueBase.setSat,
                   'CLITEMP': HueBase.setCt, 'SET_HSB': HueBase.setColorHSB, 'SET_COLOR_RGB': HueBase.setColorRGB,
                   'SET_COLOR_XY': HueBase.setColorXY, 'SET_ALERT': HueBase.setAlert, 'SET_EFFECT': HueBase.setEffect,
                   'SET_CTBR': HueBase.setCtBri
               }

    id = 'ECOLOR_LIGHT'

class HueGroup(HueBase):
    """ Node representing a group of Hue Lights """

    def __init__(self, parent, primary, address, name, element_id, device):
        super().__init__(parent, primary, address, name, element_id, device)
        self.devcount = None
        self.all_on = None

    def start(self):
        try:
            self.transitiontime = int(self.getDriver('RR'))
        except:
            self.transitiontime = DEF_TRANSTIME
        self.updateInfo()
        
    def query(self, command=None):
        self.data = self.parent.hub.get_group(self.element_id)
        if self.data is None:
            return False
        self._updateInfo()
        self.reportDrivers()
        
    def updateInfo(self):
        if self.parent.groups is None:
            return False
        self.data = self.parent.groups[str(self.element_id)]
        self._updateInfo()

    def _updateInfo(self):
        self.devcount = len(self.data['lights'])

        if self.devcount < 1:
            LOGGER.info("{} {} has {} lights, skipping updates".format(self.data['type'], self.data['name'], self.devcount))
            return False
        else:
            self.setDriver('GV6', self.devcount)

        self.on = self.data['state']['any_on']
        self.all_on = self.data['state']['all_on']

        self.brightness = self.data['action']['bri']
        self.setDriver('GV5', self.brightness)

        self.st = bri2st(self.data['action']['bri'])
        if self.on:
            self.setDriver('ST', self.st)
        else:
            self.setDriver('ST', 0)

        self.alert = self.data['action']['alert']

        if 'ct' in self.data['action']:
            self.ct = kel2mired(self.data['action']['ct'])
            self.setDriver('CLITEMP', self.ct)
        else:
            self.setDriver('CLITEMP', 0)

        if 'effect' in self.data['action']:
            self.effect = self.data['action']['effect']

        if 'xy' in self.data['action']:
            (self.color_x, self.color_y) = [round(float(val), 4)
                              for val in self.data['action'].get('xy',[0.0,0.0])]
            self.setDriver('GV1', self.color_x)
            self.setDriver('GV2', self.color_y)
        else:
            self.setDriver('GV1', 0)
            self.setDriver('GV2', 0)

        if 'hue' in self.data['action']:
            self.hue = self.data['action']['hue']
            self.setDriver('GV3', self.hue)
        else:
            self.setDriver('GV3', 0)

        if 'sat' in self.data['action']:
            self.saturation = self.data['action']['sat']
            self.setDriver('GV4', self.saturation)
        else:
            self.setDriver('GV4', 0)

        self.setDriver('RR', self.transitiontime)
        return True

    def setCt(self, command):
        if 'ct' not in self.data['action']:
            LOGGER.info("{} {} does not have Color temperature lights but CT command is received".format(self.data['type'], self.data['name']))
            return False
        super().setCt(command)

    def setCtBri(self, command):
        if 'ct' not in self.data['action']:
            LOGGER.info("{} {} does not have Color temperature lights but CTBR command is received".format(self.data['type'], self.data['name']))
            return False
        super().setCtBri(command)

    def setColorRGB(self, command):
        if 'xy' not in self.data['action']:
            LOGGER.info("{} {} does not have Color lights but RGB command is received".format(self.data['type'], self.data['name']))
            return False
        super().setColorRGB(command)

    def setColorXY(self, command):
        if 'xy' not in self.data['action']:
            LOGGER.info("{} {} does not have Color lights but XY command is received".format(self.data['type'], self.data['name']))
            return False
        super().setColorXY(command)

    def setColor(self, command):
        if 'xy' not in self.data['action']:
            LOGGER.info("{} {} does not have Color lights but Color command is received".format(self.data['type'], self.data['name']))
            return False
        super().setColor(command)

    def setHue(self, command):
        if 'hue' not in self.data['action']:
            LOGGER.info("{} {} does not have Color lights but HUE command is received".format(self.data['type'], self.data['name']))
            return False
        super().setHue(command)

    def setSat(self, command):
        if 'sat' not in self.data['action']:
            LOGGER.info("{} {} does not have Color lights but SAT command is received".format(self.data['type'], self.data['name']))
            return False
        super().setSat(command)

    def setColorHSB(self, command):
        if 'hue' not in self.data['action']:
            LOGGER.info("{} {} does not have Color lights but HSB command is received".format(self.data['type'], self.data['name']))
            return False
        super().setColorHSB(command)

    def setEffect(self, command):
        if 'effect' not in self.data['action']:
            LOGGER.info("{} {} does not have Color lights but EFFECT command is received".format(self.data['type'], self.data['name']))
            return False
        super().setEffect(command)

    def _send_command(self, command, transtime=None, checkOn=True):
        if transtime is None:
            transtime = self.transitiontime
        """ generic method to send command to light """
        if transtime != DEF_TRANSTIME:
            command['transitiontime'] = int(round(transtime / 100))
        if checkOn and self.all_on is False:
            command['on'] = True
            self.all_on = True
            if self.saved_brightness:
                """ Attempt to restore saved brightness """
                if 'bri' not in command:
                    command['bri'] = self.saved_brightness
                self.saved_brightness = None
        responses = self.parent.hub.set_group(self.element_id, command)
        return all(
            [list(resp.keys())[0] == 'success' for resp in responses[0]])

    drivers = [ {'driver': 'ST', 'value': 0, 'uom': 51},
                {'driver': 'GV1', 'value': 0, 'uom': 56},
                {'driver': 'GV2', 'value': 0, 'uom': 56},
                {'driver': 'GV3', 'value': 0, 'uom': 56},
                {'driver': 'GV4', 'value': 0, 'uom': 100},
                {'driver': 'GV5', 'value': 0, 'uom': 100},
                {'driver': 'GV6', 'value': 0, 'uom': 56},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 26},
                {'driver': 'RR', 'value': 400, 'uom': 42}
              ]

    commands = {
                   'DON': HueBase.setBaseCtl, 'DOF': HueBase.setBaseCtl, 'QUERY': query,
                   'DFON': HueBase.setBaseCtl, 'DFOF': HueBase.setBaseCtl, 'BRT': HueBase.setBaseCtl,
                   'DIM': HueBase.setBaseCtl, 'FDUP': HueBase.setBaseCtl, 'FDDOWN': HueBase.setBaseCtl,
                   'FDSTOP': HueBase.setBaseCtl, 'SET_BRI': HueBase.setBrightness, 'RR': HueBase.setTransition,
                   'SET_COLOR': setColor, 'SET_HUE': setHue, 'SET_SAT': setSat,
                   'CLITEMP': setCt, 'SET_HSB': setColorHSB, 'SET_COLOR_RGB': setColorRGB,
                   'SET_COLOR_XY': setColorXY, 'SET_ALERT': HueBase.setAlert, 'SET_EFFECT': setEffect,
                   'SET_CTBR': setCtBri
               }

    id = 'HUE_GROUP'

