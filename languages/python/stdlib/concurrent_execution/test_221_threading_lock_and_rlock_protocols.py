"""221｜``threading.Lock``/``RLock`` ownership、recursion 与 context protocol。

Primitive Lock 不记录 owner，任意 thread 都可 release；RLock 则记录 owner 与 recursion
level，只能由 owner 对称释放。两者的 context manager 都保证异常路径 release。等待者
被唤醒的次序未定义，不能把 lock 当作公平 queue。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import queue
import threading

import pytest


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
