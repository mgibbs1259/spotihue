import logging
from typing import List, Tuple

import phue


logger = logging.getLogger(__name__)


class HueLight(phue.Light):
    """
    A hue light that knows whether it is a white light.
    """

    def __init__(self, bridge, light_id):
        super().__init__(bridge, light_id)
        self._white_light = None

    @property
    def white_light(self) -> bool:
        if self._white_light is None:
            try:
                _ = self._get('colormode')
                self._white_light = False
            except KeyError:
                self._white_light = True

        return self._white_light


class HueBridge(phue.Bridge):
    """
    A more modular phue.Bridge. Accounts for unreachable lights (ex. a light in the Hue app which does not
    correspond to an actual Hue light bulb), as well as non-color lights.
    """
    light_class = HueLight

    @property
    def reachable_lights(self):
        return [light for light in self.lights if light.reachable is True]

    def get_light_objects(self, mode='list'):
        """
        Only had to re-declare this because phue.Bridge class does not accommodate phue.Light class extension.
        Instantiates HueLight objects instead of phue.Light objects.
        """
        if self.lights_by_id == {}:
            lights = self.request('GET', '/api/' + self.username + '/lights/')
            for light in lights:
                self.lights_by_id[int(light)] = self.light_class(self, int(light))
                self.lights_by_name[lights[light][
                    'name']] = self.lights_by_id[int(light)]
        if mode == 'id':
            return self.lights_by_id
        if mode == 'name':
            return self.lights_by_name
        if mode == 'list':
            # return lights in sorted id order, dicts have no natural order
            return [self.lights_by_id[id] for id in sorted(self.lights_by_id)]

    def change_light_colors(self, lights: List[str], color_values: List[Tuple[float, float]]) -> None:
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

            # If hue bulb is a white/non-color light, it has no xy attribute to set.
            if not current_light.white_light:
                current_light.xy = color

    def change_all_lights_to_white(self, lights: List[str]) -> None:
        """Change all specified lights to "normal" color.

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
