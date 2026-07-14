"""282｜asyncio Lock fairness、async context 与 Event level-triggered broadcast。

Lock 只协调同一 event loop 的 Task，不是 OS-thread lock；排队 acquire 按先到先得公平唤醒。
async with 保证异常路径 release。Event 是可重复读取的 level flag：set 唤醒全部当前 waiter，
后来 wait 也立即成功，直到 clear。原语本身没有 timeout 参数，应外包 wait_for。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Lock
# polyglot-covers: python.asyncio.Lock.acquire
# polyglot-covers: python.asyncio.Lock.release
# polyglot-covers: python.asyncio.Lock.locked
# polyglot-covers: python.asyncio.Lock-fifo-fairness
# polyglot-covers: python.asyncio.Lock-async-context-manager
# polyglot-covers: python.asyncio.Lock-unlocked-release-error
# polyglot-covers: python.asyncio.Event
# polyglot-covers: python.asyncio.Event.wait
# polyglot-covers: python.asyncio.Event.set
# polyglot-covers: python.asyncio.Event.clear
# polyglot-covers: python.asyncio.Event.is_set
# polyglot-covers: python.asyncio.Event-wake-all
# polyglot-covers: python.asyncio.Event-level-triggered
# polyglot-covers: python.asyncio.sync-primitives-no-timeout-parameter
# polyglot-covers: python.asyncio.sync-primitives-not-thread-safe

import asyncio

import pytest


def test_lock_waiters_acquire_in_arrival_order_and_context_releases():
    async def scenario():
        lock = asyncio.Lock()
        assert await lock.acquire() is True
        assert lock.locked() is True
        arrived = [asyncio.Event(), asyncio.Event()]
        order = []

        async def waiter(index):
            arrived[index].set()
            async with lock:
                order.append(index)

        tasks = [asyncio.create_task(waiter(index)) for index in range(2)]
        await asyncio.gather(*(event.wait() for event in arrived))
        lock.release()
        await asyncio.gather(*tasks)

        assert order == [0, 1]
        assert lock.locked() is False

        with pytest.raises(LookupError):
            async with lock:
                raise LookupError("body failed")
        assert lock.locked() is False
        with pytest.raises(RuntimeError, match="Lock is not acquired"):
            lock.release()

    asyncio.run(scenario())

def test_event_set_wakes_all_and_stays_set_until_clear():
    async def scenario():
        event = asyncio.Event()
        entered = [asyncio.Event(), asyncio.Event()]

        async def waiter(index):
            entered[index].set()
            return await event.wait()

        tasks = [asyncio.create_task(waiter(index)) for index in range(2)]
        await asyncio.gather(*(marker.wait() for marker in entered))
        assert event.is_set() is False

        event.set()
        assert await asyncio.gather(*tasks) == [True, True]
        assert await event.wait() is True
        event.clear()
        assert event.is_set() is False

        pending = asyncio.create_task(event.wait())
        done, _ = await asyncio.wait({pending}, timeout=0)
        assert done == set()
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)

    asyncio.run(scenario())


def test_sync_primitive_methods_reject_direct_timeout_keyword():
    async def scenario():
        lock = asyncio.Lock()
        event = asyncio.Event()

        with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
            lock.acquire(timeout=1)
        with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
            event.wait(timeout=1)

    asyncio.run(scenario())
