"""267｜``Queue.task_done/join`` 的 unfinished-task protocol 与 worker workflow。

get 只把 item 从容器移走，并不表示业务处理完成；每次 put 增加 unfinished count，每个成功
get 最终必须恰好一次 task_done。join 等计数归零而非 queue 变空。worker 应把 task_done
放在 finally 中，否则异常路径会让 join 永久等待；多调用一次则以 ValueError 暴露失配。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.queue.Queue.task_done
# polyglot-covers: python.queue.Queue.join
# polyglot-covers: python.queue.unfinished-task-counter
# polyglot-covers: python.queue.get-does-not-finish-task
# polyglot-covers: python.queue.join-waits-for-processing-not-emptiness
# polyglot-covers: python.queue.task-done-exactly-once
# polyglot-covers: python.queue.task-done-overcall-valueerror
# polyglot-covers: python.queue.worker-task-done-finally
# polyglot-covers: python.queue.multi-producer-consumer-locking

import queue
import threading

import pytest


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

    with pytest.raises(ValueError, match="task_done\(\) called too many times"):
        work.task_done()
