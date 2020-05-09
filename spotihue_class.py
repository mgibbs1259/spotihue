import logging


class SpotiHue(object):
    def __init__(self, hue_bridge, spotify):
        self.hue_bridge = hue_bridge
        self.spotify = spotify

    def turn_lights_on(self):
        """Turns all of the lights on to full brightness."""
        for light in self.hue_bridge.lights:
            light.on = True
            light.brightness = 255
