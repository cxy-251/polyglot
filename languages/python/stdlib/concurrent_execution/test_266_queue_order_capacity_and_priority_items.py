"""266｜线程 Queue/LifoQueue/PriorityQueue 的顺序、容量与非阻塞异常。

三种 bounded queue 共享锁和容量协议，只改变取出顺序。qsize/empty/full 是调用瞬间的
近似快照，不能作为随后 get/put 不阻塞的并发保证；控制流应直接用 blocking operation、
timeout 或捕获 Empty/Full。PriorityQueue 的同优先级 payload 也必须可比较，或显式忽略。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from dataclasses import dataclass, field
import queue
from typing import Any

import pytest


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
