"""271｜Task cancellation request、传播、清理与 suppression。

Task.cancel 不是立即终止：它在下一次 loop cycle 向 coroutine 注入 CancelledError，因此
finally 能清理资源，coroutine 甚至可以抑制请求。CancelledError 自 3.8 起直接继承
BaseException，宽泛的 ``except Exception`` 不会误吞取消；通常捕获后必须重新抛出。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Task.cancel
# polyglot-covers: python.asyncio.Task-cancel-message
# polyglot-covers: python.asyncio.Task.cancelled
# polyglot-covers: python.asyncio.Task-cancellation-injection
# polyglot-covers: python.asyncio.Task-cancellation-finally-cleanup
# polyglot-covers: python.asyncio.Task-cancellation-suppression
# polyglot-covers: python.asyncio.Task-cancel-awaited-future
# polyglot-covers: python.asyncio.CancelledError
# polyglot-covers: python.asyncio.CancelledError-BaseException
# polyglot-covers: python.asyncio.cancelled-task-result-exception

import asyncio

import pytest


def test_cancel_injects_message_runs_finally_and_marks_task_cancelled():
    async def scenario():
        started = asyncio.Event()
        blocker = asyncio.Event()
        cleanup = []

        async def worker():
            started.set()
            try:
                await blocker.wait()
            finally:
                cleanup.append("released")

        task = asyncio.create_task(worker())
        await started.wait()
        assert task.cancel("stop requested") is True

        with pytest.raises(asyncio.CancelledError) as raised:
            await task
        assert raised.value.args == ("stop requested",)
        assert cleanup == ["released"]
        assert task.done() is True
        assert task.cancelled() is True
        with pytest.raises(asyncio.CancelledError):
            task.result()
        with pytest.raises(asyncio.CancelledError):
            task.exception()

    asyncio.run(scenario())


def test_coroutine_can_suppress_cancellation_but_normally_should_not():
    async def scenario():
        started = asyncio.Event()
        blocker = asyncio.Event()

        async def worker():
            started.set()
            try:
                await blocker.wait()
            except asyncio.CancelledError:
                return "suppressed"

        task = asyncio.create_task(worker())
        await started.wait()
        task.cancel()

        assert await task == "suppressed"
        assert task.cancelled() is False
        assert task.result() == "suppressed"

    asyncio.run(scenario())


def test_cancelling_task_also_cancels_future_it_is_currently_awaiting():
    async def scenario():
        loop = asyncio.get_running_loop()
        awaited = loop.create_future()
        entered = asyncio.Event()

        async def worker():
            entered.set()
            await awaited

        task = asyncio.create_task(worker())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert awaited.cancelled() is True

    asyncio.run(scenario())


def test_cancelled_error_is_not_caught_by_exception_handlers():
    assert issubclass(asyncio.CancelledError, BaseException)
    assert issubclass(asyncio.CancelledError, Exception) is False
