"""225｜``threading.Barrier`` generations、leader index、action 与 broken state。

固定 parties 到齐后，Barrier 为每个参与者返回不同 index，并可进入下一 generation。
action 由其中一个参与者在 release 前执行；action 异常、timeout 或 abort 会把 barrier
置为 broken，使其他 waiter 得到 BrokenBarrierError，避免永久等待。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.threading.Barrier python.threading.Barrier.parties
# polyglot-covers: python.threading.Barrier.wait python.threading.Barrier-index
# polyglot-covers: python.threading.Barrier-reusable-generations
# polyglot-covers: python.threading.Barrier-action
# polyglot-covers: python.threading.Barrier.n_waiting
# polyglot-covers: python.threading.Barrier.broken
# polyglot-covers: python.threading.Barrier.abort python.threading.Barrier.reset
# polyglot-covers: python.threading.Barrier-timeout-breaks
# polyglot-covers: python.threading.Barrier-action-error-breaks
# polyglot-covers: python.threading.BrokenBarrierError

import threading

import pytest


def test_barrier_returns_unique_indices_and_reuses_next_generation():
    """index 可选一个 participant 做 housekeeping，但不能假定某个固定 thread 得到 0。"""

    action_threads = []
    barrier = threading.Barrier(
        3,
        action=lambda: action_threads.append(threading.get_ident()),
    )
    results = {"first": [], "second": []}
    result_lock = threading.Lock()

    def participant():
        first = barrier.wait(timeout=2)
        second = barrier.wait(timeout=2)
        with result_lock:
            results["first"].append(first)
            results["second"].append(second)

    threads = [threading.Thread(target=participant) for _ in range(2)]
    for thread in threads:
        thread.start()

    participant()
    for thread in threads:
        thread.join(timeout=2)

    assert sorted(results["first"]) == [0, 1, 2]
    assert sorted(results["second"]) == [0, 1, 2]
    assert len(action_threads) == 2
    assert barrier.parties == 3
    assert barrier.n_waiting == 0
    assert barrier.broken is False


def test_zero_timeout_breaks_barrier_for_current_and_future_waiters():
    """一次 generation timeout 后，所有后续 wait 都失败，直到显式 reset。"""

    barrier = threading.Barrier(2, timeout=0)

    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()
    assert barrier.broken is True
    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()

    barrier.reset()
    assert barrier.broken is False
    assert barrier.n_waiting == 0


def test_abort_marks_barrier_broken_and_reset_makes_it_empty_again():
    """abort 适合某个 participant 已知无法继续时主动释放其他人的失败路径。"""

    barrier = threading.Barrier(1)
    barrier.abort()

    assert barrier.broken is True
    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()

    barrier.reset()
    assert barrier.broken is False
    assert barrier.wait(timeout=0) == 0


def test_action_exception_reaches_action_runner_and_breaks_barrier():
    """触发 action 的 participant 得原异常；之后进入者统一得到 BrokenBarrierError。"""

    class ActionFailed(RuntimeError):
        pass

    def fail_action():
        raise ActionFailed("cannot publish generation")

    barrier = threading.Barrier(1, action=fail_action)

    with pytest.raises(ActionFailed, match="cannot publish generation"):
        barrier.wait()
    assert barrier.broken is True
    with pytest.raises(threading.BrokenBarrierError):
        barrier.wait()
