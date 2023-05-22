"""
UI with some logging settings
"""

import pathlib
from argparse import ArgumentParser

import trio
from loguru import logger

from framebuffer_driver import FramebufferDriver
from touch_driver import TouchDriver
from api import ACManager
# from async_task_manager import AsyncTaskManager
from app import ACApp


# TODO: add loguru settings

async def main(args):
    # task_manager = AsyncTaskManager()
    fb_driver = FramebufferDriver(args.buffer)

    ac_mgr = ACManager(args.ip, args.id, args.pw)

    touch_driver = TouchDriver("LCD35", "event0")

    app = ACApp(ac_mgr, touch_driver, fb_driver)

    # init app
    await app.init()

    async with trio.open_nursery() as nursery:
        # load loops
        # nursery.start_soon(ac_mgr.keep_alive_power)
        # nursery.start_soon(task_manager.run_executor)
        nursery.start_soon(app.ui.poll_touch)
        nursery.start_soon(app.update_temp_loop)

        logger.debug("Startup complete")


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument("ip", type=str, help="Web remote controller IP")
    parser.add_argument("id", type=str, help="Web remote controller id")
    parser.add_argument("pw", type=str, help="Web remote controller password")
    parser.add_argument(
        "-b", "--buffer", type=pathlib.Path, default=None, help="Web remote controller password"
    )
    parser.add_argument("-t", "--temp", type=int, default=26, help="Target temperature")

    trio.run(main, parser.parse_args())
