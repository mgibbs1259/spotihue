#!/usr/bin/env python3
import logging
import argparse

from spotihue_class import SpotiHue
from hue_bridge_ip_address import hue_bridge_ip_address


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--first_connect", default=False, action="store_true",
                        help="Connect to the Hue Bridge for the first time. Ensure Hue Bridge button is pressed.")
    args = parser.parse_args()

    spotihue_bridge = SpotiHue(hue_bridge_ip_address)

    if args.first_connect:
        logging.info("Connecting to the Hue Bridge for the first time")
        logging.info("Please ensure Hue Bridge button is pressed")
        spotihue_bridge.connect()

    spotihue_bridge = spotihue_bridge.turn_lights_on()

