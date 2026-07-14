"""261｜POSIX ``close_fds``、``pass_fds``、child umask 与 Linux pipesize。

PEP 446 后新 fd 默认不可继承，Popen 又默认关闭 0/1/2 以外的描述符。pass_fds 是精确
白名单并强制 close_fds=True，避免把 secret/socket 意外泄漏给 child。umask 在 child
exec 前生效而不改 parent。Python 3.10 的 pipesize 可在 Linux 调整 PIPE 容量。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.Popen.close_fds
# polyglot-covers: python.subprocess.Popen.pass_fds
# polyglot-covers: python.subprocess.pass-fds-forces-close-fds
# polyglot-covers: python.subprocess.file-descriptor-leak-prevention
# polyglot-covers: python.subprocess.Popen.umask
# polyglot-covers: python.subprocess.child-umask-parent-isolation
# polyglot-covers: python.subprocess.Popen.pipesize

import fcntl
import os
import stat
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(os.name != "posix", reason="案例使用 POSIX file descriptors")


def test_pass_fds_explicitly_exposes_one_pipe_to_the_child():
    read_fd, write_fd = os.pipe()
    process = None
    os.write(write_fd, b"explicit capability")
    os.close(write_fd)
    command = [
        sys.executable,
        "-c",
        "import os, sys; os.write(1, os.read(int(sys.argv[1]), 1000))",
        str(read_fd),
    ]

    try:
        with pytest.warns(RuntimeWarning, match="pass_fds overriding close_fds"):
            process = subprocess.Popen(
                command,
                pass_fds=(read_fd,),
                close_fds=False,
                stdout=subprocess.PIPE,
            )
        os.close(read_fd)
        read_fd = None
        stdout, _ = process.communicate(timeout=2)
    finally:
        if read_fd is not None:
            os.close(read_fd)
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()

    assert process.returncode == 0
    assert stdout == b"explicit capability"


def test_close_fds_removes_even_an_inheritable_unlisted_descriptor(tmp_path):
    low_fd = os.open(tmp_path / "source.bin", os.O_CREAT | os.O_RDONLY, 0o600)
    high_fd = fcntl.fcntl(low_fd, fcntl.F_DUPFD, 200)
    os.close(low_fd)
    os.set_inheritable(high_fd, True)
    source = (
        "import os, sys; fd = int(sys.argv[1]); "
        "\ntry: os.fstat(fd)"
        "\nexcept OSError: print('closed')"
        "\nelse: print('open')"
    )

    try:
        completed = subprocess.run(
            [sys.executable, "-c", source, str(high_fd)],
            close_fds=True,
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        os.close(high_fd)

    assert completed.stdout == "closed\n"


def test_child_umask_controls_created_mode_without_changing_parent(tmp_path):
    result = tmp_path / "created-by-child.txt"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('data')",
            str(result),
        ],
        umask=0o077,
        check=True,
    )

    assert stat.S_IMODE(result.stat().st_mode) == 0o600


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or not hasattr(fcntl, "F_GETPIPE_SZ"),
    reason="pipesize introspection 仅在 Linux 提供",
)
def test_pipesize_requests_the_kernel_pipe_capacity():
    process = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdin.buffer.read()"],
        stdin=subprocess.PIPE,
        pipesize=4096,
    )
    try:
        assert fcntl.fcntl(process.stdin.fileno(), fcntl.F_GETPIPE_SZ) == 4096
        process.stdin.close()
        assert process.wait(timeout=2) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
