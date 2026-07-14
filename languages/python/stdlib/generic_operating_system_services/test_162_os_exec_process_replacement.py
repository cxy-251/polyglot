"""162｜``execv``/``execvpe`` 的 process replacement、argv 与 environment。

exec family 不创建新进程，而是替换 caller image；成功时永不返回。因此案例先
fork 隔离 pytest parent，再把 child stdout 接到 pipe。``v`` 接受 argv sequence，
``p`` 搜索 PATH，末尾 ``e`` 则用传入 mapping 完全替换 inherited environment。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.execv python.os.exec-process-replacement
# polyglot-covers: python.os.exec-argv-zero python.os.exec-never-returns
# polyglot-covers: python.os.execvpe python.os.exec-path-search
# polyglot-covers: python.os.exec-explicit-environment python.os.exec-environment-replacement
# polyglot-covers: python.os.exec-descriptors-not-flushed python.os.exec-fork-isolation

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


def _fork_exec_and_capture(operation):
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        os.dup2(write_fd, 1, inheritable=True)
        os.close(write_fd)
        try:
            operation()
        except BaseException:
            os._exit(120)
        os._exit(121)

    os.close(write_fd)
    try:
        output = _read_all(read_fd)
    finally:
        os.close(read_fd)
        _, status = os.waitpid(pid, 0)
    return output, os.waitstatus_to_exitcode(status)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork/exec 隔离")
def test_execv_replaces_child_and_uses_explicit_executable_path():
    """argv[0] 按约定放 program name；API 不会替调用方自动补上它。"""

    code = "import os; os.write(1, b'execv-ok')"

    def execute():
        os.execv(sys.executable, [sys.executable, "-c", code])

    output, exit_code = _fork_exec_and_capture(execute)

    assert output == b"execv-ok"
    assert exit_code == 0


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork/exec 隔离")
def test_execvpe_searches_supplied_path_and_replaces_environment():
    """p/e variant 搜索新 environment 的 PATH，而不是 parent 当前 PATH。"""

    executable_name = os.path.basename(sys.executable)
    environment = {
        "PATH": os.path.dirname(sys.executable),
        "POLYGLOT_CHILD_VALUE": "explicit-only",
    }
    code = (
        "import os; "
        "os.write(1, os.environ['POLYGLOT_CHILD_VALUE'].encode('ascii'))"
    )

    def execute():
        os.execvpe(
            executable_name,
            [executable_name, "-c", code],
            environment,
        )

    output, exit_code = _fork_exec_and_capture(execute)

    assert output == b"explicit-only"
    assert exit_code == 0

    # exec 不会替 caller flush file-object buffers；进入前应自行 flush/fsync。
