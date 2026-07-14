"""161｜``fork``、child-only ``_exit``、``waitpid`` 与 nonblocking wait。

``fork`` 复制进程状态，并在 parent/child 返回不同值。child 分支必须尽快
进入明确路径；发生错误也要以 ``_exit`` 终止，避免继续跑 pytest runner。
parent 必须 reap child，否则会留下 zombie process。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.fork python.os.fork-parent-child-return
# polyglot-covers: python.os._exit python.os.child-exit-without-cleanup
# polyglot-covers: python.os.waitpid python.os.WIFEXITED
# polyglot-covers: python.os.WEXITSTATUS python.os.waitstatus-to-exitcode
# polyglot-covers: python.os.WNOHANG python.os.waitpid-nohang-zero
# polyglot-covers: python.os.fork-pipe-synchronization python.os.zombie-reaping

import os

import pytest


def _read_all(fd):
    chunks = []
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork")
def test_fork_child_writes_pipe_and_parent_decodes_wait_status():
    """pipe 传业务数据；wait status 是编码值，不能直接当 child exit code。"""

    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        try:
            os.write(write_fd, b"child-payload")
        finally:
            os.close(write_fd)
        os._exit(7)

    os.close(write_fd)
    try:
        payload = _read_all(read_fd)
    finally:
        os.close(read_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert payload == b"child-payload"
    assert waited_pid == pid
    assert os.WIFEXITED(status) is True
    assert os.WEXITSTATUS(status) == 7
    assert os.waitstatus_to_exitcode(status) == 7


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork")
def test_waitpid_wnohang_returns_zero_while_child_is_blocked_on_pipe():
    """(0, 0) 表示还没有可回收状态，不表示 pid=0 的 child 已完成。"""

    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(write_fd)
        try:
            os.read(read_fd, 1)
        finally:
            os.close(read_fd)
        os._exit(0)

    os.close(read_fd)
    try:
        assert os.waitpid(pid, os.WNOHANG) == (0, 0)
    finally:
        # EOF 解除 child 的阻塞，然后无条件 reap，避免断言失败时留下 zombie。
        os.close(write_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 0
