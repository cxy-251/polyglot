"""取消、超时与清理。

共同问题：取消是否会强制停止工作；超时如何报告；被取消路径是否仍执行清理；
取消由运行时、协作协议还是所有权机制触发。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: cancellation_timeouts_and_cleanup
# polyglot-related: languages/python/language/test_015_async_functions_and_protocols.py

import asyncio

import pytest


def test_task_cancellation_is_delivered_at_an_await_and_runs_finally():
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
        assert task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return events

    assert asyncio.run(scenario()) == ["started", "cleanup"]


def test_wait_for_reports_timeout_without_waiting_for_wall_time():
    async def scenario():
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.Event().wait(), timeout=0)

    asyncio.run(scenario())


def test_completed_task_cannot_be_retroactively_cancelled():
    async def scenario():
        task = asyncio.create_task(asyncio.sleep(0, result=42))
        assert await task == 42
        assert task.cancel() is False
        return task.cancelled()

    assert asyncio.run(scenario()) is False


def test_cancelled_error_is_a_control_flow_base_exception():
    assert issubclass(asyncio.CancelledError, BaseException)
    assert not issubclass(asyncio.CancelledError, Exception)

    # Python 3.10 中宽泛的 except Exception 不会吞掉任务取消，清理应放在 finally 中。
