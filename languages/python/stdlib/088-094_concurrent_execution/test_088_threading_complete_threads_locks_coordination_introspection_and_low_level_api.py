"""088｜``threading.Thread`` lifecycle、target dispatch、identity 与 ``join``。

``run()`` 只是普通 method call；``start()`` 才会创建 OS thread，并且每个 Thread object
只能 start 一次。``join()`` 始终返回 None，判断 timeout 应再看 ``is_alive()``。Thread
异常不会由 join 重新抛给调用方，而是交给 ``threading.excepthook``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.threading.Thread python.threading.Thread-target
# polyglot-covers: python.threading.Thread-args python.threading.Thread-kwargs
# polyglot-covers: python.threading.Thread.start python.threading.Thread.run
# polyglot-covers: python.threading.Thread-start-once
# polyglot-covers: python.threading.Thread.join python.threading.Thread-join-returns-none
# polyglot-covers: python.threading.Thread-join-before-start-error
# polyglot-covers: python.threading.Thread-self-join-error
# polyglot-covers: python.threading.Thread.is_alive
# polyglot-covers: python.threading.Thread.name python.threading.Thread.daemon
# polyglot-covers: python.threading.Thread.ident python.threading.Thread.native_id
# polyglot-covers: python.threading.Thread-subclass-run




import queue
import threading
import pytest
import _thread
import os
import signal
import subprocess
import sys

def test_start_dispatches_target_in_another_thread_and_join_waits_for_exit():
    """ident/native_id 在 start 前为 None，结束后仍保留最后一次 thread identity。"""

    started = threading.Event()
    release = threading.Event()
    observations = {}

    def worker(value, *, scale):
        observations["result"] = value * scale
        observations["thread"] = threading.current_thread()
        observations["ident"] = threading.get_ident()
        started.set()
        assert release.wait(timeout=2)

    thread = threading.Thread(
        target=worker,
        args=(6,),
        kwargs={"scale": 7},
        name="answer-worker",
    )

    assert thread.ident is None
    assert thread.native_id is None
    assert thread.is_alive() is False
    assert thread.daemon is False

    thread.start()
    assert started.wait(timeout=2)
    assert thread.is_alive() is True
    assert observations["thread"] is thread
    assert observations["ident"] == thread.ident
    assert thread.name == "answer-worker"
    assert isinstance(thread.native_id, int)

    release.set()
    assert thread.join(timeout=2) is None
    assert thread.is_alive() is False
    assert thread.ident == observations["ident"]
    assert observations["result"] == 42


def test_calling_run_directly_is_synchronous_and_does_not_start_thread():
    """直接 run 可用于窄范围测试 target，但不会赋 ident，也不消耗一次 start 机会。"""

    calls = []
    thread = threading.Thread(target=calls.append, args=(threading.get_ident(),))

    thread.run()

    assert calls == [threading.get_ident()]
    assert thread.ident is None
    assert thread.is_alive() is False


def test_start_twice_and_join_before_start_are_lifecycle_errors():
    """Thread object 不可复用；需要再次运行应创建新 object。"""

    unstarted = threading.Thread(target=lambda: None)
    with pytest.raises(RuntimeError, match="cannot join thread before it is started"):
        unstarted.join()

    thread = threading.Thread(target=lambda: None)
    thread.start()
    thread.join()
    with pytest.raises(RuntimeError, match="threads can only be started once"):
        thread.start()


def test_thread_cannot_join_itself_because_that_would_deadlock():
    """错误发生在 worker 内；用 Queue 把异常类型和文本安全送回 main thread。"""

    outcomes = queue.Queue()

    def worker():
        try:
            threading.current_thread().join()
        except RuntimeError as error:
            outcomes.put((type(error), str(error)))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    error_type, message = outcomes.get_nowait()
    assert error_type is RuntimeError
    assert "cannot join current thread" in message


def test_subclass_overrides_run_and_calls_base_initializer_first():
    """官方扩展点是 __init__/run；不要覆盖 start/join 等 lifecycle machinery。"""

    class RecordingThread(threading.Thread):
        def __init__(self, value):
            super().__init__(name="recording-thread")
            self.value = value
            self.result = None

        def run(self):
            self.result = self.value.upper()

    thread = RecordingThread("python")
    thread.start()
    thread.join()

    assert thread.result == "PYTHON"


def test_daemon_flag_must_be_configured_before_start():
    """daemon thread 会在 process shutdown 被突然终止，不能承担必须清理的持久工作。"""

    release = threading.Event()
    started = threading.Event()

    def worker():
        started.set()
        assert release.wait(timeout=2)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    assert started.wait(timeout=2)

    try:
        with pytest.raises(RuntimeError, match="cannot set daemon status"):
            thread.daemon = False
    finally:
        release.set()
        thread.join()


# ``threading.local`` isolation、``__slots__`` trap 与 exception hooks。
#
# thread-local object 的 attribute dictionary 按 thread 隔离；subclass ``__init__`` 也会在
# 每个首次访问它的 thread 中分别执行。但 subclass slots 属于 class descriptor，不是
# thread-local storage。未捕获异常经 ``threading.excepthook`` 报告，不由 ``join`` 传播。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.threading.local python.threading.local-attribute-isolation
# polyglot-covers: python.threading.local-subclass-init-per-thread
# polyglot-covers: python.threading.local-slots-shared-trap
# polyglot-covers: python.threading.excepthook
# polyglot-covers: python.threading.ExceptHookArgs
# polyglot-covers: python.threading.__excepthook__
# polyglot-covers: python.threading.Thread-exception-not-reraised-by-join
# polyglot-covers: python.threading.excepthook-reference-cycle-trap
# polyglot-covers: python.threading.excepthook-thread-resurrection-trap



def test_plain_local_has_distinct_attribute_dictionary_per_thread():
    """worker 起初看不到 main 的 value，worker 写入也不会改变 main 的 value。"""

    state = threading.local()
    state.value = "main"
    results = queue.Queue()

    def worker():
        results.put(hasattr(state, "value"))
        state.value = "worker"
        results.put(state.value)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert results.get_nowait() is False
    assert results.get_nowait() == "worker"
    assert state.value == "main"


def test_local_subclass_initializer_runs_once_in_each_thread_context():
    """每个 thread 获得自己的 list；不要期待 __init__ 只在 object 创建时执行一次。"""

    initialized_in = []

    class RequestState(threading.local):
        def __init__(self):
            initialized_in.append(threading.get_ident())
            self.values = []

    state = RequestState()
    state.values.append("main")
    results = queue.Queue()

    def worker():
        state.values.append("worker")
        results.put(list(state.values))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert results.get_nowait() == ["worker"]
    assert state.values == ["main"]
    assert len(set(initialized_in)) == 2


def test_slots_on_local_subclass_are_shared_instead_of_thread_local():
    """需要隔离的值必须留在 instance dict；slot descriptor 会暴露同一份 storage。"""

    class SlottedState(threading.local):
        __slots__ = ("shared_value",)

    state = SlottedState()
    state.shared_value = "main"
    results = queue.Queue()

    def worker():
        results.put(state.shared_value)
        state.shared_value = "worker"

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert results.get_nowait() == "main"
    assert state.shared_value == "worker"


def test_custom_excepthook_receives_uncaught_worker_exception():
    """只保存不可变摘要；长期保存 exc_value/thread 会造成 cycle 或 object resurrection。"""

    original_hook = threading.excepthook
    summaries = []

    def capture(args):
        summaries.append(
            {
                "type": args.exc_type,
                "message": str(args.exc_value),
                "has_traceback": args.exc_traceback is not None,
                "thread_name": args.thread.name,
            }
        )

    threading.excepthook = capture
    try:
        thread = threading.Thread(
            target=lambda: (_ for _ in ()).throw(LookupError("missing")),
            name="failing-worker",
        )
        thread.start()
        assert thread.join() is None
    finally:
        threading.excepthook = original_hook

    assert summaries == [
        {
            "type": LookupError,
            "message": "missing",
            "has_traceback": True,
            "thread_name": "failing-worker",
        }
    ]
    assert threading.__excepthook__ is not None


# ``threading.Lock``/``RLock`` ownership、recursion 与 context protocol。
#
# Primitive Lock 不记录 owner，任意 thread 都可 release；RLock 则记录 owner 与 recursion
# level，只能由 owner 对称释放。两者的 context manager 都保证异常路径 release。等待者
# 被唤醒的次序未定义，不能把 lock 当作公平 queue。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.threading.Lock python.threading.Lock-factory
# polyglot-covers: python.threading.Lock.acquire python.threading.Lock.release
# polyglot-covers: python.threading.Lock.locked
# polyglot-covers: python.threading.Lock-nonblocking
# polyglot-covers: python.threading.Lock-non-owner-release
# polyglot-covers: python.threading.Lock-unlocked-release-error
# polyglot-covers: python.threading.lock-context-manager
# polyglot-covers: python.threading.RLock python.threading.RLock-owner
# polyglot-covers: python.threading.RLock-recursion-level
# polyglot-covers: python.threading.RLock-balanced-release
# polyglot-covers: python.threading.TIMEOUT_MAX




def test_primitive_lock_supports_nonblocking_acquire_and_state_query():
    """blocking=False 时立即返回 bool；该模式不能同时指定 timeout。"""

    lock = threading.Lock()

    assert lock.locked() is False
    assert lock.acquire(blocking=False) is True
    assert lock.locked() is True
    assert lock.acquire(blocking=False) is False
    with pytest.raises(ValueError, match="timeout"):
        lock.acquire(blocking=False, timeout=0)

    lock.release()
    assert lock.locked() is False
    with pytest.raises(RuntimeError, match="release unlocked lock"):
        lock.release()


def test_primitive_lock_can_be_released_by_a_different_thread():
    """这是 Lock 与 RLock 的关键差异，但跨 thread release 应只用于清晰的协议。"""

    lock = threading.Lock()
    lock.acquire()
    releaser = threading.Thread(target=lock.release)

    releaser.start()
    releaser.join()

    assert lock.locked() is False


def test_lock_context_manager_releases_even_when_body_raises():
    """with 的 __enter__ 调 acquire，__exit__ 在异常传播前 release。"""

    lock = threading.Lock()

    with pytest.raises(LookupError):
        with lock as acquired:
            assert acquired is True
            assert lock.locked() is True
            raise LookupError("leave protected block")

    assert lock.locked() is False


def test_rlock_requires_balanced_release_before_another_thread_can_enter():
    """同一 owner 可递归 acquire；只 release 一次仍保持 ownership。"""

    lock = threading.RLock()
    outcomes = queue.Queue()

    assert lock.acquire() is True
    assert lock.acquire() is True

    def try_once():
        acquired = lock.acquire(blocking=False)
        outcomes.put(acquired)
        if acquired:
            lock.release()

    first = threading.Thread(target=try_once)
    first.start()
    first.join()
    assert outcomes.get_nowait() is False

    lock.release()
    second = threading.Thread(target=try_once)
    second.start()
    second.join()
    assert outcomes.get_nowait() is False

    lock.release()
    third = threading.Thread(target=try_once)
    third.start()
    third.join()
    assert outcomes.get_nowait() is True


def test_rlock_rejects_release_by_non_owner():
    """即使 lock 已经锁定，非 owner 也不能替 owner 减少 recursion level。"""

    lock = threading.RLock()
    outcomes = queue.Queue()
    lock.acquire()

    def invalid_release():
        try:
            lock.release()
        except RuntimeError as error:
            outcomes.put(str(error))

    thread = threading.Thread(target=invalid_release)
    thread.start()
    thread.join()

    assert "cannot release un-acquired lock" in outcomes.get_nowait()
    lock.release()


def test_timeout_larger_than_timeout_max_raises_before_waiting():
    """TIMEOUT_MAX 是 blocking API 可接受的浮点秒上限，不是推荐等待时间。"""

    lock = threading.Lock()
    lock.acquire()
    try:
        with pytest.raises(OverflowError):
            lock.acquire(timeout=threading.TIMEOUT_MAX * 2)
    finally:
        lock.release()


# ``threading.Condition`` lock discipline、predicate loop 与 notify timing。
#
# Condition 始终绑定一个 Lock/RLock。``wait`` 会临时完整释放 lock，醒来后重新取得；
# ``notify`` 只唤醒 waiter，并不释放 lock，所以 waiter 要等 notifier 离开 critical section
# 才能继续。predicate 必须在 loop 中重查，``wait_for`` 封装了该模式。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.threading.Condition python.threading.Condition-shared-lock
# polyglot-covers: python.threading.Condition.acquire-release-delegation
# polyglot-covers: python.threading.Condition.wait python.threading.Condition-wait-return
# polyglot-covers: python.threading.Condition.wait_for
# polyglot-covers: python.threading.Condition-predicate-loop
# polyglot-covers: python.threading.Condition.notify
# polyglot-covers: python.threading.Condition.notify_all
# polyglot-covers: python.threading.Condition-notify-does-not-release-lock
# polyglot-covers: python.threading.Condition-lock-required
# polyglot-covers: python.threading.Condition-rlock-recursion-restore




def test_wait_and_notify_require_the_condition_lock():
    """Condition method 不会替调用方猜测 critical section；协议违规立即报错。"""

    condition = threading.Condition()

    with pytest.raises(RuntimeError, match="cannot wait"):
        condition.wait(timeout=0)
    with pytest.raises(RuntimeError, match="cannot notify"):
        condition.notify()
    with pytest.raises(RuntimeError, match="cannot notify"):
        condition.notify_all()


def test_wait_for_drives_producer_consumer_predicate_under_lock():
    """predicate 返回 list；wait_for 返回最后一次 predicate 值，而非强制转换后的 bool。"""

    condition = threading.Condition()
    ready_to_wait = threading.Event()
    consumed = threading.Event()
    items = []
    results = []

    def consumer():
        with condition:
            ready_to_wait.set()
            predicate_result = condition.wait_for(lambda: items, timeout=2)
            results.append((predicate_result is items, items.pop(0)))
            consumed.set()

    thread = threading.Thread(target=consumer)
    thread.start()
    assert ready_to_wait.wait(timeout=2)

    with condition:
        items.append("work")
        condition.notify()
        # notify 没有 release 当前 lock，因此 consumer 此刻不可能完成 wait 的重新加锁。
        assert consumed.is_set() is False

    thread.join(timeout=2)
    assert thread.is_alive() is False
    assert results == [(True, "work")]


def test_wait_timeout_returns_false_and_reacquires_lock():
    """timeout=0 不等待；返回后仍在 with critical section 中持有 underlying lock。"""

    lock = threading.Lock()
    condition = threading.Condition(lock)

    with condition:
        assert condition.wait(timeout=0) is False
        assert lock.acquire(blocking=False) is False

    assert lock.acquire(blocking=False) is True
    lock.release()


def test_condition_fully_releases_and_restores_recursive_rlock_level():
    """wait 使用 RLock internal protocol，不能只调用一次 release 留下 recursion level。"""

    lock = threading.RLock()
    condition = threading.Condition(lock)
    worker_started = threading.Event()
    state = {"ready": False}

    def producer():
        worker_started.set()
        with condition:
            state["ready"] = True
            condition.notify()

    with condition:
        with condition:
            thread = threading.Thread(target=producer)
            thread.start()
            assert worker_started.wait(timeout=2)
            assert condition.wait_for(lambda: state["ready"], timeout=2) is True

    thread.join(timeout=2)
    assert thread.is_alive() is False


# ``threading.Semaphore`` permits、bulk release 与 bounded over-release。
#
# Semaphore counter 表示并发 permit 数，acquire 只在能让 counter 保持非负时成功；唤醒
# 顺序不保证公平。BoundedSemaphore 额外记住初始上限，可尽早发现 release 多于 acquire
# 的资源计数错误。两者都可用作 context manager。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.threading.Semaphore python.threading.Semaphore-counter
# polyglot-covers: python.threading.Semaphore.acquire
# polyglot-covers: python.threading.Semaphore-nonblocking
# polyglot-covers: python.threading.Semaphore.release
# polyglot-covers: python.threading.Semaphore.release-n
# polyglot-covers: python.threading.Semaphore-negative-initial-error
# polyglot-covers: python.threading.semaphore-context-manager
# polyglot-covers: python.threading.BoundedSemaphore
# polyglot-covers: python.threading.BoundedSemaphore-over-release
# polyglot-covers: python.threading.Semaphore-concurrency-limit




def test_semaphore_nonblocking_calls_expose_permit_counter_behavior():
    """第三次 acquire 因 counter 为零返回 False；release(2) 一次补回两个 permit。"""

    semaphore = threading.Semaphore(2)

    assert semaphore.acquire(blocking=False) is True
    assert semaphore.acquire(blocking=False) is True
    assert semaphore.acquire(blocking=False) is False

    semaphore.release(2)
    assert semaphore.acquire(blocking=False) is True
    assert semaphore.acquire(blocking=False) is True

    with pytest.raises(ValueError, match="initial value must be >= 0"):
        threading.Semaphore(-1)


def test_context_manager_acquires_and_releases_one_permit():
    """__enter__ 返回 acquire 的 True；异常时 __exit__ 仍归还 permit。"""

    semaphore = threading.Semaphore(1)

    with pytest.raises(LookupError):
        with semaphore as acquired:
            assert acquired is True
            assert semaphore.acquire(blocking=False) is False
            raise LookupError("resource failed")

    assert semaphore.acquire(blocking=False) is True


def test_bounded_semaphore_detects_release_without_matching_acquire():
    """普通 Semaphore 会允许 counter 无限增长；bounded variant 把错误变成 ValueError。"""

    semaphore = threading.BoundedSemaphore(1)

    with pytest.raises(ValueError, match="released too many times"):
        semaphore.release()

    assert semaphore.acquire() is True
    semaphore.release()


def test_semaphore_limits_simultaneous_critical_sections_without_sleep():
    """三个 worker 同时开始竞争，前两个被 Event 保持在区内，第三个只能等待 permit。"""

    semaphore = threading.Semaphore(2)
    start_line = threading.Barrier(4)
    release = threading.Event()
    two_inside = threading.Event()
    state_lock = threading.Lock()
    inside = []
    maximum = 0

    def worker(name):
        nonlocal maximum
        start_line.wait(timeout=2)
        with semaphore:
            with state_lock:
                inside.append(name)
                maximum = max(maximum, len(inside))
                if len(inside) == 2:
                    two_inside.set()
            assert release.wait(timeout=2)
            with state_lock:
                inside.remove(name)

    threads = [threading.Thread(target=worker, args=(name,)) for name in "ABC"]
    for thread in threads:
        thread.start()

    start_line.wait(timeout=2)
    assert two_inside.wait(timeout=2)
    with state_lock:
        assert len(inside) == 2
    release.set()

    for thread in threads:
        thread.join(timeout=2)
        assert thread.is_alive() is False
    assert maximum == 2
    assert inside == []


# ``threading.Event`` level-triggered flag 与 ``Timer`` cancellation。
#
# Event 是共享 boolean flag：set 会唤醒当前所有 waiter，且之后的 wait 也立即成功，直到
# clear。Timer 是 Thread subclass；cancel 只在 action 尚处于等待阶段时有效。测试使用
# barrier/zero-delay/cancel 驱动，不用 sleep 推测调度时机。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.threading.Event python.threading.Event.is_set
# polyglot-covers: python.threading.Event.set python.threading.Event.clear
# polyglot-covers: python.threading.Event.wait python.threading.Event-wake-all
# polyglot-covers: python.threading.Event-level-triggered
# polyglot-covers: python.threading.Timer python.threading.Timer-thread-subclass
# polyglot-covers: python.threading.Timer-args-kwargs
# polyglot-covers: python.threading.Timer.cancel
# polyglot-covers: python.threading.Timer-cancel-before-action-only



def test_event_flag_controls_immediate_wait_result():
    """wait 返回 flag 是否已 set；timeout=0 适合无阻塞查看协议结果。"""

    event = threading.Event()

    assert event.is_set() is False
    assert event.wait(timeout=0) is False
    event.set()
    assert event.is_set() is True
    assert event.wait(timeout=0) is True
    event.clear()
    assert event.is_set() is False


def test_event_set_releases_all_current_waiters_and_stays_set():
    """Barrier 证明两个 waiter 都已启动；set 后两者及未来 wait 都看到 True。"""

    event = threading.Event()
    start_line = threading.Barrier(3)
    results = []
    results_lock = threading.Lock()

    def waiter(name):
        start_line.wait(timeout=2)
        outcome = event.wait(timeout=2)
        with results_lock:
            results.append((name, outcome))

    threads = [threading.Thread(target=waiter, args=(name,)) for name in "AB"]
    for thread in threads:
        thread.start()

    start_line.wait(timeout=2)
    event.set()
    for thread in threads:
        thread.join(timeout=2)

    assert sorted(results) == [("A", True), ("B", True)]
    assert event.wait(timeout=0) is True


def test_zero_delay_timer_calls_function_with_arguments():
    """interval=0 仍由新 thread 调 action；join 用于观察确定的完成边界。"""

    observations = []

    def record(value, *, label):
        observations.append((value, label, threading.current_thread()))

    timer = threading.Timer(0, record, args=(42,), kwargs={"label": "answer"})
    assert isinstance(timer, threading.Thread)

    timer.start()
    timer.join(timeout=2)

    assert timer.is_alive() is False
    assert observations == [(42, "answer", timer)]


def test_cancel_sets_timer_finished_flag_before_long_interval_action():
    """大 interval 不会真的等待：start 后立即 cancel，内部 Event 让 timer thread 退出。"""

    calls = []
    timer = threading.Timer(3600, calls.append, args=("should-not-run",))

    timer.start()
    timer.cancel()
    timer.join(timeout=2)

    assert timer.is_alive() is False
    assert calls == []


# ``threading.Barrier`` generations、leader index、action 与 broken state。
#
# 固定 parties 到齐后，Barrier 为每个参与者返回不同 index，并可进入下一 generation。
# action 由其中一个参与者在 release 前执行；action 异常、timeout 或 abort 会把 barrier
# 置为 broken，使其他 waiter 得到 BrokenBarrierError，避免永久等待。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.threading.Barrier python.threading.Barrier.parties
# polyglot-covers: python.threading.Barrier.wait python.threading.Barrier-index
# polyglot-covers: python.threading.Barrier-reusable-generations
# polyglot-covers: python.threading.Barrier-action
# polyglot-covers: python.threading.Barrier.n_waiting
# polyglot-covers: python.threading.Barrier.broken
# polyglot-covers: python.threading.Barrier.abort python.threading.Barrier.reset
# polyglot-covers: python.threading.Barrier-timeout-breaks
# polyglot-covers: python.threading.Barrier-action-error-breaks
# polyglot-covers: python.threading.BrokenBarrierError




def test_barrier_returns_unique_indices_and_reuses_next_generation():
    """index 可选一个 participant 做 housekeeping，但不能假定某个固定 thread 得到 0。"""

    action_threads = []
    barrier = threading.Barrier(
        3,
        action=lambda: action_threads.append(threading.get_ident()),
    )
    results = {"first": [], "second": []}
    result_lock = threading.Lock()

    def participant():
        first = barrier.wait(timeout=2)
        second = barrier.wait(timeout=2)
        with result_lock:
            results["first"].append(first)
            results["second"].append(second)

    threads = [threading.Thread(target=participant) for _ in range(2)]
    for thread in threads:
        thread.start()

    participant()
    for thread in threads:
        thread.join(timeout=2)

    assert sorted(results["first"]) == [0, 1, 2]
    assert sorted(results["second"]) == [0, 1, 2]
    assert len(action_threads) == 2
    assert barrier.parties == 3
    assert barrier.n_waiting == 0
    assert barrier.broken is False


def test_zero_timeout_breaks_barrier_for_current_and_future_waiters():
    """一次 generation timeout 后，所有后续 wait 都失败，直到显式 reset。"""

    barrier = threading.Barrier(2, timeout=0)

    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()
    assert barrier.broken is True
    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()

    barrier.reset()
    assert barrier.broken is False
    assert barrier.n_waiting == 0


def test_abort_marks_barrier_broken_and_reset_makes_it_empty_again():
    """abort 适合某个 participant 已知无法继续时主动释放其他人的失败路径。"""

    barrier = threading.Barrier(1)
    barrier.abort()

    assert barrier.broken is True
    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()

    barrier.reset()
    assert barrier.broken is False
    assert barrier.wait(timeout=0) == 0


def test_action_exception_reaches_action_runner_and_breaks_barrier():
    """触发 action 的 participant 得原异常；之后进入者统一得到 BrokenBarrierError。"""

    class ActionFailed(RuntimeError):
        pass

    def fail_action():
        raise ActionFailed("cannot publish generation")

    barrier = threading.Barrier(1, action=fail_action)

    with pytest.raises(ActionFailed, match="cannot publish generation"):
        barrier.wait()
    assert barrier.broken is True
    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()


# ``threading`` introspection、trace/profile hooks 与 process-wide configuration。
#
# ``enumerate``/``current_thread`` 提供 Thread wrapper 视图，ident 只是可回收的 magic cookie，
# native_id 也只在线程存活期间唯一。settrace/setprofile 是后续 ``threading.Thread`` 的全局
# 默认 hook，测试必须恢复；stack_size 同样影响之后创建的 thread。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.threading.current_thread python.threading.main_thread
# polyglot-covers: python.threading.enumerate python.threading.active_count
# polyglot-covers: python.threading.get_ident python.threading.get_native_id
# polyglot-covers: python.threading.ident-recycling-caveat
# polyglot-covers: python.threading.settrace python.threading.gettrace
# polyglot-covers: python.threading.setprofile python.threading.getprofile
# polyglot-covers: python.threading.stack_size python.threading.stack-size-minimum
# polyglot-covers: python.threading.deprecated-camelcase-aliases
# polyglot-covers: python.threading.Thread-default-target-name
# polyglot-covers: python.threading.Thread-group-reserved




def test_module_introspection_tracks_a_live_thread_and_its_ids():
    """用 Event 保持 worker 存活，避免在 enumerate 检查前已经退出的 race。"""

    started = threading.Event()
    release = threading.Event()
    observations = {}

    def worker():
        observations["current"] = threading.current_thread()
        observations["ident"] = threading.get_ident()
        observations["native_id"] = threading.get_native_id()
        started.set()
        assert release.wait(timeout=2)

    thread = threading.Thread(target=worker)
    thread.start()
    assert started.wait(timeout=2)

    try:
        assert observations["current"] is thread
        assert observations["ident"] == thread.ident
        assert observations["native_id"] == thread.native_id
        assert thread in threading.enumerate()
        assert threading.active_count() >= 2
        assert threading.current_thread() is threading.main_thread()
        assert threading.main_thread() in threading.enumerate()
    finally:
        release.set()
        thread.join()


def test_trace_hook_is_installed_for_threads_started_after_settrace():
    """threading.settrace 不改变当前 thread；新 worker 启动前会调用 sys.settrace。"""

    original = threading.gettrace()
    events = []

    def trace(frame, event, argument):
        if frame.f_code.co_name == "traced_worker":
            events.append(event)
        return trace

    def traced_worker():
        value = 40
        return value + 2

    threading.settrace(trace)
    try:
        thread = threading.Thread(target=traced_worker)
        thread.start()
        thread.join()
    finally:
        threading.settrace(original)

    assert "call" in events
    assert "return" in events


def test_profile_hook_is_installed_for_future_threading_threads():
    """profile hook 只需返回 None；与 trace hook 不同，不为每个 frame 返回下级 hook。"""

    original = threading.getprofile()
    calls = []

    def profile(frame, event, argument):
        if event == "call" and frame.f_code.co_name == "profiled_worker":
            calls.append(frame.f_code.co_name)

    def profiled_worker():
        return sum((1, 2, 3))

    threading.setprofile(profile)
    try:
        thread = threading.Thread(target=profiled_worker)
        thread.start()
        thread.join()
    finally:
        threading.setprofile(original)

    assert calls == ["profiled_worker"]


def test_stack_size_rejects_too_small_value_and_restores_global_setting():
    """32768 是解释器保证的下限，但 OS 仍可要求更高或不允许修改，此时明确 skip。"""

    original = threading.stack_size()

    with pytest.raises(ValueError):
        threading.stack_size(1)
    assert threading.stack_size() == original

    try:
        previous = threading.stack_size(32768)
    except (RuntimeError, ValueError):
        pytest.skip("当前 thread implementation 不接受 32 KiB stack size")
    else:
        try:
            assert previous == original
            assert threading.stack_size() == 32768
        finally:
            threading.stack_size(original)


def test_python_310_deprecates_legacy_camelcase_aliases():
    """alias 仍可工作以兼容旧代码，但新代码直接使用 property 与 snake_case API。"""

    thread = threading.Thread(name="before")

    with pytest.warns(DeprecationWarning):
        assert thread.getName() == "before"
    with pytest.warns(DeprecationWarning):
        thread.setName("after")
    with pytest.warns(DeprecationWarning):
        thread.setDaemon(True)
    with pytest.warns(DeprecationWarning):
        assert thread.isDaemon() is True
    with pytest.warns(DeprecationWarning):
        assert threading.currentThread() is threading.current_thread()
    with pytest.warns(DeprecationWarning):
        assert threading.activeCount() >= 1

    assert (thread.name, thread.daemon) == ("after", True)


def test_default_name_uses_target_name_and_group_is_reserved():
    """3.10 默认名称包含 target.__name__；group 参数当前必须保持 None。"""

    def synchronize_cache():
        pass

    thread = threading.Thread(target=synchronize_cache)

    assert "synchronize_cache" in thread.name
    with pytest.raises(AssertionError, match="group argument must be None"):
        threading.Thread(group=object())


# ``_thread`` raw thread creation、lock type、identity 与 silent exit。
#
# ``_thread.start_new_thread`` 只返回 ident，没有 join/lifecycle object；生产代码通常应使用
# threading。raw thread 共享相同 lock primitive，未捕获异常走 ``sys.unraisablehook``，
# 而 ``_thread.exit`` 只是抛 SystemExit，raw thread 会静默结束。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python._thread python._thread.start_new_thread
# polyglot-covers: python._thread.start-new-thread-args
# polyglot-covers: python._thread.start-new-thread-kwargs
# polyglot-covers: python._thread.raw-thread-no-join-object
# polyglot-covers: python._thread.allocate_lock python._thread.LockType
# polyglot-covers: python._thread.lock-context-manager
# polyglot-covers: python._thread.error python._thread.error-runtimeerror-alias
# polyglot-covers: python._thread.get_ident python._thread.get_native_id
# polyglot-covers: python._thread.TIMEOUT_MAX
# polyglot-covers: python._thread.exit python._thread.exit-systemexit




def test_start_new_thread_passes_tuple_args_and_keyword_dict():
    """返回值是 raw integer ident；Event 承担本例的完成通知，因为 API 没有 join。"""

    completed = threading.Event()
    observations = queue.Queue()

    def worker(value, *, multiplier):
        observations.put(
            (value * multiplier, _thread.get_ident(), _thread.get_native_id())
        )
        completed.set()

    returned_ident = _thread.start_new_thread(
        worker,
        (6,),
        {"multiplier": 7},
    )

    assert isinstance(returned_ident, int)
    assert completed.wait(timeout=2)
    result, worker_ident, native_id = observations.get_nowait()
    assert result == 42
    assert worker_ident == returned_ident
    assert isinstance(native_id, int)


def test_start_new_thread_requires_args_tuple():
    """即使 callable 不取参数，args 也必须是 tuple 而不是通用 iterable。"""

    with pytest.raises(TypeError):
        _thread.start_new_thread(lambda: None, [])


def test_allocate_lock_returns_documented_type_and_context_protocol():
    """threading.Lock 建立在同一 primitive 上；_thread.error 现为 RuntimeError alias。"""

    lock = _thread.allocate_lock()

    assert isinstance(lock, _thread.LockType)
    assert _thread.error is RuntimeError
    assert lock.locked() is False
    with lock as acquired:
        assert acquired is True
        assert lock.locked() is True
        assert lock.acquire(False) is False
    assert lock.locked() is False
    assert _thread.TIMEOUT_MAX == threading.TIMEOUT_MAX


def test_thread_exit_raises_systemexit_and_raw_thread_treats_it_as_silent_exit():
    """先在普通 call 中证明异常类型，再由 raw worker 的 finally 通知结束。"""

    with pytest.raises(SystemExit):
        _thread.exit()

    completed = threading.Event()

    def worker():
        try:
            _thread.exit()
        finally:
            completed.set()

    _thread.start_new_thread(worker, ())

    assert completed.wait(timeout=2)


# ``_thread`` unraisable exception boundary 与 ``interrupt_main`` signal dispatch。
#
# raw thread 没有 Thread.excepthook；普通异常交给 ``sys.unraisablehook``，hook args.object
# 是原 target callable。``interrupt_main`` 不真正发送 OS signal，只安排 main thread 调用
# Python signal handler；为避免影响 pytest process，signal workflow 放进 child interpreter。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python._thread.unhandled-exception
# polyglot-covers: python._thread.sys-unraisablehook-dispatch
# polyglot-covers: python._thread.unraisablehook-object-is-target
# polyglot-covers: python._thread.SystemExit-silently-ignored
# polyglot-covers: python._thread.interrupt_main
# polyglot-covers: python._thread.interrupt-main-custom-signum
# polyglot-covers: python._thread.interrupt-main-schedules-handler




def test_raw_thread_exception_is_reported_to_sys_unraisablehook():
    """hook 中只保存摘要并立即释放 args，避免保留 traceback/reference cycle。"""

    original_hook = sys.unraisablehook
    completed = threading.Event()
    summaries = []

    def fail_worker():
        raise LookupError("raw failure")

    def capture(args):
        summaries.append(
            (
                args.exc_type,
                str(args.exc_value),
                args.object is fail_worker,
                args.err_msg,
            )
        )
        completed.set()

    sys.unraisablehook = capture
    try:
        _thread.start_new_thread(fail_worker, ())
        assert completed.wait(timeout=2)
    finally:
        sys.unraisablehook = original_hook

    assert summaries == [
        (
            LookupError,
            "raw failure",
            True,
            "Exception ignored in thread started by",
        )
    ]


@pytest.mark.skipif(os.name != "posix", reason="custom SIGUSR1 案例使用 POSIX signal")
def test_interrupt_main_custom_signal_runs_python_handler_in_child_process():
    """child 隔离 process-global signal handler；raw worker 发请求，main loop 执行 handler。"""

    code = """
import _thread
import json
import signal
import threading

requested = threading.Event()
received = []

def handle(signum, frame):
    received.append((signum, threading.current_thread() is threading.main_thread()))

def request_interrupt():
    _thread.interrupt_main(signal.SIGUSR1)
    requested.set()

signal.signal(signal.SIGUSR1, handle)
_thread.start_new_thread(request_interrupt, ())
assert requested.wait(timeout=2)
assert received
print(json.dumps(received))
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.stderr == ""
    assert completed.stdout.strip() == f"[[{signal.SIGUSR1}, true]]"
