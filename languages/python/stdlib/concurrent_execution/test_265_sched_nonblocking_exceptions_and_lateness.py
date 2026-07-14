"""265｜scheduler 非阻塞轮询、异常一致性与落后策略。

run(blocking=False) 只执行当前到期事件，并返回离下一 deadline 的延迟；它适合嵌入已有
event loop。action 或 delayfunc 的异常会向上传播，但 queue 保持一致：已开始的失败 action
不会重试，尚未弹出的事件仍保留。执行过慢只会落后，不会静默丢事件。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sched.scheduler.run
# polyglot-covers: python.sched.scheduler.run-blocking-false
# polyglot-covers: python.sched.nonblocking-next-delay
# polyglot-covers: python.sched.action-exception-state-consistency
# polyglot-covers: python.sched.delay-exception-state-consistency
# polyglot-covers: python.sched.failed-action-not-retried
# polyglot-covers: python.sched.late-events-not-dropped
# polyglot-covers: python.sched.action-schedules-earlier-event

import sched

import pytest


class FakeClock:
    def __init__(self, now=0):
        self.now = now
        self.delays = []

    def time(self):
        return self.now

    def delay(self, amount):
        self.delays.append(amount)
        self.now += amount


def test_nonblocking_run_executes_due_events_and_returns_next_delay():
    clock = FakeClock(now=10)
    scheduler = sched.scheduler(clock.time, clock.delay)
    calls = []
    scheduler.enterabs(12, 1, calls.append, argument=("first",))
    scheduler.enterabs(15, 1, calls.append, argument=("second",))

    assert scheduler.run(blocking=False) == 2
    assert calls == []
    assert clock.delays == []

    clock.now = 12
    assert scheduler.run(blocking=False) == 3
    assert calls == ["first"]
    assert clock.delays == [0]


def test_action_exception_removes_only_the_started_event():
    clock = FakeClock()
    scheduler = sched.scheduler(clock.time, clock.delay)
    calls = []

    def fail():
        raise LookupError("action failed")

    failed = scheduler.enterabs(0, 1, fail)
    remaining = scheduler.enterabs(0, 2, calls.append, argument=("kept",))

    with pytest.raises(LookupError, match="action failed"):
        scheduler.run()

    assert failed not in scheduler.queue
    assert scheduler.queue == [remaining]
    scheduler.run()
    assert calls == ["kept"]


def test_delay_exception_keeps_the_not_yet_started_event_queued():
    def broken_delay(amount):
        raise RuntimeError(f"cannot wait {amount}")

    scheduler = sched.scheduler(lambda: 0, broken_delay)
    event = scheduler.enterabs(5, 1, lambda: None)

    with pytest.raises(RuntimeError, match="cannot wait 5"):
        scheduler.run()

    assert scheduler.queue == [event]


def test_late_and_newly_inserted_events_are_reordered_but_not_dropped():
    clock = FakeClock()
    scheduler = sched.scheduler(clock.time, clock.delay)
    calls = []

    def first():
        calls.append("first")
        clock.now = 10
        scheduler.enterabs(1, 1, calls.append, argument=("inserted",))

    scheduler.enterabs(0, 1, first)
    scheduler.enterabs(2, 1, calls.append, argument=("original",))

    scheduler.run()

    assert calls == ["first", "inserted", "original"]
    assert scheduler.empty() is True
