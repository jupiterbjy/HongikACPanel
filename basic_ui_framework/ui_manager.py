"""
Manages UI events
"""

from typing import Tuple, Dict

import trio
from loguru import logger

from .primitives import *
from .combined import *


__all__ = ["UIManager"]


class UIManager:
    def __init__(self, **ui_elements: Box):

        self.all_uis = ui_elements
        self.button_type: Dict[str, Box | ButtonMixin] = {}
        self.static_type: Dict[str, Box] = {}

        for name, ui_elem in ui_elements.items():
            if isinstance(ui_elem, ButtonMixin):
                self.button_type[name] = ui_elem
            else:
                self.static_type[name] = ui_elem

    def __getitem__(self, key) -> Box | TextBox | TextButton:
        return self.all_uis[key]

    def items(self):

        return self.all_uis.items()

    def values(self):
        return self.all_uis.values()

    async def run_click_event(self, coordinate: Tuple[int, int]) -> bool:
        """Runs clicked element's action. Stops at first match.

        Returns True if there was match, otherwise False.
        """

        for name, ui_element in self.button_type.items():
            if coordinate in ui_element:
                logger.debug("Element {} click at {}", name, coordinate)
                await ui_element.on_click(coordinate)
                return True

        return False

    def draw_all(self):
        for ui_elem in self.values():
            ui_elem.draw()

    async def poll_touch(self, touch_driver, interval=0.1):
        """Due to lack of trio support in evdev, using loop temporarily."""

        logger.debug("Touch polling started")

        while True:
            await trio.sleep(interval)

            # get touch input
            touch = touch_driver.receive_touch()
            if touch is None:
                continue

            await self.run_click_event(touch)
