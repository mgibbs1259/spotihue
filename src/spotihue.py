from typing import Tuple
from urllib import request

import cv2
import numpy as np
from sklearn.cluster import KMeans


class SpotiHue():
    def __init__(self, spotify, hue_bridge):
        self.spotify = spotify
        self.hue_bridge = hue_bridge

    def retrieve_current_track_information(self) -> Tuple[str, str, str, str]:
        """Returns the current track's name, artist, album, and album artwork url."""
        current_track = self.spotify.currently_playing()
        track_name = current_track["item"]["name"]
        track_artist = current_track["item"]["album"]["artists"][0]["name"]
        track_album = current_track["item"]["album"]["name"]
        track_album_artwork_url = current_track["item"]["album"]["images"][1]["url"]
        return track_name, track_artist, track_album, track_album_artwork_url

    def download_current_track_album_artwork(
        self,
        track_album_artwork_url: str,
        track_album_artwork_file_path: str
    ) -> None:
        """Downloads the current track's album artwork."""
        request.urlretrieve(
            track_album_artwork_url, track_album_artwork_file_path
        )

    def resize_current_track_album_artwork(
        self,
        track_album_artwork_file_path: str
    ) -> np.array:
        """Resizes the current track album artwork to 50% of the original size."""
        album_artwork = cv2.imread(track_album_artwork_file_path)
        album_artwork = cv2.cvtColor(album_artwork, cv2.COLOR_BGR2RGB)
        dimensions = (
            int(album_artwork.shape[1] * 50 /
                100), int(album_artwork.shape[0] * 50 / 100)
        )
        resized_album_artwork_array = cv2.resize(
            album_artwork, dimensions, interpolation=cv2.INTER_AREA
        )
        return resized_album_artwork_array

    def convert_current_track_album_artwork_to_2D_array(
        self,
        resized_album_artwork_array: np.array
    ) -> np.array:
        """Converts the current track album artwork from a 3D to a 2D array."""
        return resized_album_artwork_array.reshape(
            resized_album_artwork_array.shape[0] *
            resized_album_artwork_array.shape[1],
            3
        )

    def obtain_kmeans_clusters(
        self,
        album_artwork_array: np.array,
        k: int
    ) -> np.array:
        """Returns the cluster centers obtained by fitting K-Means with k clusters."""
        kmeans = KMeans(n_clusters=k, random_state=1259)
        kmeans.fit(album_artwork_array)
        return kmeans.cluster_centers_

    def check_black_clusters(
        self,
        kmeans_cluster_centers: np.array
    ) -> list:
        """Returns the RGB values for white if the RGB values of a cluster are black."""
        clusters = []
        for cluster in kmeans_cluster_centers:
            if np.all(cluster == 0):
                cluster = np.array([255, 255, 255])
            clusters.append(cluster)
        return clusters

    def normalize_rgb_values(
        self,
        cluster: np.array
    ) -> Tuple[float, float, float]:
        """Returns the normalized RGB values between 0 and 1."""
        R, G, B = (cluster / 255).T
        return R, G, B

    def apply_gamma_correction(
        self,
        normalized_R: float,
        normalized_G: float,
        normalized_B: float
    ) -> Tuple[float, float, float]:
        """Returns RGB values after a gamma correction has been applied."""
        gamma_R = [((normalized_R + 0.055) / (1.0 + 0.055)) **
                   2.4 if normalized_R > 0.04045 else normalized_R / 12.92][0]
        gamma_G = [((normalized_G + 0.055) / (1.0 + 0.055)) **
                   2.4 if normalized_G > 0.04045 else normalized_G / 12.92][0]
        gamma_B = [((normalized_B + 0.055) / (1.0 + 0.055)) **
                   2.4 if normalized_B > 0.04045 else normalized_B / 12.92][0]
        return gamma_R, gamma_G, gamma_B

    def convert_rgb_to_xyz(
        self,
        gamma_R: float,
        gamma_G: float,
        gamma_B: float
    ) -> Tuple[float, float, float]:
        """Returns XYZ values after a RGB to XYZ conversion using the Wide RGB D65
        conversion formula has been applied."""
        X = gamma_R * 0.649926 + gamma_G * 0.103455 + gamma_B * 0.197109
        Y = gamma_R * 0.234327 + gamma_G * 0.743075 + gamma_B * 0.022598
        Z = gamma_R * 0.0000000 + gamma_G * 0.053077 + gamma_B * 1.035763
        return X, Y, Z

    def convert_xyz_to_xy(
        self,
        X: float,
        Y: float,
        Z: float
    ) -> Tuple[float, float]:
        """Returns xy values in the CIE 1931 colorspace after a XYZ to xy conversion has been applied."""
        # Only using one cluster for now
        x = round(X / (X + Y + Z), 4)
        y = round(Y / (X + Y + Z), 4)
        return x, y

    def turn_lights_on(self) -> None:
        """Turns all of the lights on to half brightness."""
        for light in self.hue_bridge.lights:
            light.on = True
            light.brightness = 127

    def turn_lights_off(self) -> None:
        """Turns all of the lights off."""
        for light in self.hue_bridge.lights:
            light.on = False

    def change_light_color_normal(self) -> None:
        """Change all of the lights to normal."""
        for light in self.hue_bridge.lights:
            light.hue = 10000
            light.saturation = 120

    def change_light_color_album_artwork(
        self,
        x: float,
        y: float
    ) -> None:
        """Change all of the lights to one of the prominent colors in the current track's album artwork."""
        for light in self.hue_bridge.lights:
            light.xy = [x, y]

    def determine_track_playing_status(self) -> bool:
        """Returns a boolean indicating if Spotify is still playing a track or not."""
        try:
            track_playing_status = self.spotify.currently_playing()[
                "is_playing"]
            if track_playing_status:
                return True
            else:
                return False
        except:
            return False
