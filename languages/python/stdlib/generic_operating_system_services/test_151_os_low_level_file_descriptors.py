"""151｜``os.open/read/write/lseek``、fdopen、fstat、truncate 与 buffering 边界。

file descriptor 是无 buffering 的小整数 handle；``os`` 的低层 API 只收发 bytes。
Python file object 另有 userspace buffer，混用前必须 flush/seek。``fdopen`` 可把现有 fd
包装成 file object，并由 ``closefd`` 决定 wrapper 是否取得 descriptor ownership。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.open python.os.open-flags
# polyglot-covers: python.os.O_CREAT python.os.O_EXCL
# polyglot-covers: python.os.O_TRUNC python.os.O_APPEND
# polyglot-covers: python.os.read python.os.write
# polyglot-covers: python.os.lseek python.os.SEEK_SET
# polyglot-covers: python.os.SEEK_CUR python.os.SEEK_END
# polyglot-covers: python.os.close python.os.fdopen
# polyglot-covers: python.os.fdopen-ownership python.os.closefd
# polyglot-covers: python.os.fstat python.os.ftruncate
# polyglot-covers: python.os.fsync python.os.buffer-flush-before-fsync
# polyglot-covers: python.os.isatty python.os.device-encoding
# polyglot-covers: python.os.fchmod python.os.low-level-bytes
# polyglot-covers: python.os.closerange python.os.closerange-half-open

import os
import stat

import pytest


def test_open_flags_create_exclusively_then_append_without_truncating(tmp_path):
    """O_EXCL 防止 race-prone overwrite；O_APPEND 保证每次 write 定位到文件尾。"""

    path = tmp_path / "events.bin"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        assert os.write(fd, b"first") == 5
    finally:
        os.close(fd)

    with pytest.raises(FileExistsError):
        os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)

    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        assert os.write(fd, b"-second") == 7
    finally:
        os.close(fd)

    assert path.read_bytes() == b"first-second"


def test_read_write_and_lseek_share_a_byte_offset(tmp_path):
    """lseek 单位是 bytes；EOF 返回 b''，不是 None 或异常。"""

    path = tmp_path / "random-access.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        assert os.write(fd, b"abcdef") == 6
        assert os.lseek(fd, 0, os.SEEK_SET) == 0
        assert os.read(fd, 2) == b"ab"
        assert os.lseek(fd, 1, os.SEEK_CUR) == 3
        assert os.read(fd, 2) == b"de"
        assert os.lseek(fd, 0, os.SEEK_END) == 6
        assert os.read(fd, 10) == b""
    finally:
        os.close(fd)


def test_fstat_and_ftruncate_operate_without_re_resolving_a_path(tmp_path):
    """descriptor 仍指向已打开对象；ftruncate 缩短数据并反映在 fstat size。"""

    path = tmp_path / "truncate.bin"
    path.write_bytes(b"0123456789")
    fd = os.open(path, os.O_RDWR)
    try:
        assert os.fstat(fd).st_size == 10
        assert os.ftruncate(fd, 4) is None
        assert os.fstat(fd).st_size == 4
    finally:
        os.close(fd)

    assert path.read_bytes() == b"0123"


def test_fdopen_closefd_controls_descriptor_ownership(tmp_path):
    """默认 wrapper close 一并关闭 fd；closefd=False 由调用方继续负责 close。"""

    owned_path = tmp_path / "owned.bin"
    owned_fd = os.open(owned_path, os.O_WRONLY | os.O_CREAT, 0o600)
    with os.fdopen(owned_fd, "wb") as stream:
        stream.write(b"owned")
    with pytest.raises(OSError):
        os.close(owned_fd)

    borrowed_path = tmp_path / "borrowed.bin"
    borrowed_fd = os.open(borrowed_path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        with os.fdopen(borrowed_fd, "wb", closefd=False) as stream:
            stream.write(b"borrowed")
        assert os.write(borrowed_fd, b"-still-open") == 11
    finally:
        os.close(borrowed_fd)

    assert borrowed_path.read_bytes() == b"borrowed-still-open"


def test_buffered_file_must_flush_before_fstat_and_fsync_see_bytes(tmp_path):
    """write 可只改 userspace buffer；flush 后 kernel size 才可靠，再 fsync。"""

    path = tmp_path / "buffered.bin"
    with path.open("wb") as stream:
        stream.write(b"buffered payload")
        assert os.fstat(stream.fileno()).st_size == 0

        stream.flush()
        assert os.fstat(stream.fileno()).st_size == len(b"buffered payload")
        assert os.fsync(stream.fileno()) is None


def test_regular_file_is_not_a_tty_and_has_no_device_encoding(tmp_path):
    """device_encoding 只描述 terminal device；普通 binary file 返回 None。"""

    path = tmp_path / "plain.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        assert os.isatty(fd) is False
        assert os.device_encoding(fd) is None
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "fchmod"), reason="平台不支持 fchmod")
def test_fchmod_changes_mode_through_descriptor(tmp_path):
    """权限变化不重新查找 path；只比较 permission bits，忽略 file type bits。"""

    path = tmp_path / "mode.bin"
    path.write_bytes(b"data")
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fchmod(fd, 0o640)
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o640
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="用 child 隔离 closerange 的 fd 影响")
def test_closerange_closes_half_open_interval_and_ignores_invalid_fds(tmp_path):
    """child 隔离避免误关 pytest fd；upper bound 不包含在关闭区间。"""

    report_read, report_write = os.pipe()
    base = os.open(tmp_path / "range.bin", os.O_RDWR | os.O_CREAT, 0o600)
    first = os.dup(base)
    upper = os.dup(base)
    pid = os.fork()
    if pid == 0:
        os.close(report_read)
        os.closerange(base, upper)
        try:
            closed = all(
                _descriptor_is_closed(fd)
                for fd in (base, first)
            )
            upper_open = not _descriptor_is_closed(upper)
            os.write(report_write, b"ok" if closed and upper_open else b"bad")
        finally:
            os.close(upper)
            os.close(report_write)
        os._exit(0)

    os.close(report_write)
    try:
        report = os.read(report_read, 10)
    finally:
        os.close(report_read)
        os.close(upper)
        os.close(first)
        os.close(base)
        _, status = os.waitpid(pid, 0)

    assert report == b"ok"
    assert os.waitstatus_to_exitcode(status) == 0


def _descriptor_is_closed(fd):
    try:
        os.fstat(fd)
    except OSError:
        return True
    return False
