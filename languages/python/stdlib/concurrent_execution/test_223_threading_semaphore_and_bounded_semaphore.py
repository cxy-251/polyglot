"""223｜``threading.Semaphore`` permits、bulk release 与 bounded over-release。

Semaphore counter 表示并发 permit 数，acquire 只在能让 counter 保持非负时成功；唤醒
顺序不保证公平。BoundedSemaphore 额外记住初始上限，可尽早发现 release 多于 acquire
的资源计数错误。两者都可用作 context manager。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.threading.Semaphore python.threading.Semaphore-counter
# polyglot-covers: python.threading.Semaphore.acquire
# polyglot-covers: python.threading.Semaphore-nonblocking
# polyglot-covers: python.threading.Semaphore.release
# polyglot-covers: python.threading.Semaphore.release-n
# polyglot-covers: python.threading.Semaphore-negative-initial-error
# polyglot-covers: python.threading.semaphore-context-manager
# polyglot-covers: python.threading.BoundedSemaphore
# polyglot-covers: python.threading.BoundedSemaphore-over-release
# polyglot-covers: python.threading.Semaphore-concurrency-limit

import threading

import pytest


def test_semaphore_nonblocking_calls_expose_permit_counter_behavior():
    """第三次 acquire 因 counter 为零返回 False；release(2) 一次补回两个 permit。"""

    semaphore = threading.Semaphore(2)

    assert semaphore.acquire(blocking=False) is True
    assert semaphore.acquire(blocking=False) is True
    assert semaphore.acquire(blocking=False) is False

    semaphore.release(2)
    assert semaphore.acquire(blocking=False) is True
    assert semaphore.acquire(blocking=False) is True

    with pytest.raises(ValueError, match="initial value must be >= 0"):
        threading.Semaphore(-1)


def test_context_manager_acquires_and_releases_one_permit():
    """__enter__ 返回 acquire 的 True；异常时 __exit__ 仍归还 permit。"""

    semaphore = threading.Semaphore(1)

    with pytest.raises(LookupError):
        with semaphore as acquired:
            assert acquired is True
            assert semaphore.acquire(blocking=False) is False
            raise LookupError("resource failed")

    assert semaphore.acquire(blocking=False) is True


def test_bounded_semaphore_detects_release_without_matching_acquire():
    """普通 Semaphore 会允许 counter 无限增长；bounded variant 把错误变成 ValueError。"""

    semaphore = threading.BoundedSemaphore(1)

    with pytest.raises(ValueError, match="released too many times"):
        semaphore.release()

    assert semaphore.acquire() is True
    semaphore.release()


def test_semaphore_limits_simultaneous_critical_sections_without_sleep():
    """三个 worker 同时开始竞争，前两个被 Event 保持在区内，第三个只能等待 permit。"""

    semaphore = threading.Semaphore(2)
    start_line = threading.Barrier(4)
    release = threading.Event()
    two_inside = threading.Event()
    state_lock = threading.Lock()
    inside = []
    maximum = 0

    def worker(name):
        nonlocal maximum
        start_line.wait(timeout=2)
        with semaphore:
            with state_lock:
                inside.append(name)
                maximum = max(maximum, len(inside))
                if len(inside) == 2:
                    two_inside.set()
            assert release.wait(timeout=2)
            with state_lock:
                inside.remove(name)

    threads = [threading.Thread(target=worker, args=(name,)) for name in "ABC"]
    for thread in threads:
        thread.start()

    start_line.wait(timeout=2)
    assert two_inside.wait(timeout=2)
    with state_lock:
        assert len(inside) == 2
    release.set()

    for thread in threads:
        thread.join(timeout=2)
        assert thread.is_alive() is False
    assert maximum == 2
    assert inside == []
