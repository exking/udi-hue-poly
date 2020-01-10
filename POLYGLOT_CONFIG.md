# UDI Polyglot v2 Philips Hue Poly

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/exking/udi-hue-poly/blob/master/LICENSE)

This Poly provides an interface between Hue Bridge and [Polyglot v2](https://github.com/UniversalDevicesInc/polyglot-v2) server.
All Philips branded bulbs are supported (Dimmable, White, Color and Extended Color),
bulbs could be added to the Insteon scenes as responders and should respond to all basic commands, including dimming.

### Configuration options:
  - `debug` - prints extra debug messages, value does not matter
  - `ignore_second_on` - ignore DON command if bulb is already On
  - `bridges` - this should be set to the list of Hue bridges if you have multiple you would like to be able to control, for example: `['10.0.1.1','10.0.2.1']`
