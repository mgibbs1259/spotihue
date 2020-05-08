#!/usr/bin/env python3
import logging

from phue import Bridge
from spotipy import SpotifyClientCredentials, Spotify


class SpotiHue(Bridge, SpotifyClientCredentials, Spotify):
    def __init__(self, hue_bridge_ip_address):
        Bridge.__init__(hue_bridge_ip_address)
        SpotifyClientCredentials.__init__()
        Spotify.__init__(client_credentials_manager=self)

    def turn_lights_on(self):
        """Turns all of the lights on to half brightness."""
        for light in self.lights:
            light.on = True
            light.brightness = 127

    def