"""
UI part
"""

from argparse import ArgumentParser
from random import randint
from typing import Tuple, Union

import trio
import pygame
from loguru import logger

from api import ACManager, ACTempOutOfBound
from framebuffer_driver import FramebufferDriver
from async_task_manager import AsyncTaskManager
from touch_driver import TouchDriver


SCREEN_TYPE = "LCD35"
TOUCH_DEVICE = "event0"


# TODO: add LCD protection using black screen after designated time w/o input.


class Area:
    def __init__(self, p1: tuple[int, int], p2: Tuple[int, int], r, g, b):
        """Simple class representing area.

        Args:
            p1: top_left corner
            p2: bottom_right corner
        """

        self.x1, self.y1 = p1
        self.x2, self.y2 = p2
        self.pos_full = (*p1, *p2)

        self.color = (r, g, b)

        # TODO: add dim feature when selected

    def __contains__(self, item: tuple[int, int]):
        return (self.x1 <= item[0] <= self.x2) and (self.y1 <= item[1] <= self.y2)

    def draw(self, screen: pygame.Surface, color: Tuple[int, int, int, int] = None):
        if color is None:
            color = self.color

        screen.fill(color, self.pos_full)


class DumbUI:
    # Temporary UI designation - (pos1, pos2, color)
    # 16 bit is 1 unused, RGB each 5 bits, so need to be smaller than 31.
    # But in test - screen accept ~255 range...? What??
    ui_pos = {
        "power": Area((10, 10), (50, 50), 0, 255, 0),
        "down": Area((10, 60), (50, 110), 0, 0, 255),
        "up": Area((10, 120), (50, 170), 255, 0, 0),
    }

    tgt_temp_pos = (350, 10)
    current_temp_pos = (350, 60)

    @classmethod
    def find_hit_pos(cls, coordinate: Tuple[int, int]) -> Union[str, None]:
        """Dumb code finding which ui component touch falls into.
        Will return UI name if matched, otherwise
        """

        for key, area in cls.ui_pos.items():
            if coordinate in area:
                return key

        return None


class ACApp:
    def __init__(
        self,
        ac_mgr: ACManager,
        task_mgr: AsyncTaskManager,
        touch_driver: TouchDriver,
        fb_driver: FramebufferDriver,
    ):
        super().__init__()

        pygame.font.init()

        self._ac_manager = ac_mgr
        self._task_mgr = task_mgr

        self._touch_driver = touch_driver
        self._fb_driver = fb_driver

        # some common stuffs for rendering
        self.screen = fb_driver.screen
        self._font = pygame.font.Font(None, 50)

        # register callback
        self._callback = {
            "power": self.toggle_power_pressed,
            "down": self.temp_down_pressed,
            "up": self.temp_up_pressed,
        }

    async def init(self):
        """Init job that requires async"""

        self._fb_driver.show_splash()
        await self._fb_driver.update()

        await self._ac_manager.login()

    def draw_areas(self):
        for _, area in DumbUI.ui_pos:
            area.draw(self.screen)

        self._fb_driver.update()

    async def graceful_shutdown(self):
        """Attempt graceful shutdown"""

        if self._ac_manager.is_powered:
            await self._ac_manager.power_off()

    async def temp_up_pressed(self):
        """Temp up button action"""

        try:
            await self._ac_manager.temp_up()
        except ACTempOutOfBound:
            # make target temp text red for 1 sec
            return

        # else make target temp text green for 1 sec

    async def temp_down_pressed(self):
        """Temp down button action"""

        try:
            await self._ac_manager.temp_down()
        except ACTempOutOfBound:
            # make target temp text red for 1 sec
            return

        # else make target temp text green for 1 sec

    async def toggle_power_pressed(self):
        """Power button toggle action"""

        if self._ac_manager.is_powered:
            await self._ac_manager.power_off()
            # disable all display output
        else:
            await self._ac_manager.is_powered()
            # enable all display output

    async def poll_touch(self, interval=0.1):
        """Due to lack of trio support in evdev, using loop temporarily."""

        logger.debug("Touch polling started")

        while True:
            await trio.sleep(interval)

            # get touch input
            touch = self._touch_driver.receive_touch()
            if touch is None:
                continue

            # check where it falls to
            area_name = DumbUI.find_hit_pos(touch)

            # if hit something, then run callback
            if area_name is not None:
                self._task_mgr.add_task(self._callback[area_name])

    async def _update_target_temp(self):
        """Updates target temp on screen"""
        tgt_temp = self._ac_manager.target_temp
        rendered = self._font.render(
            f"{tgt_temp}°C", True, (255, 255, 255), background=(0, 0, 0)
        )

        self.screen.blit(rendered, DumbUI.tgt_temp_pos)

    async def _update_current_temp(self):
        """Updates current temp on screen"""
        cur_temp = await self._ac_manager.get_temp()
        rendered = self._font.render(
            f"{cur_temp}°C", True, (255, 100, 100), background=(0, 0, 0)
        )

        self.screen.blit(rendered, DumbUI.tgt_temp_pos)

    async def update_temp_loop(self, interval_sec=60, max_deviation_sec = 10):
        """Updates temps continuously with interval"""

        logger.debug("Temp update started")

        while True:
            await trio.sleep(interval_sec + randint(0, max_deviation_sec))
            await self._update_current_temp()
            await self._update_target_temp()
            await self._fb_driver.update()


async def main(args):

    ac_mgr = ACManager(args.ip, args.id, args.pw)
    task_manager = AsyncTaskManager()

    fb_driver = FramebufferDriver(480, 320)
    touch_driver = TouchDriver(SCREEN_TYPE, TOUCH_DEVICE)

    app = ACApp(ac_mgr, task_manager, touch_driver, fb_driver)

    # init app
    await app.init()

    async with trio.open_nursery() as nursery:
        # load loops
        nursery.start_soon(ac_mgr.keep_alive_power)
        nursery.start_soon(task_manager.run_executor)
        nursery.start_soon(app.poll_touch)
        nursery.start_soon(app.update_temp_loop)

        logger.debug("Startup complete")


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument("ip", type=str, help="Web remote controller IP")
    parser.add_argument("id", type=str, help="Web remote controller id")
    parser.add_argument("pw", type=str, help="Web remote controller password")
    parser.add_argument("-t", "--temp", type=int, default=26, help="Target temperature")

    trio.run(main, parser.parse_args())
