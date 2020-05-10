#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request

import cv2
import numpy as np
from sklearn.cluster import KMeans


class SpotiHue(object):
    def __init__(self, hue_bridge, spotify):
        self.hue_bridge = hue_bridge
        self.spotify = spotify

    def retrieve_current_track_album_artwork(self):
        """Returns the URL associated with the current track's album artwork."""
        return self.spotify.currently_playing()["item"]["album"]["images"][1]["url"]

    def download_current_track_album_artwork(self):
        """Downloads the current track's album artwork."""
        album_artwork = self.retrieve_current_track_album_artwork()
        urllib.request.urlretrieve(album_artwork, "album_artwork.jpg")

    def resize_current_track_album_artwork(self):
        """Resizes the current track album artwork to 50% of the original size."""
        self.download_current_track_album_artwork()
        album_artwork = cv2.imread("album_artwork.jpg")
        album_artwork = cv2.cvtColor(album_artwork, cv2.COLOR_BGR2RGB)
        dimensions = (int(album_artwork.shape[1] * 50 / 100), int(album_artwork.shape[0] * 50 / 100))
        return cv2.resize(album_artwork, dimensions, interpolation=cv2.INTER_AREA)

    def convert_current_track_album_artwork_to_2D_array(self):
        """Converts the current track album artwork from a 3D to a 2D array."""
        album_artwork_array = self.resize_current_track_album_artwork()
        return album_artwork_array.reshape(album_artwork_array.shape[0] * album_artwork_array.shape[1], 3)

    def obtain_kmeans_clusters(self):
        """Returns the cluster centers obtained by fitting K-Means with 3 clusters."""
        album_artwork_array = self.convert_current_track_album_artwork_to_2D_array()
        kmeans = KMeans(n_clusters=3)
        kmeans.fit(album_artwork_array)
        return kmeans.cluster_centers_

    def check_black_clusters(self):
        """Returns the RGB values for white if the RGB values of a cluster are black."""
        clusters = []
        for cluster in self.obtain_kmeans_clusters():
            if np.all(cluster == 0):
                cluster = np.array([255, 255, 255])
            clusters.append(cluster)
        return clusters

    def standardize_rgb_values(self, cluster):
        """Returns the standardized RGB values between 0 and 1."""
        R, G, B = (cluster / 255).T
        return R, G, B

    def apply_gamma_correction(self, cluster):
        """Returns RGB values after a gamma correction has been applied."""
        R, G, B = self.standardize_rgb_values(cluster)
        R = [((R + 0.055) / (1.0 + 0.055)) ** 2.4 if R > 0.04045 else R / 12.92][0]
        G = [((G + 0.055) / (1.0 + 0.055)) ** 2.4 if G > 0.04045 else G / 12.92][0]
        B = [((B + 0.055) / (1.0 + 0.055)) ** 2.4 if B > 0.04045 else B / 12.92][0]
        return R, G, B

    def convert_rgb_to_xyz(self, cluster):
        """Returns XYZ values after a RGB to XYZ conversion using the Wide RGB D65
        conversion formula has been applied."""
        R, G, B = self.apply_gamma_correction(cluster)
        X = R * 0.649926 + G * 0.103455 + B * 0.197109
        Y = R * 0.234327 + G * 0.743075 + B * 0.022598
        Z = R * 0.0000000 + G * 0.053077 + B * 1.035763
        return X, Y, Z

    def convert_xyz_to_xy(self):
        """Returns xy values in the CIE 1931 colorspace after a XYZ to xy conversion has been applied."""
        # Only using one cluster for now
        cluster = self.check_black_clusters()[0]
        X, Y, Z = self.convert_rgb_to_xyz(cluster)
        x = round(X / (X + Y + Z), 4)
        y = round(Y / (X + Y + Z), 4)
        return x, y

    def turn_lights_on(self):
        """Turns all of the lights on to full brightness."""
        for light in self.hue_bridge.lights:
            light.on = True
            light.brightness = 255

    def change_light_color(self):
        """Change all of the lights to one of the prominent colors in the current track's album artwork."""
        self.turn_lights_on()
        x, y = self.convert_xyz_to_xy()
        for light in self.hue_bridge.lights:
            light.xy = [x, y]
