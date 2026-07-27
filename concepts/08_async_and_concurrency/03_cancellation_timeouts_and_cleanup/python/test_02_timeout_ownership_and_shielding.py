"""超时所有权、底层取消与屏蔽。

共同问题：等待超时是否取消底层工作；取消完成前是否等待清理；
调用方能否只取消当前等待而保留共享任务。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/python/stdlib/095-103_networking_and_interprocess_communication/
# polyglot-related+: test_095_asyncio_coroutines_tasks_futures_threads_and_errors.py

import asyncio

import pytest


def test_wait_for_cancels_task_and_waits_until_finally_completes():
    async def scenario():
        events = []

        async def work():
            try:
                events.append("started")
                await asyncio.Future()
            finally:
                events.append("cleanup")

        task = asyncio.create_task(work())
        await asyncio.sleep(0)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(task, timeout=0)

        return events, task.cancelled()

    assert asyncio.run(scenario()) == (["started", "cleanup"], True)


def test_shield_times_out_the_waiter_without_cancelling_shared_task():
    async def scenario():
        release = asyncio.Event()

        async def work():
            await release.wait()
            return 42

        task = asyncio.create_task(work())
        await asyncio.sleep(0)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(task), timeout=0)

        assert not task.done()
        release.set()
        return await task

    assert asyncio.run(scenario()) == 42

    # shield 只隔离外层取消；任务仍需明确所有者最终等待、取消或收集异常。
