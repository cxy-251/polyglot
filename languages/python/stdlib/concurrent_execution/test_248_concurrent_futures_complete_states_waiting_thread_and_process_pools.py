"""248｜``concurrent.futures.Future`` pending/running/cancelled/finished state machine。

Executor 通常创建 Future；官方也允许 unit test/Executor implementation 直接构造。
cancel 只对尚未 running 的 work 成功。result/exception 根据 terminal state 返回或重抛；
callback 按注册顺序执行，若注册时已完成则在 add_done_callback 调用内立即执行。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.concurrent.futures.Future
# polyglot-covers: python.concurrent.futures.Future.cancel
# polyglot-covers: python.concurrent.futures.Future.cancelled
# polyglot-covers: python.concurrent.futures.Future.running
# polyglot-covers: python.concurrent.futures.Future.done
# polyglot-covers: python.concurrent.futures.Future.result
# polyglot-covers: python.concurrent.futures.Future.exception
# polyglot-covers: python.concurrent.futures.Future.add_done_callback
# polyglot-covers: python.concurrent.futures.Future-callback-order
# polyglot-covers: python.concurrent.futures.Future-completed-callback-immediate
# polyglot-covers: python.concurrent.futures.Future.set_running_or_notify_cancel
# polyglot-covers: python.concurrent.futures.Future.set_result
# polyglot-covers: python.concurrent.futures.Future.set_exception
# polyglot-covers: python.concurrent.futures.CancelledError
# polyglot-covers: python.concurrent.futures.InvalidStateError




import concurrent.futures
import pytest
import threading
from concurrent.futures.thread import BrokenThreadPool
import multiprocessing
import os
import pickle
from concurrent.futures.process import BrokenProcessPool

def test_pending_future_can_be_cancelled_and_wakes_callbacks():
    """cancelled 也属于 done；result/exception 都用 CancelledError 表示没有 outcome。"""

    future = concurrent.futures.Future()
    callbacks = []
    future.add_done_callback(lambda completed: callbacks.append(completed.cancelled()))

    assert future.running() is False
    assert future.done() is False
    assert future.cancel() is True

    assert future.cancelled() is True
    assert future.done() is True
    assert future.cancel() is True
    assert callbacks == [True]
    with pytest.raises(concurrent.futures.CancelledError):
        future.result()
    with pytest.raises(concurrent.futures.CancelledError):
        future.exception()


def test_executor_transition_refuses_cancel_once_future_is_running():
    """set_running_or_notify_cancel 是 Executor 开工前的原子关口。"""

    future = concurrent.futures.Future()

    assert future.set_running_or_notify_cancel() is True
    assert future.running() is True
    assert future.cancel() is False

    future.set_result(42)

    assert future.running() is False
    assert future.done() is True
    assert future.cancelled() is False
    assert future.result() == 42
    assert future.exception() is None


def test_cancelled_future_tells_executor_not_to_run_callable():
    """cancel 先赢得 state transition 后，Executor gate 返回 False。"""

    future = concurrent.futures.Future()
    future.cancel()

    assert future.set_running_or_notify_cancel() is False
    assert future.cancelled() is True


def test_set_exception_is_observable_and_result_reraises_same_object():
    """exception() 返回 exception instance；result() 以该 instance 失败。"""

    future = concurrent.futures.Future()
    error = LookupError("missing")
    future.set_exception(error)

    assert future.exception() is error
    with pytest.raises(LookupError, match="missing") as raised:
        future.result()
    assert raised.value is error


def test_terminal_result_is_single_assignment_and_callbacks_preserve_order():
    """完成后 callback 立即执行；第二次 set result/exception 是 InvalidStateError。"""

    future = concurrent.futures.Future()
    calls = []
    future.add_done_callback(lambda completed: calls.append(("first", completed.result())))
    future.add_done_callback(lambda completed: calls.append(("second", completed.result())))

    future.set_result("ready")
    future.add_done_callback(lambda completed: calls.append(("late", completed.result())))

    assert calls == [
        ("first", "ready"),
        ("second", "ready"),
        ("late", "ready"),
    ]
    with pytest.raises(concurrent.futures.InvalidStateError):
        future.set_result("again")
    with pytest.raises(concurrent.futures.InvalidStateError):
        future.set_exception(RuntimeError("too late"))


# 249｜``wait`` completion policies、duplicate elimination 与 ``as_completed`` timeout。
#
# wait 接受来自不同 Executor 的 Futures，去重后返回 ``done/not_done`` sets。
# FIRST_EXCEPTION 只在 exception terminal state 出现时提前返回；as_completed 按完成顺序
# yield，每个重复 Future 只 yield 一次。timeout 从创建 iterator 的原始调用时刻计算。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.concurrent.futures.wait
# polyglot-covers: python.concurrent.futures.wait-duplicate-elimination
# polyglot-covers: python.concurrent.futures.DoneAndNotDoneFutures
# polyglot-covers: python.concurrent.futures.FIRST_COMPLETED
# polyglot-covers: python.concurrent.futures.FIRST_EXCEPTION
# polyglot-covers: python.concurrent.futures.ALL_COMPLETED
# polyglot-covers: python.concurrent.futures.as_completed
# polyglot-covers: python.concurrent.futures.as-completed-duplicate-elimination
# polyglot-covers: python.concurrent.futures.as-completed-already-done-first
# polyglot-covers: python.concurrent.futures.as-completed-timeout
# polyglot-covers: python.concurrent.futures.TimeoutError




def test_wait_deduplicates_and_partitions_done_from_pending():
    """timeout=0 是状态快照；named tuple fields 同时支持属性和 tuple unpack。"""

    finished = concurrent.futures.Future()
    pending = concurrent.futures.Future()
    finished.set_result("done")

    result = concurrent.futures.wait(
        [finished, finished, pending],
        timeout=0,
        return_when=concurrent.futures.ALL_COMPLETED,
    )
    done, not_done = result

    assert result.done == done == {finished}
    assert result.not_done == not_done == {pending}


def test_first_completed_and_first_exception_policies_use_terminal_states():
    """调用前完成的普通 future 计入 done；exception future 触发 FIRST_EXCEPTION。"""

    successful = concurrent.futures.Future()
    failed = concurrent.futures.Future()
    pending = concurrent.futures.Future()
    successful.set_result(1)

    completed = concurrent.futures.wait(
        [successful, pending],
        timeout=0,
        return_when=concurrent.futures.FIRST_COMPLETED,
    )
    assert completed.done == {successful}
    assert completed.not_done == {pending}

    failed.set_exception(ValueError("failed"))
    exceptional = concurrent.futures.wait(
        [successful, failed, pending],
        timeout=0,
        return_when=concurrent.futures.FIRST_EXCEPTION,
    )
    assert exceptional.done == {successful, failed}
    assert exceptional.not_done == {pending}


def test_as_completed_yields_done_once_then_times_out_for_pending():
    """finished 在 iterator 创建前已完成，因此第一个 next 立即得到它。"""

    finished = concurrent.futures.Future()
    pending = concurrent.futures.Future()
    finished.set_result(42)

    completed = concurrent.futures.as_completed(
        [finished, finished, pending],
        timeout=0,
    )

    assert next(completed) is finished
    with pytest.raises(concurrent.futures.TimeoutError):
        next(completed)


def test_as_completed_yields_each_future_once_when_all_are_done():
    first = concurrent.futures.Future()
    second = concurrent.futures.Future()
    first.set_result("first")
    second.set_result("second")

    yielded = list(concurrent.futures.as_completed([first, second, first]))

    assert set(yielded) == {first, second}
    assert len(yielded) == 2


# 250｜``ThreadPoolExecutor`` submit/map、initializer、thread naming 与 idle reuse。
#
# ThreadPool 共享 object graph，不要求 pickle；适合 I/O overlap，但 CPython bytecode 仍受
# GIL。Executor.map 会立即收集 input iterables，却按 input order 产出结果。worker task
# 等待同一小 pool 中另一 Future 容易 deadlock；应重构 dependency 或使用有界 timeout。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# 251｜ThreadPool cancellation、``shutdown(cancel_futures)`` 与 BrokenThreadPool。
#
# Future cancel 只影响 queue 中尚未 running 的 work。3.9+ 的 shutdown(cancel_futures=True)
# 批量取消 pending work，但 running work 仍完成。initializer 异常会使 executor broken，
# 所有 pending Future 和后续 submit 都抛 BrokenThreadPool，不会换一个 thread 重试。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.concurrent.futures.Executor.shutdown
# polyglot-covers: python.concurrent.futures.Executor-shutdown-wait-false
# polyglot-covers: python.concurrent.futures.shutdown-cancel-futures
# polyglot-covers: python.concurrent.futures.running-future-not-cancelled
# polyglot-covers: python.concurrent.futures.pending-future-cancelled
# polyglot-covers: python.concurrent.futures.Future-timeout-deadlock-guard
# polyglot-covers: python.concurrent.futures.thread.BrokenThreadPool
# polyglot-covers: python.concurrent.futures.BrokenExecutor
# polyglot-covers: python.concurrent.futures.thread-initializer-failure




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


# 252｜``ProcessPoolExecutor`` mp_context、pickling boundary、map 与 remote exception。
#
# ProcessPool 绕过 GIL，但 callable/arguments/results 必须 pickle，且 main module 必须能
# import。``mp_context`` 让 library 不强改 global start method。map 保持 input order，并用
# chunksize 降低长 iterable 的 IPC overhead。普通 task exception 不会弄坏整个 pool。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# 253｜ProcessPool initializer failure、abrupt worker exit 与 BrokenProcessPool。
#
# 普通 callable exception 只使一个 Future 失败；initializer 失败或 worker 非正常消失时，
# executor 无法确定 pool invariant，pending/subsequent work 改抛 BrokenProcessPool。
# worker 内调用本 Executor/Future method 也会 deadlock，不能传入 parent executor 依赖。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.concurrent.futures.process.BrokenProcessPool
# polyglot-covers: python.concurrent.futures.process-initializer-failure
# polyglot-covers: python.concurrent.futures.process-abrupt-worker-exit
# polyglot-covers: python.concurrent.futures.process-broken-pending-futures
# polyglot-covers: python.concurrent.futures.process-broken-submit
# polyglot-covers: python.concurrent.futures.process-task-executor-method-deadlock
# polyglot-covers: python.concurrent.futures.BrokenProcessPool-BrokenExecutor-subclass




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
