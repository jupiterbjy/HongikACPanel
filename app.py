"""
Application definition. This is just a control class.
"""
from random import randint

import pygame
import trio
from loguru import logger

from framebuffer_driver import FramebufferDriver
from touch_driver import TouchDriver
from basic_ui_framework import *
from api import ACManager, ACTempOutOfBound
from async_task_manager import AsyncTaskManager


__all__ = ["UI", "ACApp"]


class UI:
    pygame.font.init()
    font = pygame.font.Font(None, 50)
    _trans = (0, 0, 0, 0)

    ui = {
        "Temp up": TextButton((10, 10), (70, 70), "▲", color=(255, 0, 0, 255)),
        "Temp down": TextButton((10, 80), (70, 150), "▼", color=(0, 0, 255, 255)),

        "Power": TextButton((10, 250), (70, 310), "⏻", color=(255, 255, 255, 255)),

        "Temp target": TextBox((100, 10), (100, 50), "TGT --°C", color=_trans, text_color=(0, 255, 0, 255)),
        "Temp current": TextBox((100, 80), (100, 130), "CUR --°C", color=_trans, text_color=(255, 255, 255, 255)),

        # "Wind angle": TextBox((100, 80), (100, 130), "WC", color=_trans, text_color=(255, 255, 255, 255)),
        # "Wind speed": TextBox((100, 80), (100, 130), "CUR: --'C", color=_trans, text_color=(255, 255, 255, 255)),

        "Operation Mode": TextBox((370, 260), (470, 310), "BOOTING", color=_trans, text_color=(255, 255, 255, 255)),
    }

    ui_manager = UIManager(**ui)


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

        self.ui = UI.ui_manager

        # register callback
        self.ui["Temp up"].on_click = self.toggle_power_pressed
        self.ui["Temp down"].on_click = self.temp_down_pressed
        self.ui["Power"].on_click = self.temp_up_pressed

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

    async def temp_up_pressed(self, *_):
        """Temp up button action"""

        try:
            await self._ac_manager.temp_up()
        except ACTempOutOfBound:
            # make target temp text red for 1 sec
            return

        # else make target temp text green for 1 sec

    async def temp_down_pressed(self, *_):
        """Temp down button action"""

        try:
            await self._ac_manager.temp_down()
        except ACTempOutOfBound:
            # make target temp text red for 1 sec
            return

        # else make target temp text green for 1 sec

    async def toggle_power_pressed(self, *_):
        """Power button toggle action"""

        if self._ac_manager.is_powered:
            await self._ac_manager.power_off()
            # disable all display output
        else:
            await self._ac_manager.is_powered()
            # enable all display output

    def _update_target_temp(self):
        """Updates target temp on screen"""

        tgt_temp = self._ac_manager.target_temp
        self.ui["Temp target"].set_text(f"TGT {tgt_temp}°C")

    async def _update_current_temp(self):
        """Updates current temp on screen"""

        cur_temp = await self._ac_manager.get_temp()
        self.ui["Temp current"].set_text(f"CUR {cur_temp}°C")

    async def update_temp_loop(self, interval_sec=60, max_deviation_sec=10):
        """Updates temps continuously with interval"""

        logger.debug("Temp update started")

        while True:
            await trio.sleep(interval_sec + randint(0, max_deviation_sec))
            await self._update_current_temp()
            await self.draw_ui()

