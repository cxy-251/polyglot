"""287｜asyncio Queue/LifoQueue/PriorityQueue、精确 size 与 bounded backpressure。

asyncio Queue 仅服务同一 event loop，因此 qsize 是精确值；bounded put 在满时 suspend，get
释放一个 slot。get/put 自身没有 timeout 参数，应用应以 wait_for 包装。nowait 版本用
QueueEmpty/QueueFull 表达不能立即完成，三种 Queue 仅改变 retrieval order。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Queue
# polyglot-covers: python.asyncio.Queue.maxsize
# polyglot-covers: python.asyncio.Queue.qsize
# polyglot-covers: python.asyncio.Queue.empty
# polyglot-covers: python.asyncio.Queue.full
# polyglot-covers: python.asyncio.Queue.put
# polyglot-covers: python.asyncio.Queue.put_nowait
# polyglot-covers: python.asyncio.Queue.get
# polyglot-covers: python.asyncio.Queue.get_nowait
# polyglot-covers: python.asyncio.QueueFull
# polyglot-covers: python.asyncio.QueueEmpty
# polyglot-covers: python.asyncio.Queue-bounded-backpressure
# polyglot-covers: python.asyncio.Queue-exact-size
# polyglot-covers: python.asyncio.Queue-no-timeout-parameter
# polyglot-covers: python.asyncio.Queue-wait-for-timeout
# polyglot-covers: python.asyncio.PriorityQueue
# polyglot-covers: python.asyncio.LifoQueue

import asyncio

import pytest


async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_queue_variants_retrieve_fifo_lifo_and_lowest_priority_first():
    async def scenario():
        fifo = asyncio.Queue()
        lifo = asyncio.LifoQueue()
        priority = asyncio.PriorityQueue()
        for container in (fifo, lifo):
            container.put_nowait("first")
            await container.put("second")
        priority.put_nowait((20, "later"))
        await priority.put((10, "earlier"))

        assert [fifo.get_nowait(), fifo.get_nowait()] == ["first", "second"]
        assert [lifo.get_nowait(), lifo.get_nowait()] == ["second", "first"]
        assert [priority.get_nowait(), priority.get_nowait()] == [
            (10, "earlier"),
            (20, "later"),
        ]

    asyncio.run(scenario())

def test_bounded_put_suspends_until_get_releases_capacity():
    async def scenario():
        work = asyncio.Queue(maxsize=1)
        assert work.maxsize == 1
        await work.put("first")
        assert work.qsize() == 1
        assert work.full() is True

        blocked_put = asyncio.create_task(work.put("second"))
        await _next_loop_turn()
        assert blocked_put.done() is False
        with pytest.raises(asyncio.QueueFull):
            work.put_nowait("third")

        assert await work.get() == "first"
        await blocked_put
        assert work.qsize() == 1
        assert work.get_nowait() == "second"
        assert work.empty() is True
        with pytest.raises(asyncio.QueueEmpty):
            work.get_nowait()

    asyncio.run(scenario())


def test_queue_timeout_is_composed_with_wait_for_not_a_method_keyword():
    async def scenario():
        work = asyncio.Queue()
        with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
            work.get(timeout=1)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(work.get(), timeout=0)

        work.put_nowait("still usable")
        assert await work.get() == "still usable"

    asyncio.run(scenario())
