"""164｜``kill`` signal status、``waitid`` peek、``wait4`` 与 Linux pidfd。

signal termination 的 wait status 与正常 exit 不同；先用 ``WIFSIGNALED`` 再读
``WTERMSIG``。``WNOWAIT`` 可以观察 child 而不 reap，pidfd 则用稳定 descriptor 引用
process，避免 PID reuse race。案例用 pipe handshake，不依赖 sleep。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.kill python.os.WIFSIGNALED
# polyglot-covers: python.os.WTERMSIG python.os.signal-negative-exitcode
# polyglot-covers: python.os.waitid python.os.P_PID
# polyglot-covers: python.os.WEXITED python.os.WNOWAIT python.os.CLD_EXITED
# polyglot-covers: python.os.wait4 python.os.wait4-resource-usage
# polyglot-covers: python.os.pidfd-open python.os.pidfd-non-inheritable

import os
import signal

import pytest


def _fork_blocked_child():
    ready_read, ready_write = os.pipe()
    block_read, block_write = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(ready_read)
        os.close(block_write)
        os.write(ready_write, b"R")
        os.close(ready_write)
        os.read(block_read, 1)
        os.close(block_read)
        os._exit(0)

    os.close(ready_write)
    os.close(block_read)
    assert os.read(ready_read, 1) == b"R"
    os.close(ready_read)
    return pid, block_write


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork")
def test_kill_termination_is_decoded_as_negative_signal_exit_code():
    """pipe handshake 证明 child 已启动；SIGTERM 后 parent 负责 waitpid 回收。"""

    pid, unblock_fd = _fork_blocked_child()
    try:
        os.kill(pid, signal.SIGTERM)
    finally:
        os.close(unblock_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert waited_pid == pid
    assert os.WIFSIGNALED(status) is True
    assert os.WTERMSIG(status) == signal.SIGTERM
    assert os.waitstatus_to_exitcode(status) == -signal.SIGTERM


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("fork", "waitid", "WNOWAIT")),
    reason="平台不提供 waitid WNOWAIT",
)
def test_waitid_wnowait_observes_child_then_waitpid_reaps_it():
    """siginfo 是 named result；WNOWAIT 留下 waitable status 供随后 waitpid 消费。"""

    pid = os.fork()
    if pid == 0:
        os._exit(9)

    info = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
    waited_pid, status = os.waitpid(pid, 0)

    assert info.si_pid == pid
    assert info.si_code == os.CLD_EXITED
    assert info.si_status == 9
    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 9


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("fork", "wait4")),
    reason="平台不提供 wait4",
)
def test_wait4_returns_wait_status_and_child_resource_usage():
    """rusage 与 encoded status 分开返回；不要把三元组第二项当裸 code。"""

    pid = os.fork()
    if pid == 0:
        os._exit(3)

    waited_pid, status, usage = os.wait4(pid, 0)

    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 3
    assert usage.ru_utime >= 0
    assert usage.ru_stime >= 0


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("fork", "pidfd_open")),
    reason="kernel/Python 不提供 pidfd",
)
def test_pidfd_open_returns_non_inheritable_process_descriptor():
    """pidfd 稳定引用特定 process；flags 在 3.10 必须为零。"""

    pid, unblock_fd = _fork_blocked_child()
    process_fd = None
    try:
        try:
            process_fd = os.pidfd_open(pid, 0)
        except OSError as error:
            pytest.skip(f"running kernel 不支持 pidfd_open: {error}")
        assert os.get_inheritable(process_fd) is False
    finally:
        if process_fd is not None:
            os.close(process_fd)
        os.close(unblock_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 0
