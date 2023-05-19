"""
RPi Frame Buffer wrapper for pygame.
Primarily intended for weak devices like 1B+ where even mere x server is too heavy.

Uses trio to await for extra stability & safety.

Might need libsdl2-dev installed to install pygame on 1B+ w/ python 3.11.

Following is referenced from:
https://stackoverflow.com/a/54986161/10909029
"""

import subprocess
from typing import Tuple

import pygame
import trio

from .global_settings import GlobalSetting


__all__ = ["FramebufferDriver"]
# __all__ = [k for k, v in dir() if not k.startswith("_")]


def get_fb_info(fb="/dev/fb0") -> Tuple[int, int, int]:
    """Gets frame buffer info. Returns (width, height, bit_depth)"""

    cmd = f"fbset -fb {fb} | grep geometry"
    returned = subprocess.run(cmd, capture_output=True, shell=True)
    assert returned.returncode == 0, f"Return code from command '{cmd}' was {returned.returncode}"

    # result format is '   geometry 480 320 480 320 16'
    x, y, _, _, bits = map(int, returned.stdout.decode().strip().split(" ")[1:])
    return x, y, bits


class FramebufferDriver:
    def __init__(self, fb: str = None):
        """Initializes a new pygame screen using the Frame Buffer.

        Args:
            fb: Framebuffer name. Defaults to /dev/fb0 if None.

        Raises:
            NoUsableDriverError: If there's no usable framebuffer drivers
        """

        if fb is None:
            fb = GlobalSetting.fb

        self.fb: trio.Path = trio.Path(fb)
        print("Using", self.fb)
        # leaving file open is not safe usually, but for framebuffer why not.

        # Safe to call init multiple time anyway!
        pygame.init()

        self.width, self.height, self.depth = get_fb_info(fb)
        self.screen = pygame.Surface((self.width, self.height), depth=self.depth)

    def update_sync(self):
        """Synchronous framebuffer."""

        with open(self.fb, "wb") as fp:
            # noinspection PyTypeChecker
            fp.write(self.screen.get_buffer())

    async def update(self):
        """Update framebuffer."""

        # there's option to set pygame in 16bit, might need to check that out
        await self.fb.write_bytes(self.screen.get_buffer())

    def __del__(self):
        """Destructor to make sure pygame shuts down, etc."""

    def show_splash(self):
        """Shows splash image"""

        self.screen.blit(GlobalSetting.test_img, (0, 0))

    def blank(self):
        self.screen.fill((0, 0, 0))
