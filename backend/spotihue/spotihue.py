import requests
from typing import List, Optional, Tuple, Union

import cv2
import spotipy
import numpy as np
from sklearn.cluster import KMeans


class SpotiHue:
    def __init__(self, spotify, hue_bridge):
        self.spotify = spotify
        self.hue_bridge = hue_bridge

        # Make this optional in the init
        # self.default_track_name = "Track name not found"

    def _extract_album_name(self, track_data: dict) -> Optional[str]:
        """Extracts the album name from track data.

        Args:
            track_data (dict): Track data containing album information.

        Returns:
            str: The name of the album, or None if not available.
        """
        album_data = track_data.get(
            "album"
        )  # can use bracket here if I set default value
        track_name = album_data.get("name")
        return track_name

    def _extract_artist_name(self, track_data: dict) -> Optional[str]:
        """Extracts the artist name from track data.

        Args:
            track_data (dict): Track data containing album information.

        Returns:
            str: The name of the artist, or None if not available.
        """
        album_data = track_data.get("album")
        artists_data = album_data.get("artists", [])

        if not artists_data:
            track_artist = None
        else:
            track_artist = artists_data[0]["name"]

        return track_artist

    def _extract_album_artwork_url(self, track_data: dict) -> Optional[str]:
        """Extracts the album artwork URL from track data.

        Args:
            track_data (dict): Track data containing album information.

        Returns:
            str: The URL of the album artwork, or None if not available.
        """
        album_data = track_data.get("album")
        images_data = album_data.get("images", [])

        if len(images_data) < 2:
            track_album_artwork_url = None
        else:
            track_album_artwork_url = images_data[1]["url"]

        return track_album_artwork_url

    def _resize_album_artwork_image_array_by_percentage(
        self, image_array: np.ndarray, percentage: Union[int, float] = 50
    ) -> np.ndarray:
        """Resize the current track's album artwork to a given percentage of its original size.

        Args:
            image_array (numpy.ndarray): The input image array in 3D format (H x W x 3).
            percentage (Union[int, float]): The desired size percentage between 1 and 99. Defaults to 50.

        Returns:
            numpy.ndarray: The resized image array in 3D format (H x W x 3).
        """
        if image_array.ndim != 3 or image_array.shape[2] != 3:
            raise ValueError(
                "Input image array must be a 3D array with shape (H, W, 3)"
            )

        if not (1 <= percentage < 100):
            raise ValueError("Percentage must be between 1 and 99")

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
        """Converts the current track's album artwork from a 3D to a 2D array where each row
        corresponds to a pixel's values. This is useful for various image processing
        tasks, including k-means clustering and other analyses that treat each pixel
        as a data point with features.

        Args:
            image_array (np.ndarray): The input image array in 3D format (H x W x 3).

        Returns:
            np.ndarray: A 2D array where each row represents a pixel's values.
        """
        if image_array.ndim != 3 or image_array.shape[2] != 3:
            raise ValueError(
                "Input image array must be a 3D array with shape (H, W, 3)"
            )

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
            current_track = self.spotify.currently_playing()
        except spotipy.SpotifyException as e:
            print(f"Error while fetching current track status: {e}")
            return False

        if current_track is None:
            print("No current track information is available")
            return False

        current_track_status = current_track.get("is_playing")
        if current_track_status is None:
            print("No current track 'is_playing' status available")
            return False

        return current_track_status

    def retrieve_current_track_information(self) -> Optional[Tuple[str, str, str, str]]:
        """Retrieves information about the current track.

        Returns:
            tuple: The current track's name, artist, album, and album artwork URL.
            Returns None if the current track information is not available.
        """
        try:
            current_track = self.spotify.currently_playing()
        except spotipy.SpotifyException as e:
            print(f"Error while fetching current track status: {e}")
            return

        if current_track is None:
            print("No current track information is available")
            return

        track_data = current_track.get("item")
        if track_data is None:
            print("No current track 'item' information is available")
            return

        track_name = track_data.get(
            "name"
        )  # ADD , DEFAULT VALUE HERE; set as variables
        track_album = self._extract_album_name(track_data)
        track_artist = self._extract_artist_name(track_data)
        track_album_artwork_url = self._extract_album_artwork_url(track_data)

        return track_name, track_artist, track_album, track_album_artwork_url

    def obtain_current_track_album_artwork_image_array(
        self, track_album_artwork_url: str
    ) -> np.ndarray:
        """Retrieves the current track's album artwork pixel value array.

        Args:
            track_album_artwork_url (str): The current track's album artwork URL.

        Returns:
            numpy.ndarray: The album artwork pixel value array.
        """
        if not track_album_artwork_url:
            raise ValueError(
                f"The current track's album artwork URL {track_album_artwork_url} is empty"
            )

        response = requests.get(track_album_artwork_url, timeout=3)
        response.raise_for_status()

        image_bytes = response.content
        image_bytes_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image_array = cv2.imdecode(image_bytes_array, cv2.IMREAD_COLOR)

        return image_array

    def process_album_artwork_image_array(self, image_array: np.ndarray) -> np.ndarray:
        """Processes the current track's album artwork pixel value array.

        Args:
            image_array (numpy.ndarray): The album artwork pixel value array.

        Returns:
            numpy.ndarray: The processed album artwork pixel value array.
        """
        # Convert from default BGR color format to RGB color format
        image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)

        image_array = self._resize_album_artwork_image_array_by_percentage(image_array)

        image_array = self._convert_album_artwork_image_array_to_2D_array(image_array)

        return image_array

    def obtain_kmeans_clusters(self, image_array: np.ndarray, k: int = 3) -> np.ndarray:
        """Returns the cluster centers obtained by fitting k-means with k clusters.

        Args:
            image_array (numpy.ndarray): The processed album artwork pixel value array.
            k (int, optional): The number of clusters for k-means. Default is 3.

        Returns:
            numpy.ndarray: The cluster centers obtained by fitting k-means with k clusters.
        """
        kmeans = KMeans(n_init=10, n_clusters=k, random_state=1259)
        kmeans.fit(image_array)
        return kmeans.cluster_centers_

    def process_kmeans_clusters(
        self, kmeans_cluster_centers: np.ndarray
    ) -> List[Tuple[float, float]]:
        """Processes k-means cluster centers to obtain light color values.

        Args:
            kmeans_cluster_centers (numpy.ndarray): Cluster centers obtained from k-means.

        Returns:
            List[Tuple[float, float]]: List of xy values representing light color values.
        """
        light_color_values = []
        for cluster in kmeans_cluster_centers:
            cluster = self._check_for_black_cluster(cluster)

            normalized_rgb_values = self._normalize_rgb_values(cluster)
            gamma_corrected_values = self.apply_gamma_correction(normalized_rgb_values)

            X, Y, Z = self.convert_rgb_to_xyz(gamma_corrected_values)
            x, y = self.convert_xyz_to_xy(X, Y, Z)

            light_color_values.append([x, y])

        return light_color_values

    def change_all_lights_to_normal_color(self, lights: list) -> None:
        """Change all specified lights to "normal" color.

        Args:
            lights (List[str]): List of light names to be modified.

        Returns:
            None
        """
        current_lights = self.hue_bridge.get_light_objects("name")
        for light in lights:
            if not current_lights[light].on:
                current_lights[light].on = True
            current_lights[light].hue = 10000
            current_lights[light].brightness = 254
            current_lights[light].saturation = 120

    def change_all_lights_constant(
        self, lights: List[str], light_color_values: List[Tuple[float, float]]
    ) -> None:
        """Change all specified lights to the most prominent colors in the current track's album artwork.

        Args:
            lights (List[str]): List of light names to be modified.
            light_color_values (List[Tuple[float, float]]): List of xy values representing prominent colors.

        Returns:
            None
        """
        current_lights = self.hue_bridge.get_light_objects("name")
        num_colors = len(light_color_values)
        for i, light in enumerate(lights):
            color = light_color_values[i % num_colors]
            current_lights[light].xy = color

    def sync_lights_music(
        self, lights: list, last_track_album_artwork_url: str
    ) -> Tuple[str, str, str, str]:
        """Synchronize the lights with the current track's album artwork.
        This function retrieves information about the current track being played on Spotify,
        compares the album artwork URL with the previous one, and updates the lights' colors
        based on the album artwork colors if it's a new album.

        Args:
            lights (list): A list of lights to be synchronized.
            last_track_album_artwork_url (str): The last track's album artwork URL.

        Returns:
            Tuple[str, str, str, str]: A tuple containing track name, artist name, album name, and album artwork URL.
        """
        (
            track_name,
            track_artist,
            track_album,
            track_album_artwork_url,
        ) = self.retrieve_current_track_information()

        if last_track_album_artwork_url == track_album_artwork_url:
            return track_name, track_artist, track_album, track_album_artwork_url

        image_array = self.retrieve_current_track_information(track_album_artwork_url)
        processed_image_array = self.process_album_artwork_image_array(image_array)
        kmeans_cluster_centers = self.obtain_kmeans_clusters(processed_image_array)
        light_color_values = self.process_kmeans_clusters(kmeans_cluster_centers)

        self.change_all_lights_constant(lights, light_color_values)

        return track_name, track_artist, track_album, track_album_artwork_url

    def celery_worker():
        pass
