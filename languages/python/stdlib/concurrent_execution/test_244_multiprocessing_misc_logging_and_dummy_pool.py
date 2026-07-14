"""244｜multiprocessing misc introspection、logger 与 thread-backed dummy Pool。

``active_children`` 只看当前 process 的 live children，并顺带 reap 已结束 child。
``cpu_count`` 是机器 CPU 数，不一定等于 affinity 可用数。multiprocessing logger 不与普通
root logger 传播。``multiprocessing.dummy`` 复用 Pool API 但执行于 threads，可接受 lambda。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.active_children
# polyglot-covers: python.multiprocessing.active-children-reaps-finished
# polyglot-covers: python.multiprocessing.cpu_count
# polyglot-covers: python.multiprocessing.cpu-count-vs-affinity
# polyglot-covers: python.multiprocessing.parent_process-main-none
# polyglot-covers: python.multiprocessing.daemon-process-no-children
# polyglot-covers: python.multiprocessing.get_logger
# polyglot-covers: python.multiprocessing.log_to_stderr
# polyglot-covers: python.multiprocessing.logger-no-root-propagation
# polyglot-covers: python.multiprocessing.logging-not-process-shared-lock
# polyglot-covers: python.multiprocessing.dummy
# polyglot-covers: python.multiprocessing.dummy.Pool
# polyglot-covers: python.multiprocessing.pool.ThreadPool
# polyglot-covers: python.multiprocessing.dummy-no-pickling

import multiprocessing
import multiprocessing.dummy
import multiprocessing.pool
import os
import subprocess
import sys
import threading


def _hold_child(started, release):
    started.set()
    if not release.wait(timeout=5):
        raise RuntimeError("parent did not release child")


def _no_op_child():
    return None


def _daemon_attempts_child(connection):
    try:
        child = multiprocessing.Process(target=_no_op_child)
        child.start()
    except AssertionError as error:
        connection.send(str(error))
    finally:
        connection.close()


def _thread_identity(value):
    return value, os.getpid(), threading.get_ident()


def test_active_children_contains_live_child_and_main_has_no_parent_process():
    """Event 让 child 保持 live；显式 join 仍是比依赖 active_children side effect 更清晰的清理。"""

    context = multiprocessing.get_context("spawn")
    started = context.Event()
    release = context.Event()
    process = context.Process(target=_hold_child, args=(started, release))
    process.start()
    assert started.wait(timeout=5)

    try:
        assert process in multiprocessing.active_children()
        assert multiprocessing.parent_process() is None
    finally:
        release.set()
        process.join(timeout=5)

    assert process not in multiprocessing.active_children()
    process.close()


def test_cpu_count_is_machine_capacity_not_current_affinity_limit():
    """Linux affinity 可能由 container/cgroup 限制；调度 worker 数应考虑实际可用 CPU。"""

    count = multiprocessing.cpu_count()

    assert isinstance(count, int)
    assert count >= 1
    if hasattr(os, "sched_getaffinity"):
        assert len(os.sched_getaffinity(0)) <= count


def test_daemonic_process_cannot_create_child_processes():
    """parent exit 会尝试终止 daemon children，因此禁止它们再产生无法可靠清理的 descendants。"""

    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe()
    process = context.Process(
        target=_daemon_attempts_child,
        args=(child_connection,),
        daemon=True,
    )

    process.start()
    child_connection.close()
    assert parent_connection.poll(timeout=5)
    message = parent_connection.recv()
    process.join(timeout=5)

    assert "daemonic processes are not allowed to have children" in message
    assert process.exitcode == 0
    parent_connection.close()
    process.close()


def test_log_to_stderr_adds_process_formatter_without_leaking_handler():
    """child interpreter 隔离 process-global logger 与 spawn logging flag。"""

    code = """
import logging
import multiprocessing

logger = multiprocessing.get_logger()
configured = multiprocessing.log_to_stderr(logging.WARNING)
configured.warning("teaching warning")
print(configured is logger, logger.propagate)
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.stdout.strip() == "True 0"
    assert "[WARNING/MainProcess] teaching warning" in completed.stderr


def test_dummy_pool_uses_threads_shares_pid_and_accepts_lambda():
    """没有 process serialization boundary；lambda 可执行，所有 worker 与 parent pid 相同。"""

    with multiprocessing.dummy.Pool(processes=2) as pool:
        assert isinstance(pool, multiprocessing.pool.ThreadPool)
        assert pool.map(lambda value: value * value, [1, 2, 3]) == [1, 4, 9]
        identities = pool.map(_thread_identity, ["a", "b", "c"])

    assert [value for value, _, _ in identities] == ["a", "b", "c"]
    assert {pid for _, pid, _ in identities} == {os.getpid()}
