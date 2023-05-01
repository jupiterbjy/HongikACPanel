"""
Simple asynchronous task executor
"""

from typing import Callable, Awaitable, Any, Union

import trio
from loguru import logger


class AsyncTaskManager:
    def __init__(self, queue_size=4, execute_interval=0.1):
        self.exe_interval = execute_interval

        # binding twice to make pylint acknowledge this type hint
        s_ch, r_ch = trio.open_memory_channel(queue_size)
        self._send_ch: trio.MemorySendChannel = s_ch
        self._recv_ch: trio.MemoryReceiveChannel = r_ch

        self._nursery: Union[trio.Nursery, None] = None

    async def run_executor(self):
        """Opens new memory channel & starts executor task"""

        async with trio.open_nursery() as nursery:
            self._nursery = nursery

            async for task, args in self._recv_ch:

                # log received func name - not expecting to receive class here
                logger.debug("Receiving task {}", task.__name__)

                nursery.start_soon(task, *args)
                await trio.sleep(self.exe_interval)

        logger.debug("Executor stopped")

    def add_task(self, async_task: Callable[[Any], Awaitable], *args):
        """Adds task to executor

        Args:
            async_task: Async function - Not the resulting coroutine or Awaitable Class.
            *args: Args for calling async_task. Use partial if you want kwargs.
        """

        try:
            self._send_ch.send_nowait(async_task, args)

        except trio.WouldBlock:
            # if queue's full then drop item & add new synchronously.
            func, _ = self._recv_ch.receive_nowait()
            self._send_ch.send_nowait(async_task, args)

            logger.debug("Queue full, Dropped func '{}'", func.__name__)

    async def stop_executor(self):
        """Stops memory channel & executor gracefully."""

        await self._send_ch.aclose()

        # if nursery is still not closed then manually cancel
        if self._nursery.child_tasks:
            await self._nursery.cancel_scope.cancel()
