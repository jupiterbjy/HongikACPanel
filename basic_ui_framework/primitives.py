"""
UI part

Tried using typing.Protocol but seems like not much of use.
Maybe will be needed when using protocol-based type checks when iterating UI elements.
"""

from typing import Tuple, Callable, Protocol
from functools import partial

from pygame import SurfaceType, Rect
from pygame.font import FontType

from .global_settings import GlobalSetting


# TODO: add ImageBox
__all__ = ["Box", "ButtonMixin", "TextBox", "ButtonType"]


class ButtonType(Protocol):
    def on_click(self, coordinate: Tuple[int, int]):
        pass

    def __contains__(self, item):
        pass


class Box:
    def __init__(
        self, p1: Tuple[int, int], p2: Tuple[int, int], /, screen: SurfaceType = None
    ):
        """Simple class representing area.

        Args:
            p1: top_left corner
            p2: bottom_right corner
        """

        self.screen = screen if screen else GlobalSetting.surface

        self.x1, self.y1 = p1
        self.x2, self.y2 = p2

        # pre-cache
        self.width = self.x2 - self.x1
        self.height = self.y2 - self.y1
        self.pos_full = (*p1, *p2)
        # self.rect = Rect(*p1, *p1)

        # defaults to white
        self.color = (255, 255, 255, 255)

        # bake render method
        self._render = partial(self.screen.fill, self.color, self.pos_full)

    def set_color(self, r, g, b, a=255):
        """Sets color."""

        self.color = r, g, b, a
        self._render = partial(self.screen.fill, self.color, self.pos_full)

    def draw(self) -> Rect:
        """Draws UI. Returns drawn area"""

        return self._render()


class ButtonMixin:
    def on_click(self: Box, coordinate: Tuple[int, int]):
        """Action upon click. touch coordinate is given as argument."""

        pass

    def __contains__(self: Box, item: Tuple[int, int]):
        """Checks if given coordinate is within area"""

        return (self.x1 <= item[0] <= self.x2) and (self.y1 <= item[1] <= self.y2)


class TextBox(Box):
    def __init__(
        self,
        p1,
        p2,
        text: str,
        text_color: Tuple[int, int, int, int] = (0, 0, 0, 255),
        /,
        font: FontType = None,
        antialias: bool = True,
        screen=None,
    ):
        """Static Text Box Element"""

        super().__init__(p1, p2, screen)

        self.text = text
        self.text_color = text_color
        self.aa = antialias
        self.font = font if font else GlobalSetting.font

        assert (
            self.font is not None
        ), "You must set global font or provide font argument."

        self._render_txt: Callable[[], SurfaceType]
        self._render_txt = partial(
            self.font.render, self.text, self.aa, self.text_color
        )

    def set_text_color(self, r, g, b, a=255):
        """Sets color."""

        self.text_color = r, g, b, a
        self._render_txt = partial(
            self.font.render, self.text, self.aa, self.text_color
        )

    def draw(self):
        rect = self._render()

        rendered: SurfaceType = self._render_txt()
        new_x = ((self.width - rendered.get_width()) // 2) + self.x1
        new_y = ((self.height - rendered.get_height()) // 2) + self.y1

        self.screen.blit(self._render_txt(), (new_x, new_y))
        return rect
