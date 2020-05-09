#!/usr/bin/env python3
import os
import logging
import argparse

from phue import Bridge
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

import credentials
from spotihue_class import SpotiHue


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    os.environ["SPOTIPY_CLIENT_ID"] = credentials.spotify_client_id
    os.environ["SPOTIPY_CLIENT_SECRET"] = credentials.spotify_client_secret

    parser = argparse.ArgumentParser()
    parser.add_argument("--first_connect", default=False, action="store_true",
                        help="Connect to the Hue Bridge for the first time. Ensure Hue Bridge button is pressed.")
    args = parser.parse_args()

    hue_bridge = Bridge(credentials.hue_bridge_ip_address)
    spotify = Spotify(client_credentials_manager=SpotifyClientCredentials())

    if args.first_connect:
        logging.info("Connecting to the Hue Bridge for the first time")
        logging.info("Ensure Hue Bridge button is pressed")
        hue_bridge.connect()

    spotihue = SpotiHue(hue_bridge, spotify)
    spotihue = spotihue.turn_lights_on()
