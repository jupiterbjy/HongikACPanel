"""
UI with some logging settings
"""

import trio
from loguru import logger

from ui import main


# TODO: add loguru settings

trio.run(main)
