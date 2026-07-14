"""292｜``isfuture/ensure_future/wrap_future`` 的 awaitable dispatch 与线程桥。

ensure_future 对 asyncio Future/Task 保持 identity，对 coroutine 或一般 awaitable 创建 Task，
无效对象抛 TypeError。wrap_future 把 concurrent.futures.Future 的 thread-safe completion
转换成 loop-bound asyncio Future；两套 Future 的 wait/result timeout protocol 不能混用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.isfuture
# polyglot-covers: python.asyncio.isfuture-future-like-marker
# polyglot-covers: python.asyncio.ensure_future
# polyglot-covers: python.asyncio.ensure-future-preserves-future-identity
# polyglot-covers: python.asyncio.ensure-future-coroutine-to-task
# polyglot-covers: python.asyncio.ensure-future-custom-awaitable
# polyglot-covers: python.asyncio.ensure-future-invalid-type
# polyglot-covers: python.asyncio.wrap_future
# polyglot-covers: python.asyncio.wrap-concurrent-future-result
# polyglot-covers: python.asyncio.wrap-future-cancellation-propagation
# polyglot-covers: python.asyncio.future-families-timeout-protocol-difference

import asyncio
import concurrent.futures

import pytest


class CustomAwaitable:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        async def resolve():
            return self.value

        return resolve().__await__()


class FutureLikeMarker:
    _asyncio_future_blocking = False


def test_ensure_future_dispatches_existing_future_coroutine_and_custom_awaitable():
    async def scenario():
        loop = asyncio.get_running_loop()
        existing = loop.create_future()
        existing.set_result("existing")
        assert asyncio.ensure_future(existing) is existing

        async def coroutine():
            return "coroutine"

        task = asyncio.ensure_future(coroutine())
        custom_task = asyncio.ensure_future(CustomAwaitable("custom"))
        assert isinstance(task, asyncio.Task)
        assert isinstance(custom_task, asyncio.Task)
        assert await asyncio.gather(task, custom_task) == ["coroutine", "custom"]

        with pytest.raises(TypeError, match="An asyncio.Future, a coroutine or an awaitable"):
            asyncio.ensure_future(42)

    asyncio.run(scenario())

def test_isfuture_accepts_documented_future_like_marker_protocol():
    assert asyncio.isfuture(FutureLikeMarker()) is True
    assert asyncio.isfuture(object()) is False


def test_wrap_future_bridges_result_and_cancellation_into_running_loop():
    async def scenario():
        concurrent_result = concurrent.futures.Future()
        wrapped_result = asyncio.wrap_future(concurrent_result)
        concurrent_result.set_result(42)
        assert await wrapped_result == 42

        concurrent_pending = concurrent.futures.Future()
        wrapped_pending = asyncio.wrap_future(concurrent_pending)
        assert wrapped_pending.cancel("stop") is True

        turn = asyncio.get_running_loop().create_future()
        asyncio.get_running_loop().call_soon(turn.set_result, None)
        await turn
        assert concurrent_pending.cancelled() is True
        with pytest.raises(asyncio.CancelledError):
            await wrapped_pending

    asyncio.run(scenario())


def test_asyncio_future_result_does_not_accept_concurrent_timeout_argument():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        with pytest.raises(TypeError, match="takes no keyword arguments"):
            future.result(timeout=1)
        future.cancel()

    asyncio.run(scenario())
