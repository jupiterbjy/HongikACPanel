"""
Application definition. This is just a control class.
"""

import time
from random import randint


import pygame
import trio
from loguru import logger

from framebuffer_driver import FramebufferDriver
from touch_driver import TouchDriver
from basic_ui_framework import *
from api import ACManager, ACTempOutOfBound


__all__ = ["ACApp"]


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
            (10, 250), (70, 310), "⚡", color=(100, 100, 100, 255), font=symbol_font
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


class ACApp:
    def __init__(
        self,
        ac_mgr: ACManager,
        touch_driver: TouchDriver,
        fb_driver: FramebufferDriver,
    ):
        super().__init__()

        pygame.font.init()

        self._ac_manager = ac_mgr

        self._touch_driver = touch_driver
        self._fb_driver = fb_driver

        # some common stuffs for rendering
        self.screen = fb_driver.screen
        self._font = pygame.font.Font(None, 50)

        self.ui = bake_ui()

        # register callback
        self.ui["Temp up"].on_click = self.toggle_power_pressed
        self.ui["Temp down"].on_click = self.temp_down_pressed
        self.ui["Power"].on_click = self.temp_up_pressed

        self.last_update = time.time()

    async def init(self):
        """Init job that requires async"""

        self._fb_driver.show_splash()

        await self._fb_driver.update()
        await self._ac_manager.login()

    async def draw_ui(self):
        """Draw ui"""

        self.ui.draw_all()
        await self._fb_driver.update()

    async def graceful_shutdown(self):
        """Attempt graceful shutdown"""

        if self._ac_manager.is_powered:
            await self._ac_manager.power_off()
            await self.draw_ui()

    async def temp_up_pressed(self, ui_element: Box, *_):
        """Temp up button action"""

        # Start with Yellow color to indicate we're doing something
        prev_color = ui_element.color
        ui_element.set_color(255, 255, 0, 255)
        ui_element.draw()
        await self._fb_driver.update()

        try:
            await self._ac_manager.temp_up()
        except ACTempOutOfBound:
            # make target temp text red for 1 sec
            return

        ui_element.set_color(*prev_color)
        self._update_target_temp()
        await self.draw_ui()
        # else make target temp text green for 1 sec

    async def temp_down_pressed(self, ui_element: Box, *_):
        """Temp down button action"""

        prev_color = ui_element.color
        ui_element.set_color(255, 255, 0, 255)
        ui_element.draw()
        await self._fb_driver.update()

        try:
            await self._ac_manager.temp_down()
        except ACTempOutOfBound:
            # make target temp text red for 1 sec
            return

        ui_element.set_color(*prev_color)
        self._update_target_temp()
        await self.draw_ui()
        # else make target temp text green for 1 sec

    async def toggle_power_pressed(self, ui_element, *_):
        """Power button toggle action"""

        ui_element.set_color(255, 255, 0, 255)
        ui_element.draw()
        await self._fb_driver.update()

        if self._ac_manager.is_powered:
            await self._ac_manager.power_off()
            ui_element.set_color(150, 150, 150, 255)
            # disable all display output
        else:
            await self._ac_manager.power_on()
            ui_element.set_color(0, 255, 0, 255)
            # enable all display output

        # TODO: change power button color
        await self.draw_ui()

    def _update_target_temp(self):
        """Updates target temp on screen"""

        tgt_temp = self._ac_manager.target_temp
        self.ui["Temp target"].set_text(f"TGT {tgt_temp}°C")

    async def _update_current_temp(self):
        """Updates current temp on screen"""

        cur_temp = await self._ac_manager.get_temp()
        self.last_update = time.time()
        self.ui["Temp current"].set_text(f"CUR {cur_temp}°C")

    async def update_temp_loop(self, interval_sec=60, max_deviation_sec=10):
        """Updates temps continuously with interval"""

        logger.debug("Temp update started")

        while True:
            target_sleep = interval_sec + randint(0, max_deviation_sec)

            # sleep until desired interval from last_update is reached.
            while time.time() < (self.last_update + target_sleep):
                await trio.sleep(10)

            await self._update_current_temp()
            await self.draw_ui()

