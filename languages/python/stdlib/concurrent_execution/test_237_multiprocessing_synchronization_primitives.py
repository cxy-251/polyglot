"""237｜multiprocessing synchronization API differences 与 cross-process coordination。

这些 primitive 基本复刻 threading，但 Lock/RLock/Semaphore 的参数名是 ``block``；负
timeout 按零处理，unlocked Lock.release 抛 ValueError，RLock ownership 错误抛
AssertionError。对象必须来自与 Process 兼容的 context，才能安全跨 process 共享。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Lock
# polyglot-covers: python.multiprocessing.Lock-acquire-block-parameter
# polyglot-covers: python.multiprocessing.Lock-negative-timeout-is-zero
# polyglot-covers: python.multiprocessing.Lock-release-valueerror
# polyglot-covers: python.multiprocessing.RLock
# polyglot-covers: python.multiprocessing.RLock-release-assertionerror
# polyglot-covers: python.multiprocessing.Semaphore
# polyglot-covers: python.multiprocessing.BoundedSemaphore
# polyglot-covers: python.multiprocessing.BoundedSemaphore-macos-caveat
# polyglot-covers: python.multiprocessing.Event
# polyglot-covers: python.multiprocessing.Condition
# polyglot-covers: python.multiprocessing.Condition.wait_for
# polyglot-covers: python.multiprocessing.Barrier
# polyglot-covers: python.multiprocessing.sync-context-manager
# polyglot-covers: python.multiprocessing.context-compatible-primitives

import multiprocessing
import sys

import pytest


def _wait_for_shared_value(condition, value, connection):
    with condition:
        matched = condition.wait_for(lambda: value.value == 42, timeout=5)
        connection.send((matched, value.value))
    connection.close()


def _cross_process_barrier(barrier, connection):
    connection.send(barrier.wait(timeout=5))
    connection.close()


def test_lock_signature_and_errors_differ_from_threading_lock():
    """block=False 时 timeout 被忽略；block=True + negative timeout 立即返回 False。"""

    lock = multiprocessing.Lock()

    assert lock.acquire() is True
    assert lock.acquire(block=False, timeout=999) is False
    assert lock.acquire(block=True, timeout=-1) is False
    lock.release()
    with pytest.raises(ValueError, match="released too many times"):
        lock.release()


def test_rlock_is_recursive_but_unowned_release_uses_assertionerror():
    """同一 process/thread acquire 两次就必须 release 两次。"""

    lock = multiprocessing.RLock()

    with lock:
        assert lock.acquire(block=False) is True
        lock.release()

    with pytest.raises(AssertionError, match="attempt to release recursive lock"):
        lock.release()


def test_semaphore_permits_and_bounded_overrelease_detection():
    """macOS 无 sem_getvalue，BoundedSemaphore 无法区别 over-release，故只断言通用部分。"""

    semaphore = multiprocessing.Semaphore(1)
    assert semaphore.acquire(block=False) is True
    assert semaphore.acquire(block=False) is False
    semaphore.release()

    bounded = multiprocessing.BoundedSemaphore(1)
    if sys.platform == "darwin":
        bounded.acquire()
        bounded.release()
    else:
        with pytest.raises(ValueError, match="released too many times"):
            bounded.release()


def test_condition_and_value_coordinate_spawned_process():
    """Value 与 Condition 共用同一个 RLock，predicate/更新始终在同一 critical section。"""

    context = multiprocessing.get_context("spawn")
    lock = context.RLock()
    condition = context.Condition(lock)
    value = context.Value("i", 0, lock=lock)
    parent_connection, child_connection = context.Pipe()
    process = context.Process(
        target=_wait_for_shared_value,
        args=(condition, value, child_connection),
    )
    process.start()
    child_connection.close()

    with condition:
        value.value = 42
        condition.notify_all()

    assert parent_connection.poll(timeout=5)
    assert parent_connection.recv() == (True, 42)
    process.join(timeout=5)
    assert process.exitcode == 0
    parent_connection.close()
    process.close()


def test_barrier_assigns_unique_indices_across_parent_and_children():
    """三个 process 到齐才释放；返回 index 可选一个 participant 执行收尾。"""

    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(3)
    parent_connections = []
    processes = []

    for _ in range(2):
        parent_connection, child_connection = context.Pipe()
        process = context.Process(
            target=_cross_process_barrier,
            args=(barrier, child_connection),
        )
        process.start()
        child_connection.close()
        parent_connections.append(parent_connection)
        processes.append(process)

    parent_index = barrier.wait(timeout=5)
    child_indices = []
    for connection in parent_connections:
        assert connection.poll(timeout=5)
        child_indices.append(connection.recv())
        connection.close()
    for process in processes:
        process.join(timeout=5)
        assert process.exitcode == 0
        process.close()

    assert sorted([parent_index, *child_indices]) == [0, 1, 2]
