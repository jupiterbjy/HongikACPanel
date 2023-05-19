"""
Manages UI events
"""

from typing import Tuple, List

from .primitives import Box, ButtonMixin
from loguru import logger


__all__ = ["UIManager"]


class UIManager:
    def __init__(self, *ui_elements: Box):

        self.button_type: List[Box | ButtonMixin] = []
        self.static_type: List[Box] = []

        for ui_elem in ui_elements:
            if isinstance(ui_elem, ButtonMixin):
                self.button_type.append(ui_elem)
            else:
                self.static_type.append(ui_elem)

    def run_click_event(self, coordinate: Tuple[int, int]) -> bool:
        """Runs clicked element's action. Stops at first match.

        Returns True if there was match, otherwise False.
        """

        for ui_element in self.button_type:
            if coordinate in ui_element:
                logger.debug("Element {} clicked at {}", ui_element.__name__, coordinate)
                ui_element.on_click(coordinate)
                return True

        return False
