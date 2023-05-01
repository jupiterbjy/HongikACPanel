"""
RPi Frame Buffer Driver using pygame.

Primarily intended for weak devices like 1B+ where even mere x server is too heavy.

Uses trio to await for extra stability & safety.

Following is referenced from:
https://stackoverflow.com/a/54986161/10909029
"""

import time
import pathlib

import pygame
import trio


__all__ = ["FramebufferDriver"]

ROOT = pathlib.Path(__file__).parent

# Splash file to show up on framebuffer for testing - merely 26 KiB on memory.
# Probably a tiny bit intended to keep Hina loaded on memory.
SPLASH_IMG_PATH = ROOT / "splash.png"
TEST_SPLASH_FILE = pygame.image.load(SPLASH_IMG_PATH.as_posix())

# Test screen via
# while true; do sudo cat /dev/urandom > /dev/fb1; sleep .01; done
# sudo fbi -T 2 -d /dev/fb1 -noverbose -a splash.png


class FramebufferDriver:

    def __init__(self, screen_x, screen_y, bit_depth=16, fb_id=0):
        """Initializes a new pygame screen using the Frame Buffer.

        Args:
            screen_x: Screen X pixels
            screen_y: Screen Y pixels
            bit_depth: Bits depth of pygame surface. 16 for GPIO LCD, 24 otherwise
            fb_id: Framebuffer ID. Default 0

        Raises:
            NoUsableDriverError: If there's no usable framebuffer drivers
        """

        self.dim = (screen_x, screen_y)
        self.bit_depth = bit_depth

        self.fb: trio.Path = trio.Path(f"/dev/fb{fb_id}")
        # leaving file open is not safe usually, but for framebuffer why not.

        print(f"Using {self.fb}")

        # Safe to call init multiple time anyway!
        pygame.init()
        self.screen = pygame.Surface(self.dim, depth=bit_depth)

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

        # basically

        self.screen.blit(TEST_SPLASH_FILE, (0, 0))

    def blank(self):
        self.screen.fill((0, 0, 0))


if __name__ == "__main__":
    # Create an instance of the PyScope class, assuming rpi, 480 320
    driver = FramebufferDriver(480, 320, 1)

    driver.show_splash()
    driver.update_sync()

    time.sleep(10)

    driver.blank()
    driver.update_sync()
