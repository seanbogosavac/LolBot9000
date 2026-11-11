"""Run blocking Riot API calls without freezing the Discord event loop.

`RiotClient` is synchronous and its rate-limit handling sleeps in place, so calling it
directly from a coroutine stalls the whole event loop — including Discord heartbeats,
which logs "heartbeat blocked for more than N seconds" and can drop the gateway.

These calls go through a single-worker executor on purpose: `requests.Session` is not
thread-safe, so serialising them keeps the same one-request-at-a-time behaviour the
blocking code had, while the event loop stays free.
"""
import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial

__all__ = ["run_blocking"]

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="riot-api")


async def run_blocking(func: Callable, *args, **kwargs):
    """Call `func` on the Riot worker thread and await its result."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, partial(func, *args, **kwargs))
