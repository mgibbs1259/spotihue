import time
import random
import requests
from typing import List, Optional, Tuple, Union

import cv2
import phue
import redis
import spotipy
import numpy as np
from sklearn.cluster import KMeans


class SpotiHue:
    def __init__(
        self,
        spotify_username: str,
        spotify_scope: str,
        spotify_client_id: str,
        spotify_client_secret: str,
        spotify_redirect_uri: str,
        hue_bridge_ip_address: str,
    ):
        """Initialize a SpotiHue instance.

        Args:
            spotify_username (str): Spotify username.
            spotify_scope (str): Spotify scope.
            spotify_client_id (str): Spotify client ID.
            spotify_client_secret (str): Spotify client secret.
            spotify_redirect_uri (str): Spotify redirect URI.
            hue_bridge_ip (str): IP address of the Hue bridge.
        """
        self._spotify = self._initialize_spotify(
            spotify_username,
            spotify_scope,
            spotify_client_id,
            spotify_client_secret,
            spotify_redirect_uri,
        )

        self._hue = self._initialize_hue(hue_bridge_ip_address)

        self._default_track_name = "unavailable"
        self._default_track_artist = "unavailable"
        self._default_track_album = "unavailable"
        self._default_track_album_artwork_url = ""

    def _initialize_spotify(
        self,
        spotify_username: str,
        spotify_scope: str,
        spotify_client_id: str,
        spotify_client_secret: str,
        spotify_redirect_uri: str,
    ) -> spotipy.Spotify:
        """Initialize the Spotify object.

        Args:
            username (str): Spotify username.
            scope (str): Spotify scope.
            client_id (str): Spotify client ID.
            client_secret (str): Spotify client secret.
            redirect_uri (str): Spotify redirect URI.

        Returns:
            spotipy.Spotify: Initialized Spotify object.
        """
        spotify = spotipy.Spotify(
            auth=spotipy.util.prompt_for_user_token(
                spotify_username,
                spotify_scope,
                spotify_client_id,
                spotify_client_secret,
                spotify_redirect_uri,
            )
        )
        return spotify

    def _initialize_hue(self, hue_bridge_ip_address) -> phue.Bridge:
        """Initialize the Hue Bridge object.

        Args:
            bridge_ip (str): IP address of the Hue bridge.

        Returns:
            phue.Bridge: Initialized Hue Bridge object.
        """
        hue = phue.Bridge(hue_bridge_ip_address)
        hue.connect()
        return hue

    def _extract_track_name(self, track_data: dict) -> str:
        """Extracts the track name from track data.

        Args:
            track_data (dict): Track data containing album information.

        Returns:
            str: The name of the track, or the default track name if not available.
        """
        track_name = track_data.get("name", self._default_track_name)
        return track_name

    def _extract_artist_name(self, track_data: dict) -> str:
        """Extracts the artist name from track data.

        Args:
            track_data (dict): Track data containing album information.

        Returns:
            str: The name of the artist, or the default artist name if not available.
        """
        album_data = track_data.get("album")
        artists_data = album_data.get("artists", [])

        if artists_data:
            artist_name = artists_data[0].get("name", self._default_track_artist)
        else:
            artist_name = self._default_track_artist

        return artist_name

    def _extract_album_name(self, track_data: dict) -> str:
        """Extracts the album name from track data.

        Args:
            track_data (dict): Track data containing album information.

        Returns:
            str: The name of the album, or the default album name if not available.
        """
        album_data = track_data.get("album")
        album_name = album_data.get("name", self._default_track_album)
        return album_name

    def _extract_album_artwork_url(self, track_data: dict) -> Optional[str]:
        """Extracts the album artwork URL from track data.

        Args:
            track_data (dict): Track data containing album information.

        Returns:
            str: The URL of the album artwork, or None if not available.
        """
        album_data = track_data.get("album")
        images_data = album_data.get("images", [])

        if len(images_data) > 1:
            track_album_artwork_url = images_data[1].get(
                "url", self._default_track_album_artwork_url
            )
        else:
            track_album_artwork_url = self._default_track_album_artwork_url

        return track_album_artwork_url

    def _resize_album_artwork_image_array_by_percentage(
        self, image_array: np.ndarray, percentage: Union[int, float] = 60
    ) -> np.ndarray:
        """Resize the track's album artwork to a given percentage of its original size.

        Args:
            image_array (numpy.ndarray): The input image array in 3D format (H x W x 3).
            percentage (Union[int, float]): The desired size percentage between 1 and 99. Defaults to 60.

        Returns:
            numpy.ndarray: The resized image array in 3D format (H x W x 3).
        """
        if not (1 <= percentage < 100):
            raise ValueError("percentage must be between 1 and 99.")

        dimensions = (
            int(image_array.shape[1] * percentage / 100),
            int(image_array.shape[0] * percentage / 100),
        )
        resized_image_array = cv2.resize(
            image_array, dimensions, interpolation=cv2.INTER_AREA
        )

        return resized_image_array

    def _convert_album_artwork_image_array_to_2D_array(
        self, image_array: np.ndarray
    ) -> np.ndarray:
        """Converts the track's album artwork from a 3D to a 2D array where each row
        corresponds to a pixel's values. This is useful for various image processing
        tasks, including k-means clustering and other analyses that treat each pixel
        as a data point with features.

        Args:
            image_array (np.ndarray): The input image array in 3D format (H x W x 3).

        Returns:
            np.ndarray: The output image array in 2D format where each row represents a pixel's values (# pixels, 3).
        """
        return image_array.reshape(-1, 3)

    def _check_for_black_cluster(self, cluster: np.ndarray) -> np.ndarray:
        """Returns the RGB values for white if the RGB values of a cluster are black.

        Args:
            cluster (numpy.ndarray): RGB values of a cluster.

        Returns:
            numpy.ndarray: Modified RGB values after checking and adjusting for black RGB values.
        """
        return np.where(np.all(cluster == 0), np.array([255, 255, 255]), cluster)

    def _normalize_rgb_values(self, cluster: np.ndarray) -> np.ndarray:
        """Returns the normalized RGB values between 0 and 1.

        Args:
            cluster (numpy.ndarray): RGB values of a cluster.

        Returns:
            numpy.ndarray: Normalized RGB values between 0 and 1.
        """
        return cluster / 255.0

    def _apply_gamma_correction(self, normalized_rgb_values: np.ndarray) -> np.ndarray:
        """Applies gamma correction to normalized RGB values.

        Args:
            normalized_rgb_values (numpy.ndarray): An array of normalized RGB values between 0 and 1.

        Returns:
            numpy.ndarray: An array of gamma-corrected RGB values.

        Notes:
            The gamma correction formula is applied element-wise based on the condition:
            If the normalized value is greater than 0.04045, the formula is:
            ((normalized_value + 0.055) / (1.0 + 0.055)) ** 2.4
            Otherwise, the formula is:
            normalized_value / 12.92
        """
        return np.where(
            normalized_rgb_values > 0.04045,
            ((normalized_rgb_values + 0.055) / (1.0 + 0.055)) ** 2.4,
            normalized_rgb_values / 12.92,
        )

    def _convert_rgb_to_xyz(
        self, gamma_corrected_values: np.ndarray
    ) -> Tuple[float, float, float]:
        """Returns XYZ values after an RGB to XYZ conversion using the Wide RGB D65
        conversion formula has been applied.

        Args:
            gamma_corrected_values (numpy.ndarray): Gamma-corrected RGB values.

        Returns:
            Tuple[float, float, float]: XYZ values after RGB to XYZ conversion.
        """
        gamma_R, gamma_G, gamma_B = gamma_corrected_values.T

        X = gamma_R * 0.649926 + gamma_G * 0.103455 + gamma_B * 0.197109
        Y = gamma_R * 0.234327 + gamma_G * 0.743075 + gamma_B * 0.022598
        Z = gamma_R * 0.0000000 + gamma_G * 0.053077 + gamma_B * 1.035763

        return X, Y, Z

    def _convert_xyz_to_xy(self, X: float, Y: float, Z: float) -> Tuple[float, float]:
        """Converts XYZ values to xy values in the CIE 1931 colorspace.

        Args:
            X (float): X component of XYZ color values.
            Y (float): Y component of XYZ color values.
            Z (float): Z component of XYZ color values.

        Returns:
            Tuple[float, float]: xy values after the XYZ to xy conversion.
        """
        total = X + Y + Z

        x = round(X / total, 4)
        y = round(Y / total, 4)

        return x, y

    def determine_current_track_status(self) -> bool:
        """Determines if Spotify is currently playing a track.

        Returns:
            bool: True if Spotify is playing a track, False otherwise.
        """
        try:
            current_track = self._spotify.currently_playing()
        except spotipy.SpotifyException as e:
            print(f"Error while fetching current track status: {e}")
            return False

        if current_track is None:
            print("No current track information is available")
            return False

        current_track_status = current_track.get("is_playing")
        if current_track_status:
            return True
        else:
            print("No current track 'is_playing' status available")
            return False

    def retrieve_current_track_information(self) -> dict:
        """Retrieves information about the current track.

        Returns:
            dict: A dictionary containing the current track's name, artist, album, and album artwork URL.
            Returns default values if the current track information is not available.
        """
        defaults = {
            "track_name": self._default_track_name,
            "track_artist": self._default_track_artist,
            "track_album": self._default_track_album,
            "track_album_artwork_url": self._default_track_album_artwork_url,
        }

        try:
            current_track = self._spotify.currently_playing()
        except spotipy.SpotifyException as e:
            print(f"Error while fetching current track status: {e}")
            return defaults

        if not current_track:
            print("No current track information is available")
            return defaults

        track_data = current_track.get("item")
        if not track_data:
            print("No current track 'item' information is available")
            return defaults

        track_info = {
            "track_name": self._extract_track_name(track_data),
            "track_artist": self._extract_album_name(track_data),
            "track_album": self._extract_artist_name(track_data),
            "track_album_artwork_url": self._extract_album_artwork_url(track_data),
        }
        return track_info

    def obtain_track_album_artwork_image_array(
        self, track_album_artwork_url: str
    ) -> np.ndarray:
        """Retrieves the track's album artwork pixel value array.

        Args:
            track_album_artwork_url (str): The track's album artwork URL.

        Returns:
            numpy.ndarray: The album artwork pixel value array in 3D format (H x W x 3).
        """
        if (
            not track_album_artwork_url
            or track_album_artwork_url == self._default_track_album_artwork_url
        ):
            raise ValueError(
                f"track_album_artwork_url {track_album_artwork_url} is invalid"
            )

        response = requests.get(track_album_artwork_url, timeout=3)
        response.raise_for_status()

        image_bytes = response.content
        image_bytes_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image_array = cv2.imdecode(image_bytes_array, cv2.IMREAD_COLOR)

        return image_array

    def process_album_artwork_image_array(self, image_array: np.ndarray) -> np.ndarray:
        """Processes the track's album artwork pixel value array.

        Args:
            image_array (numpy.ndarray): The album artwork pixel value array in 3D format (H x W x 3).

        Returns:
            numpy.ndarray: The processed album artwork pixel value array in 2D format (# pixels, 3).
        """
        if not isinstance(image_array, np.ndarray):
            raise ValueError("image_array should be a numpy.ndarray")

        if image_array.ndim != 3 or image_array.shape[2] != 3:
            raise ValueError("image_array must be a 3D array with shape (H, W, 3)")

        # Convert from default BGR color format to RGB color format
        image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)

        image_array = self._resize_album_artwork_image_array_by_percentage(image_array)
        image_array = self._convert_album_artwork_image_array_to_2D_array(image_array)

        return image_array

    def obtain_kmeans_clusters(self, image_array: np.ndarray, k: int = 3) -> np.ndarray:
        """Returns the cluster centers obtained by fitting k-means with k clusters.

        Args:
            image_array (numpy.ndarray): The processed album artwork pixel value array in 2D format (# pixels, 3).
            k (int, optional): The number of clusters for k-means. Default is 3.

        Returns:
            numpy.ndarray: The cluster centers obtained by fitting k-means with k clusters.
        """
        if not isinstance(image_array, np.ndarray):
            raise ValueError("image_array should be a numpy.ndarray")

        if len(image_array.shape) != 2:
            raise ValueError("image_array must be a 2D array with shape (# pixels, 3)")

        if k <= 0:
            raise ValueError("k should be a positive integer")

        kmeans = KMeans(n_init=10, n_clusters=k, random_state=1259)
        kmeans.fit(image_array)
        return kmeans.cluster_centers_

    def process_kmeans_clusters_to_light_color_values(
        self, kmeans_cluster_centers: np.ndarray
    ) -> List[Tuple[float, float]]:
        """Processes k-means cluster centers to obtain light color values.

        Args:
            kmeans_cluster_centers (numpy.ndarray): Cluster centers obtained from k-means.

        Returns:
            List[Tuple[float, float]]: List of xy values representing light color values.
        """
        if not isinstance(kmeans_cluster_centers, np.ndarray):
            raise ValueError("kmeans_cluster_centers should be a numpy.ndarray")

        if len(kmeans_cluster_centers.shape) != 2:
            raise ValueError("kmeans_cluster_centers should be a 2D array")

        light_color_values = []
        for cluster in kmeans_cluster_centers:
            cluster = self._check_for_black_cluster(cluster)

            normalized_rgb_values = self._normalize_rgb_values(cluster)
            gamma_corrected_values = self._apply_gamma_correction(normalized_rgb_values)

            X, Y, Z = self._convert_rgb_to_xyz(gamma_corrected_values)
            x, y = self._convert_xyz_to_xy(X, Y, Z)

            light_color_values.append([x, y])

        return light_color_values

    def retrieve_available_lights(self) -> List[str]:
        """Retrieves the names of available lights.

        Returns:
            List[str]: A list of light names, or an empty list if no lights are available or an error occurs.
        """
        return [light.name for light in self._hue.lights]

    def change_all_lights_to_normal_color(self, lights: list) -> None:
        """Change all specified lights to "normal" color.

        Args:
            lights (List[str]): List of light names to be modified.

        Returns:
            None
        """
        current_lights = self._hue.get_light_objects("name")
        for light in lights:
            if not current_lights[light].on:
                current_lights[light].on = True
            current_lights[light].hue = 10000
            current_lights[light].brightness = 254
            current_lights[light].saturation = 120

    def change_all_lights_constant(
        self, lights: List[str], light_color_values: List[Tuple[float, float]]
    ) -> None:
        """Change all specified lights to the most prominent colors in the track's album artwork.

        Args:
            lights (List[str]): List of light names to be modified.
            light_color_values (List[Tuple[float, float]]): List of xy values representing prominent colors.

        Returns:
            None
        """
        current_lights = self._hue.get_light_objects("name")
        num_colors = len(light_color_values)
        for i, light in enumerate(lights):
            color = light_color_values[i % num_colors]
            current_lights[light].xy = color

    def sync_lights_music(self, track_album_artwork_url: str, lights: list) -> None:
        """Synchronize the track's album artwork and lights.

        Args:
            track_album_artwork_url (str): The track's album artwork URL.
            lights (list): A list of lights to be synchronized.
        """
        if (
            not track_album_artwork_url
            or track_album_artwork_url == self._default_track_album_artwork_url
        ):
            raise ValueError(
                f"track_album_artwork_url {track_album_artwork_url} is invalid"
            )

        if not lights:
            raise ValueError("lights list should not be empty")

        image_array = self.obtain_track_album_artwork_image_array(
            track_album_artwork_url
        )
        processed_image_array = self.process_album_artwork_image_array(image_array)
        kmeans_cluster_centers = self.obtain_kmeans_clusters(processed_image_array)
        light_color_values = self.process_kmeans_clusters_to_light_color_values(
            kmeans_cluster_centers
        )

        self.change_all_lights_constant(lights, light_color_values)
