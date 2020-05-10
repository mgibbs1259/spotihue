#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

import spotipy.util as util
from phue import Bridge
from spotipy import Spotify

import credentials
from spotihue import SpotiHue


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first_connect", default=False, action="store_true",
                        help="Connect to the Hue Bridge for the first time. Ensure Hue Bridge button is pressed.")
    args = parser.parse_args()

    # Hue Bridge
    hue_bridge = Bridge(credentials.hue_bridge_ip_address)
    if args.first_connect:
        hue_bridge.connect()

    # Spotify
    spotify_token = util.prompt_for_user_token(credentials.spotify_username, credentials.spotify_scope,
                                               credentials.spotify_client_id, credentials.spotify_client_secret,
                                               credentials.spotify_redirect_uri)
    spotify = Spotify(auth=spotify_token)

    # SpotiHue
    spotihue = SpotiHue(hue_bridge, spotify)
    spotihue.change_light_color()
