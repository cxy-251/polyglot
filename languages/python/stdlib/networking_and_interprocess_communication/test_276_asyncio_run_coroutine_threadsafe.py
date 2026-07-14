"""276｜从其他 OS thread 使用 ``run_coroutine_threadsafe``。

此函数要求显式 loop，并返回 thread-safe ``concurrent.futures.Future``，供非 event-loop
线程同步取得结果、异常或发出取消。asyncio Task/Future 本身通常不是 thread-safe；跨线程
callback 应使用 loop.call_soon_threadsafe，不能直接操作 loop 内对象。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.run_coroutine_threadsafe
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-explicit-loop
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-concurrent-future
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-result
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-exception
# polyglot-covers: python.asyncio.run-coroutine-threadsafe-cancel
# polyglot-covers: python.asyncio.loop.call_soon_threadsafe
# polyglot-covers: python.asyncio.cross-thread-task-safety-boundary

import asyncio
import concurrent.futures
from contextlib import contextmanager
import threading

import pytest


@contextmanager
def _event_loop_in_worker_thread():
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    failures = []

    def run_loop():
        asyncio.set_event_loop(loop)
        ready.set()
        try:
            loop.run_forever()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        except BaseException as error:
            failures.append(error)
        finally:
            loop.close()

    thread = threading.Thread(target=run_loop, name="asyncio-loop-thread")
    thread.start()
    assert ready.wait(timeout=2)
    try:
        yield loop, thread.ident
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        assert thread.is_alive() is False
        if failures:
            raise failures[0]


def test_threadsafe_submission_returns_concurrent_future_result_and_exception():
    async def describe(value):
        return value * 2, threading.get_ident()

    async def fail():
        raise LookupError("async failure")

    with _event_loop_in_worker_thread() as (loop, loop_thread_ident):
        result_future = asyncio.run_coroutine_threadsafe(describe(21), loop)
        assert isinstance(result_future, concurrent.futures.Future)
        assert result_future.result(timeout=2) == (42, loop_thread_ident)

        failed_future = asyncio.run_coroutine_threadsafe(fail(), loop)
        with pytest.raises(LookupError, match="async failure"):
            failed_future.result(timeout=2)


def test_cancelling_returned_future_requests_task_cancellation_in_loop_thread():
    started = threading.Event()
    cleaned = threading.Event()

    async def pending():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    with _event_loop_in_worker_thread() as (loop, _):
        future = asyncio.run_coroutine_threadsafe(pending(), loop)
        assert started.wait(timeout=2)
        assert future.cancel() is True
        with pytest.raises(concurrent.futures.CancelledError):
            future.result(timeout=2)
        assert cleaned.wait(timeout=2)
