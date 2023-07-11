"""
UI with some logging settings
"""

import pathlib
from argparse import ArgumentParser

import trio
from loguru import logger

from framebuffer_driver import FramebufferDriver, framebuffer_init
from touch_driver import TouchDriver
from basic_ui_framework import ui_framework_init
from api import ACManager
# from async_task_manager import AsyncTaskManager
from app import ACApp


# TODO: add loguru settings

async def main(args):

    # check buffer param
    buffer = pathlib.Path(args.buffer) if args.buffer else None

    # task_manager = AsyncTaskManager()
    framebuffer_init()
    fb_d = FramebufferDriver(buffer)
    fb_d.show_splash()
    fb_d.update_sync()

    # init touch driver
    touch_d = TouchDriver("LCD35", "event0")

    # init ui framework
    ui_framework_init(fb_d.screen)

    ac_mgr = ACManager(args.ip, args.id, args.pw)

    app = ACApp(ac_mgr, touch_d, fb_d)

    # init app
    await app.init()

    async with trio.open_nursery() as nursery:
        # load loops
        # nursery.start_soon(ac_mgr.keep_alive_power)
        # nursery.start_soon(task_manager.run_executor)
        nursery.start_soon(app.ui.poll_touch, touch_d)
        nursery.start_soon(app.update_temp_loop)

        logger.debug("Startup complete")


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument("ip", type=str, help="Web remote controller IP")
    parser.add_argument("id", type=str, help="Web remote controller id")
    parser.add_argument("pw", type=str, help="Web remote controller password")
    parser.add_argument(
        "-b", "--buffer", type=str, default="", help="Web remote controller password"
    )
    parser.add_argument("-t", "--temp", type=int, default=26, help="Target temperature")

    trio.run(main, parser.parse_args())
