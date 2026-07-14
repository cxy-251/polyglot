"""250｜``ThreadPoolExecutor`` submit/map、initializer、thread naming 与 idle reuse。

ThreadPool 共享 object graph，不要求 pickle；适合 I/O overlap，但 CPython bytecode 仍受
GIL。Executor.map 会立即收集 input iterables，却按 input order 产出结果。worker task
等待同一小 pool 中另一 Future 容易 deadlock；应重构 dependency 或使用有界 timeout。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.concurrent.futures.Executor
# polyglot-covers: python.concurrent.futures.Executor.submit
# polyglot-covers: python.concurrent.futures.Executor.map
# polyglot-covers: python.concurrent.futures.Executor-map-eager-input
# polyglot-covers: python.concurrent.futures.Executor-map-ordered-results
# polyglot-covers: python.concurrent.futures.Executor-context-manager
# polyglot-covers: python.concurrent.futures.ThreadPoolExecutor
# polyglot-covers: python.concurrent.futures.ThreadPoolExecutor-max_workers
# polyglot-covers: python.concurrent.futures.thread-name-prefix
# polyglot-covers: python.concurrent.futures.ThreadPoolExecutor-initializer
# polyglot-covers: python.concurrent.futures.ThreadPoolExecutor-initargs
# polyglot-covers: python.concurrent.futures.ThreadPoolExecutor-idle-reuse
# polyglot-covers: python.concurrent.futures.thread-shared-object-graph
# polyglot-covers: python.concurrent.futures.thread-pool-future-dependency-deadlock

import concurrent.futures
import threading

import pytest


_THREAD_WORKER_STATE = threading.local()


def _initialize_thread_worker(label):
    _THREAD_WORKER_STATE.label = label


def _describe_thread_task(value, *, multiplier=1):
    return {
        "result": value * multiplier,
        "label": _THREAD_WORKER_STATE.label,
        "name": threading.current_thread().name,
        "ident": threading.get_ident(),
    }


def test_submit_passes_arguments_and_initializer_configures_named_worker():
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="polyglot-worker",
        initializer=_initialize_thread_worker,
        initargs=("ready",),
    )
    try:
        first = executor.submit(_describe_thread_task, 6, multiplier=7).result(timeout=2)
        second = executor.submit(_describe_thread_task, 3, multiplier=5).result(timeout=2)

        assert first["result"] == 42
        assert first["label"] == second["label"] == "ready"
        assert first["name"].startswith("polyglot-worker")
        assert first["ident"] == second["ident"]
    finally:
        executor.shutdown()


def test_map_eagerly_collects_generator_but_yields_in_input_order():
    """worker 被 Event gate 挡住，仍不妨碍 map 返回 iterator 前耗尽 generator。"""

    gate = threading.Event()
    visited = []

    def inputs():
        for value in [3, 1, 2]:
            visited.append(value)
            yield value

    def gated_square(value):
        assert gate.wait(timeout=2)
        return value * value

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        results = executor.map(gated_square, inputs())
        assert visited == [3, 1, 2]
        gate.set()
        assert list(results) == [9, 1, 4]


def test_thread_pool_shares_non_picklable_closure_and_survives_task_error():
    """closure/list 可共享；task exception 保存在 Future，不会自动破坏 pool。"""

    values = []

    def append_and_count(value):
        values.append(value)
        return len(values)

    def fail():
        raise LookupError("task failed")

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        assert executor.submit(append_and_count, "item").result() == 1
        failed = executor.submit(fail)
        with pytest.raises(LookupError, match="task failed"):
            failed.result()
        assert executor.submit(append_and_count, "next").result() == 2

    assert values == ["item", "next"]


def test_invalid_worker_count_and_submit_after_context_shutdown_fail():
    with pytest.raises(ValueError, match="max_workers must be greater than 0"):
        concurrent.futures.ThreadPoolExecutor(max_workers=0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        assert executor.submit(pow, 2, 5).result() == 32

    with pytest.raises(RuntimeError, match="cannot schedule new futures after shutdown"):
        executor.submit(pow, 2, 6)
