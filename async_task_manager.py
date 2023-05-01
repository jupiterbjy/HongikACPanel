"""
Simple asynchronous task executor.
Designed with UI callback handling in mind, so UI click spam
won't take everything down with it.
"""

from typing import Callable, Awaitable, Any, Union

import trio
from loguru import logger


__all__ = ["AsyncTaskManager"]


class AsyncTaskManager:
    def __init__(self, max_concurrency=4, execute_interval=0.1):
        """Receive & execute tasks with simple throttling & graceful shutdown.

        Args:
            max_concurrency: Max number of simultaneous tasks.
                                  Drops the oldest task to accept the newest.
            execute_interval: Task scheduling interval.
        """
        self.max_concurrency = max_concurrency
        self.exe_interval = execute_interval

        # binding again to make pylint acknowledge type hint
        s_ch, r_ch = trio.open_memory_channel(max_concurrency)
        self._send_ch: trio.MemorySendChannel = s_ch
        self._recv_ch: trio.MemoryReceiveChannel = r_ch

        self._nursery: Union[trio.Nursery, None] = None

    async def run_executor(self):
        """Opens new memory channel & starts executor task."""

        async with trio.open_nursery() as nursery:
            self._nursery = nursery

            # await for incoming tasks
            async for task, args in self._recv_ch:
                logger.debug("Receiving task {}", task.__name__)

                # if there's headroom in concurrency lim, start new task
                # trio.CapacityLimiter or Lock is overkill for this
                if len(nursery.child_tasks) < self.max_concurrency:
                    nursery.start_soon(task, *args)
                else:
                    logger.debug("Tasks full, dropped {}", task.__name__)

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

            logger.debug("Queue full, dropped '{}'", func.__name__)

    async def stop_executor(self):
        """Stops memory channel & executor gracefully."""

        await self._send_ch.aclose()

        # if nursery is still not closed then manually cancel
        if self._nursery.child_tasks:
            await self._nursery.cancel_scope.cancel()
