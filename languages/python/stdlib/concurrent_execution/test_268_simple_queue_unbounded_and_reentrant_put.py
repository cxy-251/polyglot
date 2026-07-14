"""268｜``SimpleQueue`` 的精简 FIFO protocol 与 CPython reentrant implementation。

SimpleQueue 永不因容量阻塞，put 的 block/timeout 只为 Queue 兼容而存在；它没有 task
tracking。get 仍可阻塞。CPython 的 C 实现允许同线程的 put/get 被另一次 put 重入，因而
可安全用于 __del__ 或 weakref callback；这是 implementation detail，不应假定其他实现相同。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import gc
import platform
import queue
import threading

import pytest


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
