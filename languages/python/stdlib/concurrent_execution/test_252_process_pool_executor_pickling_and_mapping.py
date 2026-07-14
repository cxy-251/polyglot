"""252｜``ProcessPoolExecutor`` mp_context、pickling boundary、map 与 remote exception。

ProcessPool 绕过 GIL，但 callable/arguments/results 必须 pickle，且 main module 必须能
import。``mp_context`` 让 library 不强改 global start method。map 保持 input order，并用
chunksize 降低长 iterable 的 IPC overhead。普通 task exception 不会弄坏整个 pool。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.concurrent.futures.ProcessPoolExecutor
# polyglot-covers: python.concurrent.futures.ProcessPoolExecutor-max_workers
# polyglot-covers: python.concurrent.futures.process-mp-context
# polyglot-covers: python.concurrent.futures.ProcessPoolExecutor-initializer
# polyglot-covers: python.concurrent.futures.ProcessPoolExecutor-initargs
# polyglot-covers: python.concurrent.futures.process-picklable-callable
# polyglot-covers: python.concurrent.futures.process-picklable-arguments-results
# polyglot-covers: python.concurrent.futures.process-main-importability
# polyglot-covers: python.concurrent.futures.process-map-chunksize
# polyglot-covers: python.concurrent.futures.process-map-input-order
# polyglot-covers: python.concurrent.futures.process-remote-exception
# polyglot-covers: python.concurrent.futures.process-pickling-error-not-broken

import concurrent.futures
import multiprocessing
import os
import pickle

import pytest


_PROCESS_WORKER_LABEL = None


def _initialize_process_worker(label):
    global _PROCESS_WORKER_LABEL
    _PROCESS_WORKER_LABEL = label


def _describe_process_task(value):
    return _PROCESS_WORKER_LABEL, value * value, os.getpid()


def _raise_process_task_error(message):
    raise LookupError(message)


def test_process_executor_uses_selected_context_initializer_and_mapping():
    """结果 pid 与 parent 不同；map 即使 worker 完成顺序不同也按 input 排列。"""

    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=2,
        mp_context=context,
        initializer=_initialize_process_worker,
        initargs=("spawn-ready",),
    ) as executor:
        first = executor.submit(_describe_process_task, 6).result(timeout=5)
        mapped = list(
            executor.map(
                _describe_process_task,
                [3, 1, 2],
                chunksize=2,
            )
        )

    assert first[:2] == ("spawn-ready", 36)
    assert first[2] != os.getpid()
    assert [(label, result) for label, result, _ in mapped] == [
        ("spawn-ready", 9),
        ("spawn-ready", 1),
        ("spawn-ready", 4),
    ]
    assert all(pid != os.getpid() for _, _, pid in mapped)


def test_remote_task_exception_is_reconstructed_but_executor_remains_usable():
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=1,
        mp_context=context,
    ) as executor:
        failed = executor.submit(_raise_process_task_error, "remote missing")

        assert isinstance(failed.exception(timeout=5), LookupError)
        with pytest.raises(LookupError, match="remote missing") as raised:
            failed.result()
        assert raised.value.__cause__.__class__.__name__ == "_RemoteTraceback"

        assert executor.submit(pow, 2, 8).result(timeout=5) == 256


def test_unpicklable_lambda_fails_its_future_without_breaking_process_pool():
    """submit 本身先返回 Future；queue feeder serialization error 在 result 边界出现。"""

    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=1,
        mp_context=context,
    ) as executor:
        unpicklable = executor.submit(lambda: 42)

        with pytest.raises((AttributeError, pickle.PicklingError)):
            unpicklable.result(timeout=5)
        assert executor.submit(pow, 3, 3).result(timeout=5) == 27


def test_invalid_process_worker_count_is_rejected():
    with pytest.raises(ValueError, match="max_workers must be greater than 0"):
        concurrent.futures.ProcessPoolExecutor(max_workers=0)
