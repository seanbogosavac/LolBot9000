import asyncio
import threading
import time

import pytest

from bot.api_worker import run_blocking


def test_blocking_call_runs_off_the_event_loop():
    """A slow call must not freeze other coroutines waiting on the same loop."""

    async def scenario():
        ticks = []

        async def heartbeat():
            while True:
                await asyncio.sleep(0.01)
                ticks.append(time.perf_counter())

        hb = asyncio.create_task(heartbeat())
        await run_blocking(time.sleep, 0.2)  # the rate-limit sleep, off the loop
        hb.cancel()
        return len(ticks)

    ticks = asyncio.run(scenario())
    # 200ms at 10ms cadence: a blocked loop would produce ~0-1 ticks
    assert ticks > 10, f"event loop was starved, only {ticks} heartbeats during the sleep"


def test_blocking_call_returns_its_value_and_propagates_exceptions():
    async def scenario():
        assert await run_blocking(lambda a, b: a + b, 2, 3) == 5

        def boom():
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            await run_blocking(boom)

    asyncio.run(scenario())


def test_keyword_arguments_are_forwarded():
    async def scenario():
        return await run_blocking(lambda *, name: name, name="Maxime")

    assert asyncio.run(scenario()) == "Maxime"


def test_calls_are_serialised_on_one_thread():
    """requests.Session is not thread-safe, so the worker must stay single."""
    seen = set()

    def record():
        seen.add(threading.current_thread().name)
        time.sleep(0.01)

    async def scenario():
        await asyncio.gather(*(run_blocking(record) for _ in range(20)))

    asyncio.run(scenario())
    assert len(seen) == 1, f"calls spread across threads: {seen}"


def test_sequential_calls_do_not_overlap():
    """Overlapping Riot calls would re-introduce the concurrency the sync client can't handle."""
    active = 0
    peak = 0

    def tracked():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        time.sleep(0.01)
        active -= 1

    async def scenario():
        await asyncio.gather(*(run_blocking(tracked) for _ in range(10)))

    asyncio.run(scenario())
    assert peak == 1, f"{peak} Riot calls ran concurrently"
