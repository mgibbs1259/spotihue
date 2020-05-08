#!/usr/bin/env python3
import logging

import phue
import spotipy
from phue import Bridge


class SpotiHue(Bridge):
    def __init__(self, hue_bridge_ip_address):
        super().__init__(hue_bridge_ip_address)

    def turn_lights_on(self):
        """Turns all of the lights on to half brightness."""
        for light in self.lights:
            light.on = True
            light.brightness = 127


