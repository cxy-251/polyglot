"""222｜``threading.Condition`` lock discipline、predicate loop 与 notify timing。

Condition 始终绑定一个 Lock/RLock。``wait`` 会临时完整释放 lock，醒来后重新取得；
``notify`` 只唤醒 waiter，并不释放 lock，所以 waiter 要等 notifier 离开 critical section
才能继续。predicate 必须在 loop 中重查，``wait_for`` 封装了该模式。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import threading

import pytest


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
