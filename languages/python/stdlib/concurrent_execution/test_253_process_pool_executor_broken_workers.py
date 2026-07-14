"""253｜ProcessPool initializer failure、abrupt worker exit 与 BrokenProcessPool。

普通 callable exception 只使一个 Future 失败；initializer 失败或 worker 非正常消失时，
executor 无法确定 pool invariant，pending/subsequent work 改抛 BrokenProcessPool。
worker 内调用本 Executor/Future method 也会 deadlock，不能传入 parent executor 依赖。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.concurrent.futures.process.BrokenProcessPool
# polyglot-covers: python.concurrent.futures.process-initializer-failure
# polyglot-covers: python.concurrent.futures.process-abrupt-worker-exit
# polyglot-covers: python.concurrent.futures.process-broken-pending-futures
# polyglot-covers: python.concurrent.futures.process-broken-submit
# polyglot-covers: python.concurrent.futures.process-task-executor-method-deadlock
# polyglot-covers: python.concurrent.futures.BrokenProcessPool-BrokenExecutor-subclass

import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import multiprocessing
import os

import pytest


def _fail_process_initializer():
    raise RuntimeError("initializer failed")


def _exit_worker_abruptly():
    os._exit(17)


def test_initializer_failure_breaks_first_future_and_subsequent_submit():
    context = multiprocessing.get_context("spawn")
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=1,
        mp_context=context,
        initializer=_fail_process_initializer,
    )
    pending = executor.submit(pow, 2, 3)

    try:
        with pytest.raises(BrokenProcessPool):
            pending.result(timeout=5)
        with pytest.raises(BrokenProcessPool):
            executor.submit(pow, 2, 4)
    finally:
        executor.shutdown()


def test_abrupt_worker_exit_marks_pool_broken_instead_of_hanging():
    """os._exit 仅发生在 disposable worker；parent pytest process 不受影响。"""

    context = multiprocessing.get_context("spawn")
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=1,
        mp_context=context,
    )
    crashed = executor.submit(_exit_worker_abruptly)

    try:
        with pytest.raises(BrokenProcessPool):
            crashed.result(timeout=5)
        with pytest.raises(BrokenProcessPool):
            executor.submit(pow, 2, 5)
        assert issubclass(BrokenProcessPool, concurrent.futures.BrokenExecutor)
    finally:
        executor.shutdown()
