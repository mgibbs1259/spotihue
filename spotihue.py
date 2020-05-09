#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import argparse

import spotipy.util as util
from phue import Bridge
from spotipy import Spotify

import credentials
from spotihue_class import SpotiHue


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--first_connect", default=False, action="store_true",
                        help="Connect to the Hue Bridge for the first time. Ensure Hue Bridge button is pressed.")
    args = parser.parse_args()

    hue_bridge = Bridge(credentials.hue_bridge_ip_address)
    if args.first_connect:
        logging.info("Connecting to the Hue Bridge for the first time")
        logging.info("Ensure Hue Bridge button is pressed")
        hue_bridge.connect()

    spotify_token = util.prompt_for_user_token(credentials.spotify_username, credentials.spotify_scope,
                                               credentials.spotify_client_id, credentials.spotify_client_secret,
                                               credentials.spotify_redirect_uri)
    spotify = Spotify(auth=spotify_token)

    spotihue = SpotiHue(hue_bridge, spotify)
    spotihue.turn_lights_on()
    spotihue.download_current_track_album_artwork()
    spotihue.change_light_color()
