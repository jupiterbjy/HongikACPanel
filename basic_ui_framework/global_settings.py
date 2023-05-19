"""
Deals with global settings
"""

from pygame import SurfaceType
from pygame.font import FontType


__all__ = ["GlobalSetting", "ui_framework_init"]


class GlobalSetting:
    """Settings singleton"""
    surface: SurfaceType | None = None
    font: FontType = None


def ui_framework_init(surface: SurfaceType = None, font: FontType = None):
    """Set global configuration. Optional."""

    GlobalSetting.surface = surface
    GlobalSetting.font = font
