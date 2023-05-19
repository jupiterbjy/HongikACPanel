"""
UI, Framebuffer driver & touch driver test code
"""

import pygame
import trio
from loguru import logger

from basic_ui_framework import *
from framebuffer_driver import *
from touch_driver import *

pygame.init()


def bake_ui():
    _trans = (25, 25, 25, 255)
    symbol_font = pygame.font.SysFont("freeserif", 50)
    temp_font = pygame.font.SysFont("notosansmono", 50)
    state_font = pygame.font.SysFont("undotum", 40)

    ui = {
        "Temp up": TextButton(
            (10, 10), (70, 70), "▲", color=(255, 0, 0, 255), font=symbol_font
        ),
        "Temp down": TextButton(
            (10, 80), (70, 140), "▼", color=(0, 0, 255, 255), font=symbol_font
        ),
        "Power": TextButton(
            (10, 250), (70, 310), "⚡", color=(50, 0, 0, 255), font=symbol_font
        ),
        "Temp target": TextBox(
            (220, 10),
            (470, 70),
            "TGT --°C",
            color=_trans,
            text_color=(0, 255, 0, 255),
            font=temp_font,
        ),
        "Temp current": TextBox(
            (220, 80),
            (470, 140),
            "CUR --°C",
            color=_trans,
            text_color=(255, 255, 255, 255),
            font=temp_font,
        ),
        # "Wind angle": TextBox((100, 80), (100, 130), "WC", color=_trans, text_color=(255, 255, 255, 255)),
        # "Wind speed": TextBox((100, 80), (100, 130), "CUR: --'C", color=_trans, text_color=(255, 255, 255, 255)),
        "Operation Mode": TextBox(
            (370, 260),
            (470, 310),
            "꺼짐",
            color=_trans,
            text_color=(255, 255, 255, 255),
            font=state_font,
        ),
    }

    return UIManager(**ui)


async def main():
    framebuffer_init()
    fb_d = FramebufferDriver()
    fb_d.update_sync()

    touch_d = TouchDriver("LCD35", "event0")

    ui_framework_init(fb_d.screen)
    ui = bake_ui()

    async with trio.open_nursery() as nursery:
        # load loops
        nursery.start_soon(ui.poll_touch, touch_d)

        logger.debug("Startup complete")

        while True:
            ui.draw_all()
            nursery.start_soon(fb_d.update)
            await trio.sleep(0.1)


trio.run(main)
