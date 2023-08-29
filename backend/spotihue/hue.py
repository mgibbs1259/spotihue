import logging
from typing import Dict, List, Tuple, Union

import phue


logger = logging.getLogger(__name__)


class HueLight(phue.Light):
    """
    A class that extends phue.Light. It represents a Hue light that
    provides information about whether it is a white (non-color) light
    and offers access to its corresponding RGB color values.
    """

    def __init__(self, bridge, light_id):
        super().__init__(bridge, light_id)
        self._white_light = None
        self._rgb = None

    @property
    def white_light(self) -> bool:
        """Property method to determine whether the Hue light is a white (non-color) light.

        Returns:
            bool: True if the light is a white light, False if it's a color light.
        """
        if self._white_light is None:
            try:
                _ = self._get("colormode")
                self._white_light = False
            except KeyError:
                self._white_light = True

        return self._white_light

    @property
    def rgb(self) -> Tuple[int, int, int]:
        """Property method to return the Hue light's RGB values.
        Converts normalized xy values to RGB color values. The x and y
        values are assumed to be within the range [0, 1], where x + y <= 1.

        Returns:
            Tuple[int, int, int]: The RGB value as a tuple of integers (R, G, B).
        """
        if self._rgb is None:
            try:
                x, y = self.xy
                r = int(x * 255)
                g = int(y * 255)
                b = int((1 - x - y) * 255)
                self._rgb = (r, g, b)
            except (AttributeError, ValueError):
                self._rgb = None

        return self._rgb


class HueBridge(phue.Bridge):
    """
    A class that extends phue.Bridge. It represents a Hue bridge that
    accounts for unreachable and white (non-color) lights.
    """

    light_class = HueLight

    @property
    def reachable_lights(self) -> List[HueLight]:
        """Retrieves the Hue bridge's reachable lights.

        Returns:
            List[HueLight]: List of HueLight objects.
        """
        return [light for light in self.lights if light.reachable is True]

    def get_light_objects(
        self, mode: str = "list"
    ) -> Union[List[HueLight], Dict[str, HueLight]]:
        """Retrieves light objects associated with the Hue bridge.
        Only had to re-declare this because phue.Bridge class does
        not accommodate phue.Light class extension. Instantiates HueLight
        objects instead of phue.Light objects. Otherwise, the same as
        phue.Bridge.get_light_objects.

        Args:
            mode (str, optional):
                The mode for returning light objects. Possible values are:
                - "id": Return a dictionary of light objects indexed by ID.
                - "name": Return a dictionary of light objects indexed by name.
                - "list" (default): Return a list of light objects sorted by ID.

        Returns:
            list or dict:
                If mode is "id", returns a dictionary of light objects indexed by ID.
                If mode is "name", returns a dictionary of light objects indexed by name.
                If mode is "list" (default), returns a list of light objects sorted by ID.
        """
        if self.lights_by_id == {}:
            lights = self.request("GET", "/api/" + self.username + "/lights/")
            for light in lights:
                self.lights_by_id[int(light)] = self.light_class(self, int(light))
                self.lights_by_name[lights[light]["name"]] = self.lights_by_id[
                    int(light)
                ]

        if mode == "id":
            return self.lights_by_id
        if mode == "name":
            return self.lights_by_name
        if mode == "list":
            # Return lights in sorted ID order, dicts have no natural order
            return [self.lights_by_id[id] for id in sorted(self.lights_by_id)]

    def change_all_lights_to_white(self, lights: List[str]) -> None:
        """Change all specified lights to "normal" white color.

        Args:
            lights (List[str]): List of light names to be modified.

        Returns:
            None
        """
        current_lights = self.get_light_objects("name")
        for light in lights:
            current_light = current_lights[light]

            if not current_light.on:
                current_light.on = True
                current_light.brightness = 254

                if not current_light.white_light:
                    current_light.hue = 10000
                    current_light.saturation = 120

    def change_lights_colors(
        self, lights: List[str], color_values: List[Tuple[float, float]]
    ) -> None:
        """Change all specified lights to the most prominent colors in the track's album artwork.

        Args:
            lights (List[str]): List of light names to be modified.
            color_values (List[Tuple[float, float]]): List of xy values representing prominent colors.

        Returns:
            None
        """
        current_lights = self.get_light_objects("name")
        num_colors = len(color_values)

        for i, light in enumerate(lights):
            color = color_values[i % num_colors]
            current_light = current_lights[light]

            # If Hue light is a white/non-color light, it has no xy attribute to set
            if not current_light.white_light:
                current_light.xy = color
