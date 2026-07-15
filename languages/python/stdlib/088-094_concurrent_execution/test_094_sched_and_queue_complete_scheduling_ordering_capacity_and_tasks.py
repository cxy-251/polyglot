"""094｜``sched.scheduler`` 的绝对/相对事件、优先级、queue 与取消。

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
from dataclasses import dataclass, field
import queue
from typing import Any
import threading
import gc
import platform

class SchedulingClock:
    def __init__(self, now=0):
        self.now = now
        self.delays = []

    def time(self):
        return self.now

    def delay(self, amount):
        self.delays.append(amount)
        self.now += amount


def test_absolute_and_relative_events_use_priority_then_registration_order():
    clock = SchedulingClock(now=100)
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
    clock = SchedulingClock()
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


# scheduler 非阻塞轮询、异常一致性与落后策略。
#
# run(blocking=False) 只执行当前到期事件，并返回离下一 deadline 的延迟；它适合嵌入已有
# event loop。action 或 delayfunc 的异常会向上传播，但 queue 保持一致：已开始的失败 action
# 不会重试，尚未弹出的事件仍保留。执行过慢只会落后，不会静默丢事件。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.sched.scheduler.run
# polyglot-covers: python.sched.scheduler.run-blocking-false
# polyglot-covers: python.sched.nonblocking-next-delay
# polyglot-covers: python.sched.action-exception-state-consistency
# polyglot-covers: python.sched.delay-exception-state-consistency
# polyglot-covers: python.sched.failed-action-not-retried
# polyglot-covers: python.sched.late-events-not-dropped
# polyglot-covers: python.sched.action-schedules-earlier-event




class NonblockingClock:
    def __init__(self, now=0):
        self.now = now
        self.delays = []

    def time(self):
        return self.now

    def delay(self, amount):
        self.delays.append(amount)
        self.now += amount


def test_nonblocking_run_executes_due_events_and_returns_next_delay():
    clock = NonblockingClock(now=10)
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
    clock = NonblockingClock()
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
    clock = NonblockingClock()
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


# 线程 Queue/LifoQueue/PriorityQueue 的顺序、容量与非阻塞异常。
#
# 三种 bounded queue 共享锁和容量协议，只改变取出顺序。qsize/empty/full 是调用瞬间的
# 近似快照，不能作为随后 get/put 不阻塞的并发保证；控制流应直接用 blocking operation、
# timeout 或捕获 Empty/Full。PriorityQueue 的同优先级 payload 也必须可比较，或显式忽略。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.queue.Queue
# polyglot-covers: python.queue.LifoQueue
# polyglot-covers: python.queue.PriorityQueue
# polyglot-covers: python.queue.Empty
# polyglot-covers: python.queue.Full
# polyglot-covers: python.queue.Queue.qsize
# polyglot-covers: python.queue.Queue.empty
# polyglot-covers: python.queue.Queue.full
# polyglot-covers: python.queue.Queue.put
# polyglot-covers: python.queue.Queue.put_nowait
# polyglot-covers: python.queue.Queue.get
# polyglot-covers: python.queue.Queue.get_nowait
# polyglot-covers: python.queue.nonblocking-timeout-ignored
# polyglot-covers: python.queue.maxsize-nonpositive-unbounded
# polyglot-covers: python.queue.state-inspection-race-trap
# polyglot-covers: python.queue.priority-lowest-first
# polyglot-covers: python.queue.priority-payload-comparability-trap
# polyglot-covers: python.queue.priority-dataclass-compare-false
# polyglot-covers: python.queue.same-thread-reentrancy-not-supported




@dataclass(order=True)
class PrioritizedItem:
    priority: int
    payload: Any = field(compare=False)


def test_fifo_lifo_and_priority_queues_change_only_retrieval_order():
    fifo = queue.Queue()
    lifo = queue.LifoQueue()
    priority = queue.PriorityQueue()

    for container in (fifo, lifo):
        container.put("first")
        container.put("second")
    priority.put((20, "later"))
    priority.put((10, "earlier"))

    assert [fifo.get_nowait(), fifo.get_nowait()] == ["first", "second"]
    assert [lifo.get_nowait(), lifo.get_nowait()] == ["second", "first"]
    assert [priority.get_nowait(), priority.get_nowait()] == [
        (10, "earlier"),
        (20, "later"),
    ]


def test_bounded_queue_nonblocking_operations_raise_full_and_empty():
    work = queue.Queue(maxsize=2)
    assert work.empty() is True
    assert work.full() is False

    assert work.put_nowait("a") is None
    work.put("b", block=False, timeout=-1)
    assert work.qsize() == 2
    assert work.full() is True

    # block=False 时 timeout 被忽略；容量状态直接决定 Full/Empty。
    with pytest.raises(queue.Full):
        work.put("c", block=False, timeout=-1)
    assert work.get_nowait() == "a"
    assert work.get(block=False, timeout=-1) == "b"
    with pytest.raises(queue.Empty):
        work.get(block=False, timeout=-1)


def test_nonpositive_maxsize_is_unbounded():
    work = queue.Queue(maxsize=0)
    for value in range(100):
        work.put_nowait(value)

    assert work.qsize() == 100
    assert work.full() is False


def test_priority_payload_tie_needs_comparable_data_or_a_wrapper():
    broken = queue.PriorityQueue()
    broken.put((1, {"name": "first"}))
    with pytest.raises(TypeError):
        broken.put((1, {"name": "second"}))

    safe = queue.PriorityQueue()
    safe.put(PrioritizedItem(2, {"name": "later"}))
    safe.put(PrioritizedItem(1, {"name": "first"}))

    assert safe.get_nowait().payload == {"name": "first"}
    assert safe.get_nowait().payload == {"name": "later"}


# ``Queue.task_done/join`` 的 unfinished-task protocol 与 worker workflow。
#
# get 只把 item 从容器移走，并不表示业务处理完成；每次 put 增加 unfinished count，每个成功
# get 最终必须恰好一次 task_done。join 等计数归零而非 queue 变空。worker 应把 task_done
# 放在 finally 中，否则异常路径会让 join 永久等待；多调用一次则以 ValueError 暴露失配。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.queue.Queue.task_done
# polyglot-covers: python.queue.Queue.join
# polyglot-covers: python.queue.unfinished-task-counter
# polyglot-covers: python.queue.get-does-not-finish-task
# polyglot-covers: python.queue.join-waits-for-processing-not-emptiness
# polyglot-covers: python.queue.task-done-exactly-once
# polyglot-covers: python.queue.task-done-overcall-valueerror
# polyglot-covers: python.queue.worker-task-done-finally
# polyglot-covers: python.queue.multi-producer-consumer-locking




def test_worker_marks_every_item_in_finally_before_join_can_finish():
    work = queue.Queue()
    processed = []
    worker_finished = threading.Event()
    sentinel = object()

    def worker():
        while True:
            item = work.get()
            try:
                if item is sentinel:
                    return
                processed.append(item * item)
            finally:
                work.task_done()
                if item is sentinel:
                    worker_finished.set()

    thread = threading.Thread(target=worker, name="queue-consumer")
    thread.start()
    for item in (2, 3, 4, sentinel):
        work.put(item)

    work.join()
    assert worker_finished.wait(timeout=2)
    thread.join(timeout=2)

    assert thread.is_alive() is False
    assert processed == [4, 9, 16]


def test_join_still_waits_after_get_until_task_done_is_called():
    work = queue.Queue()
    work.put("retrieved but unfinished")
    assert work.get_nowait() == "retrieved but unfinished"
    assert work.empty() is True

    joined = threading.Event()

    def wait_for_completion():
        work.join()
        joined.set()

    waiter = threading.Thread(target=wait_for_completion)
    waiter.start()
    assert joined.wait(timeout=0.05) is False

    work.task_done()
    assert joined.wait(timeout=2)
    waiter.join(timeout=2)
    assert waiter.is_alive() is False


def test_task_done_more_times_than_put_is_rejected():
    work = queue.Queue()
    work.put("one")
    work.get()
    work.task_done()

    with pytest.raises(ValueError, match=r"task_done\(\) called too many times"):
        work.task_done()


# ``SimpleQueue`` 的精简 FIFO protocol 与 CPython reentrant implementation。
#
# SimpleQueue 永不因容量阻塞，put 的 block/timeout 只为 Queue 兼容而存在；它没有 task
# tracking。get 仍可阻塞。CPython 的 C 实现允许同线程的 put/get 被另一次 put 重入，因而
# 可安全用于 __del__ 或 weakref callback；这是 implementation detail，不应假定其他实现相同。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.queue.SimpleQueue
# polyglot-covers: python.queue.SimpleQueue.qsize
# polyglot-covers: python.queue.SimpleQueue.empty
# polyglot-covers: python.queue.SimpleQueue.put
# polyglot-covers: python.queue.SimpleQueue.put_nowait
# polyglot-covers: python.queue.SimpleQueue.get
# polyglot-covers: python.queue.SimpleQueue.get_nowait
# polyglot-covers: python.queue.SimpleQueue-put-never-blocks
# polyglot-covers: python.queue.SimpleQueue-put-compatibility-arguments
# polyglot-covers: python.queue.SimpleQueue-no-task-tracking
# polyglot-covers: python.queue.SimpleQueue-cpython-reentrant
# polyglot-covers: python.queue.SimpleQueue-destructor-safe




def test_simple_queue_is_unbounded_fifo_and_ignores_put_control_arguments():
    work = queue.SimpleQueue()

    assert work.put("first", block=False, timeout=-1) is None
    assert work.put_nowait("second") is None
    assert work.qsize() == 2
    assert work.empty() is False
    assert work.get_nowait() == "first"
    assert work.get(block=False, timeout=-1) == "second"
    assert work.empty() is True
    with pytest.raises(queue.Empty):
        work.get_nowait()


def test_simple_queue_has_no_task_tracking_protocol():
    work = queue.SimpleQueue()

    assert hasattr(work, "task_done") is False
    assert hasattr(work, "join") is False


def test_blocking_get_is_released_by_a_producer_thread_handoff():
    work = queue.SimpleQueue()
    consumer_started = threading.Event()
    consumer_finished = threading.Event()
    received = []

    def consume():
        consumer_started.set()
        received.append(work.get())
        consumer_finished.set()

    thread = threading.Thread(target=consume)
    thread.start()
    assert consumer_started.wait(timeout=2)

    work.put({"payload": 42})
    assert consumer_finished.wait(timeout=2)
    thread.join(timeout=2)

    assert thread.is_alive() is False
    assert received == [{"payload": 42}]


@pytest.mark.skipif(
    platform.python_implementation() != "CPython",
    reason="reentrant put 是 CPython C implementation detail",
)
def test_cpython_simple_queue_can_be_used_from_a_destructor():
    work = queue.SimpleQueue()

    class EnqueueOnDelete:
        def __del__(self):
            work.put("from __del__")

    value = EnqueueOnDelete()
    del value
    gc.collect()

    assert type(work).__module__ == "_queue"
    assert work.get_nowait() == "from __del__"
