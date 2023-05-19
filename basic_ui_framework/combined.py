"""
Combines elements
"""

from typing import Tuple

from pygame.font import FontType

from .primitives import *


__all__ = ["TextButton"]


class TextButton(TextBox, ButtonMixin):
    def __init__(
        self,
        p1,
        p2,
        text: str,
        /,
        text_color: Tuple[int, int, int, int] = (0, 0, 0, 255),
        color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        font: FontType = None,
        antialias: bool = True,
        screen=None,
    ):
        """The Textbox that clicked, to jokingly say."""
        super().__init__(
            p1,
            p2,
            text,
            text_color=text_color,
            color=color,
            font=font,
            antialias=antialias,
            screen=screen,
        )
