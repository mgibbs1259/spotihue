#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import argparse

from spotihue import SpotiHue


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--first_connect", default=False, action="store_true",
                        help="Connect to the Hue Bridge for the first time. Ensure Hue Bridge button is pressed.")
    args = parser.parse_args()

    spotihue = SpotiHue()
    if args.first_connect:
        spotihue.connect_hue_bridge_first_time()
    spotihue.sync_current_track_album_artwork_lights()
