"""163｜``posix_spawn`` file actions、legacy ``spawn*``、popen 与 system status。

``posix_spawn`` 可在启动 child 前安排 fd open/close/dup2，避免 Python child 分支。
旧 ``spawn*``、``popen`` 和 ``system`` 仍需理解，但新代码通常应使用
``subprocess``；尤其 shell string 会引入 quoting/injection 和平台差异。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.posix-spawn python.os.posix-spawn-file-actions
# polyglot-covers: python.os.POSIX_SPAWN_DUP2 python.os.POSIX_SPAWN_CLOSE
# polyglot-covers: python.os.posix-spawn-environment python.os.posix-spawn-waitpid
# polyglot-covers: python.os.spawnv python.os.P_WAIT
# polyglot-covers: python.os.spawnv-nowait python.os.P_NOWAIT
# polyglot-covers: python.os.popen python.os.popen-close-status
# polyglot-covers: python.os.system python.os.system-wait-status
# polyglot-covers: python.os.legacy-process-launcher-trap

import os
import sys

import pytest


def _read_all(fd):
    chunks = []
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


@pytest.mark.skipif(not hasattr(os, "posix_spawn"), reason="平台不提供 posix_spawn")
def test_posix_spawn_file_actions_redirect_stdout_without_python_child_code():
    """actions 在 exec 前执行；parent 仍须关闭 write end 才能读到 EOF。"""

    read_fd, write_fd = os.pipe()
    code = "import os; os.write(1, b'spawn-output')"
    actions = [
        (os.POSIX_SPAWN_DUP2, write_fd, 1),
        (os.POSIX_SPAWN_CLOSE, read_fd),
        (os.POSIX_SPAWN_CLOSE, write_fd),
    ]
    pid = os.posix_spawn(
        sys.executable,
        [sys.executable, "-c", code],
        os.environ.copy(),
        file_actions=actions,
    )

    os.close(write_fd)
    try:
        output = _read_all(read_fd)
    finally:
        os.close(read_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert output == b"spawn-output"
    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 0


@pytest.mark.skipif(not hasattr(os, "spawnv"), reason="平台不提供 legacy spawnv")
def test_spawnv_wait_returns_code_while_nowait_returns_pid():
    """P_WAIT 直接给 decoded code；P_NOWAIT 给 pid，caller 必须另行 wait。"""

    waited_code = os.spawnv(
        os.P_WAIT,
        sys.executable,
        [sys.executable, "-c", "raise SystemExit(6)"],
    )
    assert waited_code == 6

    pid = os.spawnv(
        os.P_NOWAIT,
        sys.executable,
        [sys.executable, "-c", "raise SystemExit(4)"],
    )
    waited_pid, status = os.waitpid(pid, 0)
    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 4


@pytest.mark.skipif(os.name != "posix", reason="本例依赖 POSIX shell 与 wait status")
def test_popen_and_system_expose_legacy_shell_status_conventions():
    """成功 popen close 返回 None；system 返回 encoded status，而非裸 code。"""

    stream = os.popen("printf polyglot", mode="r")
    assert stream.read() == "polyglot"
    assert stream.close() is None

    status = os.system("exit 7")
    assert os.WIFEXITED(status)
    assert os.waitstatus_to_exitcode(status) == 7
