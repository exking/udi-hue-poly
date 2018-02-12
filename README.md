# UDI Polyglot v2 Philips Hue Poly 

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/exking/udi-hue-poly/blob/master/LICENSE)
[![Build Status](https://travis-ci.org/exking/udi-hue-poly.svg?branch=master)](https://travis-ci.org/exking/udi-hue-poly)

This Poly provides an interface between Hue Bridge and [Polyglot v2](https://github.com/UniversalDevicesInc/polyglot-v2) server.
All Philips branded bulbs are supported (Dimmable, White, Color and Extended Color),
bulbs could be added to the Insteon scenes as responders and should respond to all basic commands, including dimming.

### Installation instructions
Make sure that you have a `zip` executable on the system, install using your OS package manager if necessarily.
You can install it from the Polyglot store or manually running
```
cd ~/.polyglot/nodeservers
git clone https://github.com/exking/udi-hue-poly.git Hue
```

### Configuration

Once installed - push the button on the Hue Bridge and add NodeServer into Polyglot, that will allow it to pair with the Bridge.
If you have been using v1 of the Hue Poly - you will likely have a file named `bridges`, copy that file into `~/.python_hue` - you should be able to skip the pairing process and start this Poly out of the box.

Sometimes automatic bridge IP address discovery fails, in that case - you can specify Bridge IP address in a custom parameter `ip` for the NodeServer using Polyglot's frontend interface. Additionally - if `username` parameter is given - NodeServer will use it (in case you have a username established already and don't want another one created on the Bridge).

### Notes

Poly assumes that Bridge IP address never change, so it is recommended that you create an IP address reservation for the Hue Bridge on your router.

Please report any problems on the UDI user forum.

Thanks and good luck.

### History
1. [Phue](https://github.com/studioimaginaire/phue) Library with minor modifications is used as a backend.
2. [Original Implementation](https://github.com/UniversalDevicesInc/Polyglot) of the Hue Poly by UniversalDevices team was a base.
3. [LiFX Poly](https://github.com/Einstein42/udi-lifx-poly) was used as a template in order to re-write this Poly for [Polyglot v2](https://github.com/UniversalDevicesInc/polyglot-v2)
