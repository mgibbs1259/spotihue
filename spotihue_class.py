import urllib.request

import cv2
import numpy as np
from sklearn.cluster import KMeans
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
        img = cv2.imread("album_artwork.jpg")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        scale_percent = 50  # percent of original size
        width = int(img.shape[1] * scale_percent / 100)
        height = int(img.shape[0] * scale_percent / 100)
        dim = (width, height)
        # resize image
        resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
        return resized

    def convert_current_track_album_artwork_to_2D_array(self):
        album_artwork_array = self.convert_current_track_album_artwork_to_array()
        return album_artwork_array.reshape(album_artwork_array.shape[0] * album_artwork_array.shape[1], 3)

    def kmeans(self):
        album_artwork_array = self.convert_current_track_album_artwork_to_2D_array()
        kmeans = KMeans(n_clusters=2)
        kmeans.fit(album_artwork_array)
        print(kmeans.cluster_centers_)
        return kmeans.cluster_centers_

    def first_cluster(self):
        album_artwork_array = self.kmeans()
        if np.all(album_artwork_array[0]==0):
            cluster = np.array([255, 255, 255])
        else:
            cluster = album_artwork_array[0]
        return cluster

    def convert_rgb_to_xy(self):
        # Convert values to between 0 and 1
        R, G, B = (self.first_cluster() / 255).T
        print(R, G, B)
        # Apply gamma correction
        R = [((R + 0.055) / (1.0 + 0.055))**2.4 if R > 0.04045 else R / 12.92][0]
        G = [((G + 0.055) / (1.0 + 0.055))**2.4 if G > 0.04045 else G / 12.92][0]
        B = [((B + 0.055) / (1.0 + 0.055))**2.4 if B > 0.04045 else B / 12.92][0]
        # Convert to XYZ using the Wide RGB D65 conversion formula
        X = R * 0.649926 + G * 0.103455 + B * 0.197109
        Y = R * 0.234327 + G * 0.743075 + B * 0.022598
        Z = R * 0.0000000 + G * 0.053077 + B * 1.035763
        # Calculate xy
        x = round(X / (X + Y + Z), 4)
        y = round(Y / (X + Y + Z), 4)
        return x, y

    def change_bulb(self):
        x, y = self.convert_rgb_to_xy()
        for l in self.hue_bridge.lights:
            l.xy = [x, y]
