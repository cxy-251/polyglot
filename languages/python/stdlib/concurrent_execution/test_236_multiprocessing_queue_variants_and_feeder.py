"""236｜multiprocessing ``Queue``/``SimpleQueue``/``JoinableQueue`` lifecycle。

Queue 用 pipe、locks 和 background feeder thread 传送 pickle；``put`` 返回时 bytes 可能
尚未进入 pipe，因此 ``empty/qsize`` 只近似，且 producer 在 feeder flush 前退出会影响
join。SimpleQueue 没有 feeder，JoinableQueue 则以 task_done/join 追踪 unfinished tasks。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Queue
# polyglot-covers: python.multiprocessing.Queue-pickle-copy
# polyglot-covers: python.multiprocessing.Queue-background-feeder-thread
# polyglot-covers: python.multiprocessing.Queue.empty-unreliable
# polyglot-covers: python.multiprocessing.Queue.qsize-platform-caveat
# polyglot-covers: python.multiprocessing.Queue.put_nowait
# polyglot-covers: python.multiprocessing.Queue.get_nowait
# polyglot-covers: python.multiprocessing.Queue.Full
# polyglot-covers: python.multiprocessing.Queue.Empty
# polyglot-covers: python.multiprocessing.Queue.close
# polyglot-covers: python.multiprocessing.Queue.join_thread
# polyglot-covers: python.multiprocessing.Queue.cancel_join_thread
# polyglot-covers: python.multiprocessing.SimpleQueue
# polyglot-covers: python.multiprocessing.JoinableQueue
# polyglot-covers: python.multiprocessing.JoinableQueue.task_done
# polyglot-covers: python.multiprocessing.JoinableQueue.join
# polyglot-covers: python.multiprocessing.JoinableQueue-over-task-done

import multiprocessing
import queue

import pytest


def test_queue_round_trip_returns_pickled_copy_and_nonblocking_errors():
    """full 由 maxsize semaphore 决定；empty/qsize 不用于 correctness protocol。"""

    work = multiprocessing.Queue(maxsize=1)
    payload = {"items": [1, 2]}

    try:
        work.put_nowait(payload)
        with pytest.raises(queue.Full):
            work.put_nowait("too-much")

        received = work.get(timeout=5)
        assert received == payload
        assert received is not payload
        assert received["items"] is not payload["items"]
        with pytest.raises(queue.Empty):
            work.get_nowait()
    finally:
        work.close()
        work.join_thread()

    with pytest.raises(ValueError, match="Queue.*closed"):
        work.put("after-close")


def test_cancel_join_thread_is_explicit_data_loss_tradeoff():
    """它只取消 process exit 时的隐式 feeder join；不代表 queue/feeder 已经关闭。"""

    work = multiprocessing.Queue()
    work.cancel_join_thread()

    work.put("still-usable")
    assert work.get(timeout=5) == "still-usable"
    work.close()


def test_simple_queue_has_synchronous_pipe_api_and_explicit_close():
    """SimpleQueue 没有 timeout/maxsize/task tracking；empty 在本例静态边界可观察。"""

    work = multiprocessing.SimpleQueue()

    assert work.empty() is True
    work.put([1, 2, 3])
    assert work.empty() is False
    assert work.get() == [1, 2, 3]
    assert work.empty() is True
    work.close()

    with pytest.raises(OSError):
        work.put("after-close")


def test_joinable_queue_requires_one_task_done_per_get():
    """join 等 unfinished counter 归零；多调用一次 task_done 是可检测的逻辑错误。"""

    work = multiprocessing.JoinableQueue()

    try:
        work.put("job")
        assert work.get(timeout=5) == "job"
        work.task_done()
        assert work.join() is None
        with pytest.raises(ValueError, match="task_done.*too many times"):
            work.task_done()
    finally:
        work.close()
        work.join_thread()
