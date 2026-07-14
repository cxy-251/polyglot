"""284｜asyncio Semaphore capacity、async context 与 BoundedSemaphore invariant。

Semaphore counter 为零时 acquire suspend，release 可超过初始容量；BoundedSemaphore 则把
over-release 当作配对错误。locked 表示当前不能立即 acquire，并不授予未来执行保证。
案例用 Event gate 同时占满两个 permit，不依靠 wall-clock delay 判断并发上限。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Semaphore
# polyglot-covers: python.asyncio.Semaphore.acquire
# polyglot-covers: python.asyncio.Semaphore.release
# polyglot-covers: python.asyncio.Semaphore.locked
# polyglot-covers: python.asyncio.Semaphore-negative-initial-error
# polyglot-covers: python.asyncio.Semaphore-over-release-allowed
# polyglot-covers: python.asyncio.Semaphore-async-context-manager
# polyglot-covers: python.asyncio.Semaphore-concurrency-limit
# polyglot-covers: python.asyncio.BoundedSemaphore
# polyglot-covers: python.asyncio.BoundedSemaphore-over-release

import asyncio

import pytest


def test_semaphore_limits_simultaneous_sections_without_real_time_waits():
    async def scenario():
        semaphore = asyncio.Semaphore(2)
        started = [asyncio.Event() for _ in range(3)]
        two_inside = asyncio.Event()
        release = asyncio.Event()
        active = 0
        maximum = 0

        async def worker(index):
            nonlocal active, maximum
            started[index].set()
            async with semaphore:
                active += 1
                maximum = max(maximum, active)
                if active == 2:
                    two_inside.set()
                await release.wait()
                active -= 1

        tasks = [asyncio.create_task(worker(index)) for index in range(3)]
        await asyncio.gather(*(event.wait() for event in started))
        await two_inside.wait()
        assert semaphore.locked() is True
        assert active == 2

        release.set()
        await asyncio.gather(*tasks)
        assert maximum == 2
        assert active == 0
        assert semaphore.locked() is False

    asyncio.run(scenario())


def test_plain_semaphore_allows_extra_release_but_bounded_variant_rejects_it():
    async def scenario():
        semaphore = asyncio.Semaphore(0)
        assert semaphore.locked() is True
        semaphore.release()
        semaphore.release()
        assert await semaphore.acquire() is True
        assert await semaphore.acquire() is True
        assert semaphore.locked() is True

        bounded = asyncio.BoundedSemaphore(1)
        assert await bounded.acquire() is True
        bounded.release()
        with pytest.raises(ValueError, match="BoundedSemaphore released too many times"):
            bounded.release()

    asyncio.run(scenario())


def test_negative_initial_semaphore_value_is_rejected():
    with pytest.raises(ValueError, match="Semaphore initial value must be >= 0"):
        asyncio.Semaphore(-1)
