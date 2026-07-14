"""224｜``threading.Event`` level-triggered flag 与 ``Timer`` cancellation。

Event 是共享 boolean flag：set 会唤醒当前所有 waiter，且之后的 wait 也立即成功，直到
clear。Timer 是 Thread subclass；cancel 只在 action 尚处于等待阶段时有效。测试使用
barrier/zero-delay/cancel 驱动，不用 sleep 推测调度时机。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.threading.Event python.threading.Event.is_set
# polyglot-covers: python.threading.Event.set python.threading.Event.clear
# polyglot-covers: python.threading.Event.wait python.threading.Event-wake-all
# polyglot-covers: python.threading.Event-level-triggered
# polyglot-covers: python.threading.Timer python.threading.Timer-thread-subclass
# polyglot-covers: python.threading.Timer-args-kwargs
# polyglot-covers: python.threading.Timer.cancel
# polyglot-covers: python.threading.Timer-cancel-before-action-only

import threading


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
