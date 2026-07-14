"""152｜``os.pipe``、dup/dup2、shared offset、blocking mode 与 inheritable flag。

pipe 是单向 byte stream；关闭所有 write ends 后 reader 才观察 EOF。``dup`` 产生新的
fd，但两个 fd 指向同一个 open file description，所以共享 cursor。Python 3.4+
创建的 fd 默认不可继承；若确需跨 exec 继承，必须显式设置并及时恢复。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.pipe python.os.pipe-eof
# polyglot-covers: python.os.pipe-non-inheritable python.os.dup
# polyglot-covers: python.os.dup-shared-offset python.os.dup-non-inheritable
# polyglot-covers: python.os.dup2 python.os.dup2-return-fd
# polyglot-covers: python.os.get-inheritable python.os.set-inheritable
# polyglot-covers: python.os.fd-inheritance python.os.get-blocking
# polyglot-covers: python.os.set-blocking python.os.nonblocking-read
# polyglot-covers: python.os.pipe2 python.os.O_NONBLOCK
# polyglot-covers: python.os.O_CLOEXEC python.os.openpty
# polyglot-covers: python.os.ttyname python.os.terminal-size
# polyglot-covers: python.os.get-terminal-size python.os.non-tty-error

import os

import pytest


def test_pipe_transfers_bytes_and_close_of_writer_produces_eof():
    """read end 不知道消息边界；关闭 write end 后，第二次 read 得到 EOF。"""

    read_fd, write_fd = os.pipe()
    try:
        assert os.get_inheritable(read_fd) is False
        assert os.get_inheritable(write_fd) is False
        assert os.write(write_fd, b"pipe payload") == len(b"pipe payload")
        os.close(write_fd)
        write_fd = None

        assert os.read(read_fd, 100) == b"pipe payload"
        assert os.read(read_fd, 1) == b""
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)


def test_dup_descriptors_share_the_same_open_file_offset(tmp_path):
    """dup 不 clone kernel cursor；任一 fd read 都推进 shared offset。"""

    path = tmp_path / "shared-offset.bin"
    path.write_bytes(b"abcdef")
    original = os.open(path, os.O_RDONLY)
    duplicate = os.dup(original)
    try:
        assert duplicate != original
        assert os.get_inheritable(duplicate) is False
        assert os.read(original, 2) == b"ab"
        assert os.read(duplicate, 2) == b"cd"
    finally:
        os.close(duplicate)
        os.close(original)


def test_dup2_retargets_an_existing_fd_and_controls_inheritability(tmp_path):
    """dup2 先关闭 target 所指对象，再令该 fd 指向 source open description。"""

    source_path = tmp_path / "source.bin"
    target_path = tmp_path / "target.bin"
    source_path.write_bytes(b"source")
    target_path.write_bytes(b"target")
    source = os.open(source_path, os.O_RDONLY)
    target = os.open(target_path, os.O_RDONLY)
    try:
        assert os.dup2(source, target, inheritable=False) == target
        assert os.get_inheritable(target) is False
        assert os.read(target, 6) == b"source"
    finally:
        os.close(target)
        os.close(source)


def test_inheritable_flag_can_be_toggled_and_restored(tmp_path):
    """flag 只影响 future child exec；它不会自动把 fd 内容复制到 child。"""

    fd = os.open(tmp_path / "inherit.bin", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        assert os.get_inheritable(fd) is False
        os.set_inheritable(fd, True)
        assert os.get_inheritable(fd) is True
        os.set_inheritable(fd, False)
        assert os.get_inheritable(fd) is False
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "set_blocking"), reason="平台不支持 fd blocking flag")
def test_nonblocking_empty_pipe_raises_instead_of_waiting():
    """writer 打开时 empty pipe 不是 EOF；nonblocking read 会表示 would-block。"""

    read_fd, write_fd = os.pipe()
    try:
        assert os.get_blocking(read_fd) is True
        os.set_blocking(read_fd, False)
        assert os.get_blocking(read_fd) is False
        with pytest.raises(BlockingIOError):
            os.read(read_fd, 1)

        os.set_blocking(read_fd, True)
        assert os.get_blocking(read_fd) is True
    finally:
        os.close(write_fd)
        os.close(read_fd)


@pytest.mark.skipif(not hasattr(os, "pipe2"), reason="平台不支持 atomic pipe flags")
def test_pipe2_applies_nonblocking_and_close_on_exec_atomically():
    """O_NONBLOCK 与 O_CLOEXEC 在 fd 暴露给其他 threads 前由 kernel 一次设置。"""

    read_fd, write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        assert os.get_blocking(read_fd) is False
        assert os.get_blocking(write_fd) is False
        assert os.get_inheritable(read_fd) is False
        assert os.get_inheritable(write_fd) is False
    finally:
        os.close(write_fd)
        os.close(read_fd)


@pytest.mark.skipif(not hasattr(os, "openpty"), reason="平台不支持 pseudo-terminal")
def test_openpty_returns_non_inheritable_tty_descriptors():
    """slave 是 tty device，master/slave 均遵循 Python 的 non-inheritable default。"""

    master, slave = os.openpty()
    try:
        assert os.isatty(slave) is True
        assert os.ttyname(slave)
        assert os.get_inheritable(master) is False
        assert os.get_inheritable(slave) is False
    finally:
        os.close(slave)
        os.close(master)


def test_terminal_size_is_named_tuple_and_regular_file_query_fails(tmp_path):
    """low-level query 需要 tty；shutil.get_terminal_size 才提供 environment/fallback。"""

    size = os.terminal_size((80, 24))
    assert tuple(size) == (80, 24)
    assert size.columns == 80
    assert size.lines == 24

    fd = os.open(tmp_path / "not-a-terminal", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with pytest.raises(OSError):
            os.get_terminal_size(fd)
    finally:
        os.close(fd)
