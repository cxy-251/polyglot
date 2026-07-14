"""264｜``sched.scheduler`` 的绝对/相对事件、优先级、queue 与取消。

scheduler 把时间来源和等待策略注入构造器，因此业务代码可使用 monotonic clock，测试则可
使用 deterministic fake clock。较小 priority 数先执行；同一 time/priority 保持登记顺序。
enter/enterabs 返回的 Event 是 cancel handle，queue 返回按执行顺序排列的快照。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.sched.scheduler
# polyglot-covers: python.sched.scheduler-timefunc
# polyglot-covers: python.sched.scheduler-delayfunc
# polyglot-covers: python.sched.scheduler.enter
# polyglot-covers: python.sched.scheduler.enterabs
# polyglot-covers: python.sched.scheduler.cancel
# polyglot-covers: python.sched.scheduler.empty
# polyglot-covers: python.sched.scheduler.queue
# polyglot-covers: python.sched.Event
# polyglot-covers: python.sched.event-priority-order
# polyglot-covers: python.sched.equal-priority-registration-order
# polyglot-covers: python.sched.action-arguments-kwargs
# polyglot-covers: python.sched.delayfunc-zero-yield

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


def test_absolute_and_relative_events_use_priority_then_registration_order():
    clock = FakeClock(now=100)
    scheduler = sched.scheduler(clock.time, clock.delay)
    calls = []

    def record(label, *, suffix=""):
        calls.append(label + suffix)

    relative = scheduler.enter(
        5,
        2,
        record,
        argument=("relative-first",),
        kwargs={"suffix": "!"},
    )
    scheduler.enterabs(105, 1, record, argument=("higher-priority",))
    scheduler.enterabs(105, 2, record, argument=("relative-second",))

    assert relative.time == 105
    assert relative.priority == 2
    assert relative.action is record
    assert relative.argument == ("relative-first",)
    assert relative.kwargs == {"suffix": "!"}

    scheduler.run()

    assert calls == ["higher-priority", "relative-first!", "relative-second"]
    # 第一次等待推进到 deadline；每个 action 后 delayfunc(0) 给其他线程让出机会。
    assert clock.delays == [5, 0, 0, 0]
    assert scheduler.empty() is True


def test_queue_is_an_ordered_snapshot_and_event_is_a_cancel_handle():
    clock = FakeClock()
    scheduler = sched.scheduler(clock.time, clock.delay)
    later = scheduler.enterabs(20, 1, lambda: None)
    earlier = scheduler.enterabs(10, 1, lambda: None)

    snapshot = scheduler.queue
    assert [event.time for event in snapshot] == [10, 20]
    assert snapshot[0] is earlier
    snapshot.clear()
    assert scheduler.empty() is False

    scheduler.cancel(earlier)
    assert scheduler.queue == [later]
    with pytest.raises(ValueError):
        scheduler.cancel(earlier)
