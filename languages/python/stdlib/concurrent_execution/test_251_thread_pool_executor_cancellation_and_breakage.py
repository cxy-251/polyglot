"""251｜ThreadPool cancellation、``shutdown(cancel_futures)`` 与 BrokenThreadPool。

Future cancel 只影响 queue 中尚未 running 的 work。3.9+ 的 shutdown(cancel_futures=True)
批量取消 pending work，但 running work 仍完成。initializer 异常会使 executor broken，
所有 pending Future 和后续 submit 都抛 BrokenThreadPool，不会换一个 thread 重试。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.concurrent.futures.Executor.shutdown
# polyglot-covers: python.concurrent.futures.Executor-shutdown-wait-false
# polyglot-covers: python.concurrent.futures.shutdown-cancel-futures
# polyglot-covers: python.concurrent.futures.running-future-not-cancelled
# polyglot-covers: python.concurrent.futures.pending-future-cancelled
# polyglot-covers: python.concurrent.futures.Future-timeout-deadlock-guard
# polyglot-covers: python.concurrent.futures.thread.BrokenThreadPool
# polyglot-covers: python.concurrent.futures.BrokenExecutor
# polyglot-covers: python.concurrent.futures.thread-initializer-failure

import concurrent.futures
from concurrent.futures.thread import BrokenThreadPool
import threading

import pytest


def _fail_thread_initializer():
    raise RuntimeError("initializer failed")


def test_shutdown_cancel_futures_cancels_pending_but_not_running_work():
    """单 worker 被 gate 占用，第二个 Future 确定还在 queue 中。"""

    gate = threading.Event()
    started = threading.Event()

    def running_task():
        started.set()
        assert gate.wait(timeout=2)
        return "running-finished"

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    running = executor.submit(running_task)
    assert started.wait(timeout=2)
    pending = executor.submit(lambda: "never-runs")

    executor.shutdown(wait=False, cancel_futures=True)

    assert running.running() is True
    assert pending.cancelled() is True
    gate.set()
    assert running.result(timeout=2) == "running-finished"
    with pytest.raises(concurrent.futures.CancelledError):
        pending.result()


def test_timeout_prevents_single_worker_nested_future_wait_from_deadlocking():
    """outer 不无限等待 inner；timeout 后归还唯一 worker，inner 才能执行。"""

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def outer():
        inner = executor.submit(pow, 5, 2)
        try:
            inner.result(timeout=0)
        except concurrent.futures.TimeoutError:
            return inner
        raise AssertionError("inner should still be queued")

    try:
        inner = executor.submit(outer).result(timeout=2)
        assert inner.result(timeout=2) == 25
    finally:
        executor.shutdown()


def test_initializer_failure_breaks_pending_and_future_submissions():
    """BrokenThreadPool 是 BrokenExecutor 子类；这不是可隔离的普通 task exception。"""

    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=1,
        initializer=_fail_thread_initializer,
    )
    pending = executor.submit(pow, 2, 3)

    try:
        with pytest.raises(BrokenThreadPool):
            pending.result(timeout=2)
        with pytest.raises(BrokenThreadPool):
            executor.submit(pow, 2, 4)
        assert issubclass(BrokenThreadPool, concurrent.futures.BrokenExecutor)
    finally:
        executor.shutdown()
