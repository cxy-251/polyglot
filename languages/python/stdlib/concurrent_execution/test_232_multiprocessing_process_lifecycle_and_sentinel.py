"""232｜``multiprocessing.Process`` lifecycle、child identity、sentinel 与 close。

Process 与 Thread API 相似，但 target 在独立 interpreter/process 中运行，参数必须适合
所选 start method。pid/sentinel 在 start 后可用，exitcode 在结束前为 None；``join`` 仍
总返回 None。``close`` 释放 parent 侧 Process resources，不能用于仍存活的 child。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Process
# polyglot-covers: python.multiprocessing.Process-target-args-kwargs
# polyglot-covers: python.multiprocessing.Process.start
# polyglot-covers: python.multiprocessing.Process.join
# polyglot-covers: python.multiprocessing.Process.is_alive
# polyglot-covers: python.multiprocessing.Process.name
# polyglot-covers: python.multiprocessing.Process.pid
# polyglot-covers: python.multiprocessing.Process.exitcode
# polyglot-covers: python.multiprocessing.Process.authkey
# polyglot-covers: python.multiprocessing.Process.sentinel
# polyglot-covers: python.multiprocessing.connection.wait-process-sentinel
# polyglot-covers: python.multiprocessing.current_process
# polyglot-covers: python.multiprocessing.parent_process
# polyglot-covers: python.multiprocessing.Process-close-live-error
# polyglot-covers: python.multiprocessing.Process.close
# polyglot-covers: python.multiprocessing.Process-subclass-run

import multiprocessing
import multiprocessing.connection
import os

import pytest


def _report_process_state(connection, started, release, value, *, multiplier):
    process = multiprocessing.current_process()
    parent = multiprocessing.parent_process()
    started.set()
    if not release.wait(timeout=5):
        raise RuntimeError("parent did not release child")
    connection.send(
        {
            "result": value * multiplier,
            "name": process.name,
            "pid": os.getpid(),
            "parent_pid": parent.pid,
            "daemon": process.daemon,
        }
    )
    connection.close()


class _DoublingProcess(multiprocessing.Process):
    def __init__(self, connection, value):
        super().__init__(name="doubling-process")
        self.connection = connection
        self.value = value

    def run(self):
        self.connection.send(self.value * 2)
        self.connection.close()


def _do_nothing():
    return None


def test_spawn_process_reports_identity_and_sentinel_becomes_ready_on_exit():
    """显式 spawn 证明 target/arguments 可序列化，不依赖 Linux 默认 fork memory snapshot。"""

    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=True)
    started = context.Event()
    release = context.Event()
    process = context.Process(
        target=_report_process_state,
        args=(child_connection, started, release, 6),
        kwargs={"multiplier": 7},
        name="spawned-answer-worker",
    )

    assert process.pid is None
    assert process.exitcode is None
    assert process.is_alive() is False
    assert process.authkey == multiprocessing.current_process().authkey

    process.start()
    child_connection.close()
    assert started.wait(timeout=5)

    try:
        assert process.is_alive() is True
        assert isinstance(process.pid, int)
        assert process.exitcode is None
        assert multiprocessing.connection.wait([process.sentinel], timeout=0) == []

        release.set()
        ready = multiprocessing.connection.wait([process.sentinel], timeout=5)
        assert ready == [process.sentinel]
        assert process.join(timeout=5) is None

        report = parent_connection.recv()
        assert report == {
            "result": 42,
            "name": "spawned-answer-worker",
            "pid": process.pid,
            "parent_pid": os.getpid(),
            "daemon": False,
        }
        assert process.exitcode == 0
        assert process.is_alive() is False
    finally:
        release.set()
        process.join(timeout=5)
        parent_connection.close()
        process.close()


def test_process_start_once_and_join_before_start_are_lifecycle_errors():
    """Process object 与 native process 一一对应；再次执行应创建新 instance。"""

    process = multiprocessing.Process(target=_do_nothing)

    with pytest.raises(AssertionError, match="can only join a started process"):
        process.join()

    process.start()
    process.join()
    with pytest.raises(AssertionError, match="cannot start a process twice"):
        process.start()
    process.close()


def test_close_rejects_live_process_and_invalidates_finished_process_object():
    """close 不是 terminate；必须先建立 child 已结束的同步边界。"""

    context = multiprocessing.get_context()
    started = context.Event()
    release = context.Event()
    process = context.Process(
        target=_wait_for_release,
        args=(started, release),
    )
    process.start()
    assert started.wait(timeout=5)

    with pytest.raises(ValueError, match="Cannot close a process while it is still running"):
        process.close()

    release.set()
    process.join(timeout=5)
    assert process.exitcode == 0
    process.close()

    with pytest.raises(ValueError, match="process object is closed"):
        process.is_alive()


def _wait_for_release(started, release):
    started.set()
    if not release.wait(timeout=5):
        raise RuntimeError("release event timed out")


def test_process_subclass_overrides_run_and_uses_normal_lifecycle():
    """与 Thread 相同，只覆盖 __init__/run，并先调用 Process.__init__。"""

    parent_connection, child_connection = multiprocessing.Pipe()
    process = _DoublingProcess(child_connection, 21)

    process.start()
    child_connection.close()
    process.join(timeout=5)

    assert parent_connection.recv() == 42
    assert process.name == "doubling-process"
    assert process.exitcode == 0
    parent_connection.close()
    process.close()
