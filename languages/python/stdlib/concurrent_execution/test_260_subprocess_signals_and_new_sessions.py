"""260｜POSIX 子进程信号、negative returncode 与新 session。

send_signal 发送指定信号；terminate/kill 在 POSIX 分别对应 SIGTERM/SIGKILL。由信号 N
终止时 returncode 为 -N，不是 shell 的 128+N。start_new_session=True 在 exec 前调用
setsid，常用于服务进程替代线程环境中不安全的 preexec_fn(os.setsid)。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.Popen.send_signal
# polyglot-covers: python.subprocess.Popen.terminate
# polyglot-covers: python.subprocess.Popen.kill
# polyglot-covers: python.subprocess.signal-negative-returncode
# polyglot-covers: python.subprocess.send-signal-finished-noop
# polyglot-covers: python.subprocess.start_new_session
# polyglot-covers: python.subprocess.preexec-fn-thread-deadlock-trap

import os
import select
import signal
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(os.name != "posix", reason="案例演示 POSIX signal/session")


def _blocking_child(*, start_new_session=False):
    source = (
        "import os, sys, threading; "
        "print(os.getpid(), os.getsid(0), os.getpgrp(), flush=True); "
        "threading.Event().wait()"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", source],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=start_new_session,
    )
    readable, _, _ = select.select([process.stdout], [], [], 2)
    if not readable:
        process.kill()
        process.wait()
        raise AssertionError("child did not report readiness")
    line = process.stdout.readline()
    try:
        identity = tuple(map(int, line.split()))
        if len(identity) != 3:
            raise ValueError("expected pid, session id and process group")
    except ValueError:
        if process.poll() is None:
            process.kill()
        process.wait()
        raise AssertionError(f"invalid child readiness record: {line!r}") from None
    return process, identity


def test_start_new_session_makes_child_its_session_and_process_group_leader():
    process, (pid, session_id, process_group) = _blocking_child(
        start_new_session=True
    )
    try:
        assert pid == process.pid
        assert session_id == process_group == process.pid

        process.terminate()
        assert process.wait(timeout=2) == -signal.SIGTERM
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_send_signal_and_kill_report_the_signal_as_negative_returncode():
    terminated, _ = _blocking_child()
    try:
        terminated.send_signal(signal.SIGTERM)
        assert terminated.wait(timeout=2) == -signal.SIGTERM
    finally:
        if terminated.poll() is None:
            terminated.kill()
            terminated.wait()

    killed, _ = _blocking_child()
    try:
        killed.kill()
        assert killed.wait(timeout=2) == -signal.SIGKILL
    finally:
        if killed.poll() is None:
            killed.kill()
            killed.wait()


def test_send_signal_is_a_noop_after_exit_has_been_observed():
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    assert process.wait(timeout=2) == 0

    assert process.send_signal(signal.SIGTERM) is None
    assert process.returncode == 0
