"""
Test touch
"""

import trio
import pygame

from framebuffer_driver import *
from touch_driver import *


async def main():
    framebuffer_init("/dev/fb1")

    fb_driver = FramebufferDriver()
    input_driver = TouchDriver("LCD35", "event0")

    fb_driver.show_splash()
    await fb_driver.update()

    async with trio.open_nursery() as nursery:
        while True:
            pos = input_driver.receive_touch()

            if pos:
                print(f"Touch at {pos}")
                pygame.draw.circle(fb_driver.screen, (255, 0, 0, 100), pos, 10)
                nursery.start_soon(fb_driver.update)

            await trio.sleep(0.1)


trio.run(main)
