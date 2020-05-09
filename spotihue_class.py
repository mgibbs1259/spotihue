import urllib.request

import cv2
import numpy as np
from skimage import color


class SpotiHue(object):
    def __init__(self, hue_bridge, spotify):
        self.hue_bridge = hue_bridge
        self.spotify = spotify

    def turn_lights_on(self):
        """Turns all of the lights on to full brightness."""
        for light in self.hue_bridge.lights:
            light.on = True
            light.brightness = 255

    def retrieve_current_track_album_artwork(self):
        """Returns the URL associated with the current track's album artwork."""
        return self.spotify.currently_playing()["item"]["album"]["images"][1]["url"]

    def download_current_track_album_artwork(self):
        """Downloads the current track's album artwork."""
        album_artwork = self.retrieve_current_track_album_artwork()
        urllib.request.urlretrieve(album_artwork, "album_artwork.jpg")

    def convert_current_track_album_artwork_to_array(self):
        """Returns a numpy array of the current track's album artwork."""
        return cv2.imread("album_artwork.jpg", flags=cv2.IMREAD_COLOR)

    def convert_rgb_to_xyz(self):
        album_artwork_array = self.convert_current_track_album_artwork_to_array()
        return color.rgb2xyz(album_artwork_array)

    def obtain_mean_pixel_value_in_array(self):
        xyz = self.convert_rgb_to_xyz()
        return np.mean(xyz, axis=(0, 1))

    def obtain_median_pixel_value_in_array(self):
        xyz = self.convert_rgb_to_xyz()
        return np.median(xyz, axis=(0, 1))

    def convert_xyz_to_xy(self):
        X, Y, Z= self.obtain_median_pixel_value_in_array().T
        x = round(X / (X + Y + Z), 4)
        y = round(Y / (X + Y + Z), 4)
        return x, y

    # def convert_rgb_to_xy(self):
    #     # Convert values to between 0 and 1
    #     R, G, B = (self.obtain_median_pixel_value_in_array() / 255).T
    #     # Apply gamma correction
    #     R = [((R + 0.055) / (1.0 + 0.055))**2.4 if R > 0.04045 else R / 12.92][0]
    #     G = [((G + 0.055) / (1.0 + 0.055))**2.4 if G > 0.04045 else G / 12.92][0]
    #     B = [((B + 0.055) / (1.0 + 0.055))**2.4 if B > 0.04045 else B / 12.92][0]
    #     # Convert to XYZ using the Wide RGB D65 conversion formula
    #     X = R * 0.649926 + G * 0.103455 + B * 0.197109
    #     Y = R * 0.234327 + G * 0.743075 + B * 0.022598
    #     Z = R * 0.0000000 + G * 0.053077 + B * 1.035763
    #     # Check if XYZ values within CIE color gamut
    #     # Calculate xy
    #     x = round(X / (X + Y + Z), 4)
    #     y = round(Y / (X + Y + Z), 4)
    #     return x, y

    def change_bulb(self):
        x, y = self.convert_xyz_to_xy()
        for l in self.hue_bridge.lights:
            l.xy = [x, y]
