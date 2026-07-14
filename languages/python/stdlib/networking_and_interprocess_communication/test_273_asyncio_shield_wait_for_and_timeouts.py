"""273｜``shield`` 与 ``wait_for`` 的 cancellation ownership。

wait_for 超时会取消 underlying Task，并等待取消真正完成后才抛 TimeoutError。shield 只阻断
调用者取消向 inner 传播：outer 仍收到 CancelledError，inner 可继续；inner 若被直接取消，
shield 也会失败。两者组合可让 timeout 结束等待但保留后台 Task，调用者必须保存并回收它。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.shield
# polyglot-covers: python.asyncio.shield-outer-cancel-inner-survives
# polyglot-covers: python.asyncio.shield-direct-inner-cancel
# polyglot-covers: python.asyncio.wait_for
# polyglot-covers: python.asyncio.wait-for-timeout
# polyglot-covers: python.asyncio.wait-for-cancels-underlying
# polyglot-covers: python.asyncio.wait-for-awaits-cancellation-cleanup
# polyglot-covers: python.asyncio.wait-for-timeout-none
# polyglot-covers: python.asyncio.wait-for-shield-preserves-task
# polyglot-covers: python.asyncio.TimeoutError

import asyncio

import pytest


def test_wait_for_timeout_cancels_task_and_waits_for_finally_cleanup():
    async def scenario():
        started = asyncio.Event()
        blocker = asyncio.Event()
        cleanup = []

        async def worker():
            started.set()
            try:
                await blocker.wait()
            finally:
                cleanup.append("finished")

        task = asyncio.create_task(worker())
        await started.wait()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=0)

        assert task.cancelled() is True
        assert cleanup == ["finished"]

    asyncio.run(scenario())

def test_wait_for_none_waits_normally_without_installing_a_deadline():
    async def result():
        return 42

    assert asyncio.run(asyncio.wait_for(result(), timeout=None)) == 42


def test_cancelling_outer_shield_wait_does_not_cancel_inner_task():
    async def scenario():
        started = asyncio.Event()
        release = asyncio.Event()

        async def inner_work():
            started.set()
            await release.wait()
            return "inner result"

        inner = asyncio.create_task(inner_work())

        async def outer_work():
            return await asyncio.shield(inner)

        outer = asyncio.create_task(outer_work())
        await started.wait()
        outer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await outer

        assert inner.cancelled() is False
        release.set()
        assert await inner == "inner result"

    asyncio.run(scenario())


def test_wait_for_shield_times_out_without_abandoning_inner_task():
    async def scenario():
        started = asyncio.Event()
        release = asyncio.Event()

        async def worker():
            started.set()
            await release.wait()
            return "kept"

        task = asyncio.create_task(worker())
        await started.wait()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), timeout=0)

        assert task.cancelled() is False
        release.set()
        assert await task == "kept"

    asyncio.run(scenario())


def test_directly_cancelled_inner_also_cancels_shield_awaitable():
    async def scenario():
        inner = asyncio.create_task(asyncio.Event().wait())
        protected = asyncio.shield(inner)
        inner.cancel()

        with pytest.raises(asyncio.CancelledError):
            await protected
        assert inner.cancelled() is True

    asyncio.run(scenario())
