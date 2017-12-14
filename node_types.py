""" Node classes used by the Hue Node Server. """

from converters import RGB_2_xy, color_xy, bri2st, kel2mired
from functools import partial
import json
import polyinterface as polyglot

def myint(value):
    """ round and convert to int """
    return int(round(float(value)))

def myfloat(value, prec=4):
    """ round and return float """
    return round(float(value), prec)


class HueColorLight(polyglot.Node):
    """ Node representing Hue Color Light """

    def __init__(self, parent, primary, address, name, lamp_id, device):
        super(HueColorLight, self).__init__(parent, primary, address, name)
        self.lamp_id = int(lamp_id)
        self.name = name
        self.on = None
        self.st = None
        self.hue = None
        self.saturation = None
        self.brightness = None
        self.color_x = None
        self.color_y = None
        self.ct = None
        self.effect = None
        self.alert = None
        self.transitiontime = None
        self.reachable = None

    def start(self):
        self.query()
        
    def query(self, command = None):
        self.updateInfo()
        
    def updateInfo(self):
        data = self.parent.hub.get_light(self.lamp_id)
        
        (self.color_x, self.color_y) = [round(val, 4)
                              for val in data['state'].get('xy',[0.0,0.0])]
        self.on = data['state']['on']                      
        self.brightness = data['state']['bri']
        self.st = bri2st(data['state']['bri'])
        self.hue = data['state']['hue']
        self.saturation = data['state']['sat']
        self.colortemp = kel2mired(data['state']['ct'])
        self.reachable = data['state']['reachable']
        self.alert = data['state']['alert']
        self.effect = data['state']['effect']
        
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        self.setDriver('GV3', self.hue)
        self.setDriver('GV4', self.saturation)
        self.setDriver('GV5', self.brightness)
        self.setDriver('GV6', self.reachable)

        if self.on:
            self.setDriver('ST', self.st)
        else:
            self.setDriver('ST', 0)
        return True

    def setOn(self, *args, **kwargs):
        command = {'on': True}
        result = self._send_command(command)
        self.setDriver('ST', self.st)
        return result

    def setOff(self, *args, **kwargs):
        command = {'on': False}
        result = self._send_command(command)
        self.setDriver('ST', 0)
        return result

    def setColorRGB(self, command):
        """ set light RGB color """
        query = command.get('query')
        color_r = int(query.get('R.uom56'))
        color_g = int(query.get('G.uom56'))
        color_b = int(query.get('B.uom56'))
        (self.color_x, self.color_y) = RGB_2_xy(color_r, color_g, color_b)
        hue_command = {'xy': [self.color_x, self.color_y]}
        if self.on != True:
            hue_command['on'] = True
            self.on = True
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command)

    def setColorXY(self, command):
        """ set light XY color """
        query = command.get('query')
        self.color_x = int(query.get('X.uom56'))
        self.color_y = int(query.get('Y.uom56'))
        hue_command = {'xy': [self.color_x, self.color_y]}
        if self.on != True:
            hue_command['on'] = True
            self.on = True
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)            
        return self._send_command(hue_command)

    def setColor(self, command):
        """ set color from index """
        c_id = int(command.get('value')) - 1
        (color_x, color_y) = color_xy(c_id)
        hue_command = {'xy': [color_x, color_y]}
        if self.on != True:
            hue_command['on'] = True
            self.on = True
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command)

    def setManual(self, command):
        cmd = command.get('cmd')
        val = int(command.get('value'))
        if cmd == "SET_HUE":
            self.hue = value
            driver = ['GV3', self.hue]
            hue_command = _checkOn( { 'hue': self.hue } )
        elif cmd == "SET_SAT":
            self.saturation = value
            driver = ['GV4', self.saturation]
            hue_command = _checkOn( { 'sat': self.saturation } )
        elif cmd == "SET_BRI":
            self.brightness = value
            driver = ['GV5', self.brightness]
            hue_command = _checkOn( { 'bri': self.brightness } )
        elif cmd == "SET_KEL":
            self.ct = value
            driver = ['CLITEMP', self.ct]
            hue_command = _checkOn( { 'ct': kel2mired(self.ct) } )
        if driver:
           self.setDriver(driver[0], driver[1])
        return self._send_command(hue_command)

    def setColorHSB(self, command):
        query = command.get('query')
        self.hue = int(query.get('H.uom56'))
        self.saturation = int(query.get('S.uom56'))
        self.brightness = int(query.get('B.uom56'))
        self.st = bri2st(self.brightness)
        if self.on != True:
            hue_command['on'] = True
            self.on = True
        hue_command = {'hue': self.hue, 'sat': self.saturation, 'bri': self.brightness}
        self.setDriver('GV3', self.hue)
        self.setDriver('GV4', self.saturation)
        self.setDriver('GV5', self.brightness)
        self.setDriver('ST', self.st)
        return self._send_command(hue_command)
        
    def _send_command(self, command):
        """ generic method to send command to light """
        responses = self.parent.hub.set_light(self.lamp_id, command)
        return all(
            [list(resp.keys())[0] == 'success' for resp in responses[0]])

    def _checkOn(self, command):
        if self.on != True:
            command['on'] = True
        return command

    """ Driver Details:
    GV1: Color X
    GV2: Color Y
    ST: Status / Brightness
    """

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
                   'DON': setOn, 'DOF': setOff, 'QUERY': query,
                   'SET_COLOR': setColor, 'SET_HUE': setManual,
                   'SET_SAT': setManual, 'SET_BRI': setManual,
                   'SET_KEL': setManual, 'SET_DUR': setManual,
                   'SET_HSB': setColorHSB, 'SET_COLOR_RGB': setColorRGB,
                   'SET_COLOR_XY': setColorXY
               }

    id = 'COLOR_LIGHT'
