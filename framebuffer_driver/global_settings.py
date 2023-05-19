"""
Deals with global settings
"""

from os import environ
import pathlib

import pygame


__all__ = ["GlobalSetting", "framebuffer_init"]


SPLASH_IMG_PATH = pathlib.Path(__file__).parent / "splash.bmp"


class GlobalSetting:
    """Settings singleton"""
    fb: pathlib.Path | None = None

    # Splash file to show up on framebuffer for testing - merely 26 KiB on memory.
    # Probably a tiny bit intended to keep Hina loaded on memory.
    test_img = pygame.image.load(SPLASH_IMG_PATH.as_posix())


# could also test screen via
# while true; do sudo cat /dev/urandom > /dev/fb1; sleep .01; done
# or
# sudo fbi -T 2 -d /dev/fb1 -noverbose -a splash.png


def framebuffer_init(fb: str = None):
    """Sets global configuration. Optional."""

    if fb:
        GlobalSetting.fb = pathlib.Path(fb)
    else:
        try:
            GlobalSetting.fb = pathlib.Path(environ["FRAMEBUFFER"])
        except KeyError:
            # use fb1 instead
            print("FRAMEBUFFER not set, defaulting to /dev/fb0.")
            GlobalSetting.fb = pathlib.Path("/dev/fb0")

    # Assert fb exists
    if not GlobalSetting.fb.exists():
        raise FileNotFoundError(f"Can't access framebuffer {GlobalSetting.fb}")
