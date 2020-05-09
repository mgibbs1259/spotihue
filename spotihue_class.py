import urllib.request

import cv2


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
        urllib.request.urlretrieve(self.retrieve_current_track_album_artwork(),
                                   "current_track_album_artwork.jpg")

    def convert_current_track_album_artwork_to_array(self):
        """Returns a flattened numpy array of the current track's album artwork."""
        return cv2.imread("current_track_album_artwork.jpg", flags=cv2.IMREAD_COLOR).flatten()

    def
