""" Node classes used by the Hue Node Server. """

from converters import RGB_2_xy, color_xy
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
        self.brightness = None
        self.colormode = None
        self.hue = None
        self.saturation = None
        self.color_x = None
        self.color_y = None
        self.colortemp = None
        self.effect = None
        self.alert = None
        self.transitiontime = None
        self.reachable = None
        self.color = []

    def start(self):
        self.query()
        
    def query(self, command = None):
        self.updateInfo()
        
    def updateInfo(self):
        data = self.parent.hub.get_light(self.lamp_id)
        
        (self.color_x, self.color_y) = [round(val, 4)
                              for val in data['state'].get('xy',[0.0,0.0])]
        self.on = data['state']['on']                      
        self.brightness = round(data['state']['bri'] / 255. * 100., 4)
        self.hue = data['state']['hue']
        self.saturation = data['state']['sat']
        self.colortemp = data['state']['ct']
        self.reachable = data['state']['reachable']
        
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        if self.on:
            self.setDriver('ST', self.brightness)
        else:
            self.setDriver('ST', 0)
        return True

    def setOn(self, *args, **kwargs):
        command = {'on': True}
        result = self._send_command(command)
        self.setDriver('ST', self.brightness)
        return result

    def setOff(self, *args, **kwargs):
        command = {'on': False}
        result = self._send_command(command)
        self.setDriver('ST', 0)
        return result
            
    def _set_brightness(self, value=None, **kwargs):
        """ set node brightness """
        # pylint: disable=unused-argument
        if value is not None:
            value = int(value / 100. * 255)
            if value > 0:
                command = {'on': True, 'bri': value}
            else:
                command = {'on': False}
        else:
            command = {'on': True}
        return self._send_command(command)

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
        c_id = int(command.get('value'))
        (color_x, color_y) = color_xy(c_id)
        hue_command = {'xy': [color_x, color_y]}
        if self.on != True:
            hue_command['on'] = True
            self.on = True
        self.setDriver('GV1', self.color_x)
        self.setDriver('GV2', self.color_y)
        return self._send_command(hue_command)

    def setManual(self, command):
        return True

    def setHSBKD(self, command):
        return True
        
    def _send_command(self, command):
        """ generic method to send command to light """
        responses = self.parent.hub.set_light(self.lamp_id, command)
        return all(
            [list(resp.keys())[0] == 'success' for resp in responses[0]])

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
                {'driver': 'RR', 'value': 0, 'uom': 42}
              ]

    commands = {
                   'DON': setOn, 'DOF': setOff, 'QUERY': query,
                   'SET_COLOR': setColor, 'SET_HUE': setManual,
                   'SET_SAT': setManual, 'SET_BRI': setManual,
                   'SET_KEL': setManual, 'SET_DEL': setManual,
                   'SET_HSBKD': setHSBKD, 'SET_COLOR_RGB': setColorRGB,
                   'SET_COLOR_XY': setColorXY
               }

    id = 'COLOR_LIGHT'
