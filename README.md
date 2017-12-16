# UDI Polyglot v2 Philips Hue Poly 

This Poly provides an interface between Hue Bridge and Polyglot v2 server.
All Philips branded bulbs are supported (Dimmable, White, Color and Extended Color),
bulbs could be added to the Insteon scenes as responders and should respond to all basic commands, including dimming.

### Installation instructions

You can install it from the Polyglot store or manually running
```
cd ~/.polyglot/nodeservers
git clone https://github.com/exking/udi-hue-poly.git Hue
```

Once installed - push the button on the Hue Bridge and add nodeserver into the Polyglot, that will allow it to pair with the Bridge.

If you have been using v1 of the Hue Poly - you will likely have a file named `bridges`

If you copy that file into `~/.python_hue` - you should be able to skip the pairing process and start this Poly out of the box.

Note that Poly assumes that Bridge IP address never changes, so it is recommended that you create an IP address reservation for the Hue Bridge on your router.

Please report any problems on the UDI user forum.

Thanks and good luck.

