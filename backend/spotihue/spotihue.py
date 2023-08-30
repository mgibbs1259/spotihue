import cv2
import logging
from typing import List, Optional, Tuple, Union

import numpy as np
import phue
import redis
import requests
import spotipy
from spotipy import cache_handler
from sklearn.cluster import KMeans

from . import constants, hue, oauth


logger = logging.getLogger(__name__)


class SpotiHue:
    def __init__(
        self,
        spotify_scope: str,
        spotify_client_id: str,
        spotify_client_secret: str,
        spotify_redirect_uri: str,
        hue_bridge_ip_address: str,
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize a SpotiHue instance.

        Args:
            spotify_scope (str): Spotify scope.
            spotify_client_id (str): Spotify client ID.
            spotify_client_secret (str): Spotify client secret.
            spotify_redirect_uri (str): Spotify redirect URI.
            hue_bridge_ip (str): IP address of the Hue bridge.
            redis_client (redis.Redis object): Optional redis client for Spotify auth token caching. If not
            supplied, Spotify auth token cache handler defaults to a file cache handler.
        """
        self._spotify = self._initialize_spotify(
            spotify_scope,
            spotify_client_id,
            spotify_client_secret,
            spotify_redirect_uri,
            redis_client=redis_client,
        )

        # Because HueBridge initialization relies upon the user having pressed their bridge's link button
        # within the last 30 seconds, it is allowed to fail. The initialization is retried by accessing
        # the SpotiHue object's hue_bridge property.
        self._hue_bridge_ip_address = hue_bridge_ip_address
        self._hue = None
        try:
            self._hue = self._initialize_hue(self._hue_bridge_ip_address)
        except phue.PhueRegistrationException:
            logger.info('Unable to connect to Hue bridge; link button has not been pushed')

        self._default_track_name = "unavailable"
        self._default_track_artist = "unavailable"
        self._default_track_album = "unavailable"
        self._default_track_album_artwork_url = ""

    @property
    def hue_bridge(self) -> hue.HueBridge:
        if not self._hue:
            self._hue = self._initialize_hue(self._hue_bridge_ip_address)
        return self._hue

    @property
    def spotify_oauth(self) -> oauth.SpotihueOauth:
        return self._spotify.auth_manager

    @staticmethod
    def _initialize_spotify(scope: str, client_id: str, client_secret: str, redirect_uri: str,
                            redis_client: Optional[redis.Redis] = None) -> spotipy.Spotify:
        """Initialize the Spotify object.

        Args:
            scope (str): Spotify scope.
            client_id (str): Spotify client ID.
            client_secret (str): Spotify client secret.
            redirect_uri (str): Spotify redirect URI.
            redis_client (redis.Redis object): Optional redis client for Spotify auth token caching. If not
            supplied, Spotify auth token cache handler defaults to a file cache handler.

        Returns:
            spotipy.Spotify: Initialized Spotify object.
        """
        oauth_cache_handler = (
            cache_handler.RedisCacheHandler(
                redis=redis_client, key=constants.REDIS_SPOTIFY_ACCESS_TOKEN_KEY
            )
            if redis_client
            else cache_handler.CacheFileHandler(cache_path="data/.spotify_token_cache")
        )

        oauth_manager = oauth.SpotihueOauth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            open_browser=False,
            cache_handler=oauth_cache_handler
        )
        return spotipy.Spotify(auth_manager=oauth_manager)

    @staticmethod
    def _initialize_hue(hue_bridge_ip_address: str) -> hue.HueBridge:
        """Initialize the Hue Bridge object.

        Args:
            hue_bridge_ip_address (str): IP address of the Hue bridge.

        Returns:
            hue.HueBridge: Initialized Hue Bridge object.
        """
        return hue.HueBridge(hue_bridge_ip_address, config_file_path=".hue_config")

    def spotify_ready(self) -> bool:
        """ Checks whether a Spotify access token has been obtained. If access token is expired, refreshes it
        and returns True.

        Returns:
             bool: Whether an access token exists in Spotify's auth manager's cache.
        """
        spotify_token = self.spotify_oauth.validate_token(
            self.spotify_oauth.cache_handler.get_cached_token()
        )
        token_exists = bool(spotify_token is not None)
        return token_exists

    def hue_ready(self, raise_exception: bool = False) -> bool:
        """ Checks whether connection to Hue bridge can be made.
        If hue bridge is already initialized, connect to it.

        Args:
            raise_exception (bool): Whether to re-raise exceptions caught in this method.

        Returns:
             bool: Whether Hue bridge connection is instantiated and current.
        """
        try:
            self.hue_bridge.connect()
            return True
        except Exception as e:
            logger.error(f'Hue bridge connection failed: {e}')
            if raise_exception:
                raise
            else:
                return False

    def _get_current_track(self) -> Optional[dict]:
        """Gets currently-playing track on Spotify (if there is one).

        Returns: dictionary of track information if a Spotify track is playing, or None.
        """
        current_track = None
        try:
            current_track = self._spotify.currently_playing()
        except spotipy.SpotifyException as e:
            logger.error(f"Error while fetching current track status: {e}")
        finally:
            return current_track

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

    def ascertain_track_playing(self) -> bool:
        """Determines if Spotify is currently playing a track.

        Returns:
            bool: True if Spotify is playing a track, False otherwise.
        """
        current_track = self._get_current_track()

        if current_track is None:
            return False

        track_is_playing = current_track.get("is_playing")
        return True if track_is_playing is True else False

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
        current_track = self._get_current_track() or defaults

        track_data = current_track.get("item", {})
        if not track_data:
            logger.info("No current track information is available")
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

            light_color_values.append((x, y))

        return light_color_values

    def retrieve_available_lights(self) -> List[dict]:
        """Retrieves the names of available lights and their RGB values.

        Returns:
            List[dict]: A list of dictionaries containing light names and their RGB values.
            An empty list is returned if no lights are available or an error occurs.
        """
        lights = []
        for light in self.hue_bridge.reachable_lights:
            lights.append({"light_name": light.name, "light_rgb": light.rgb})
        return lights

    def change_all_lights_to_normal_color(self, lights: list) -> None:  # TODO: currently unused
        """Change all specified lights to "normal" color.

        Args:
            lights (List[str]): List of light names to be modified.

        Returns:
            None
        """
        self.hue_bridge.change_all_lights_to_white(lights)

    def sync_lights_music(self, track_album_artwork_url: str, lights: List[str]) -> None:
        """Synchronize the track's album artwork and lights.

        Args:
            track_album_artwork_url (str): The track's album artwork URL.
            lights (List[str]): A list of lights to be synchronized.
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

        self.hue_bridge.change_light_colors(lights, light_color_values)