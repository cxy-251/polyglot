"""153｜``os.pread/pwrite``、readv/writev、preadv/pwritev 与 kernel-side copy。

positioned I/O 显式给 offset 且不改变 shared file cursor，适合并发读取固定区段。
vectored I/O 一次 syscall 处理多个 buffers，但返回值仍可能短于总长度。
``copy_file_range`` 和 ``splice`` 让 kernel 搬运数据；可用性还取决于 kernel 与当前
filesystem。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.pread python.os.pwrite
# polyglot-covers: python.os.positioned-io-offset python.os.positioned-io-shared-cursor
# polyglot-covers: python.os.readv python.os.writev
# polyglot-covers: python.os.vectored-buffer-order python.os.vectored-short-count
# polyglot-covers: python.os.preadv python.os.pwritev
# polyglot-covers: python.os.copy-file-range python.os.kernel-side-copy
# polyglot-covers: python.os.copy-file-range-short-copy python.os.splice
# polyglot-covers: python.os.splice-pipe python.os.platform-capability-guard

import errno
import os

import pytest


@pytest.mark.skipif(not hasattr(os, "pread"), reason="平台不支持 positioned I/O")
def test_pread_and_pwrite_leave_shared_cursor_unchanged(tmp_path):
    """offset 参数独立于 open description cursor；返回 count 仍应由调用方检查。"""

    path = tmp_path / "positioned.bin"
    path.write_bytes(b"0123456789")
    fd = os.open(path, os.O_RDWR)
    try:
        assert os.lseek(fd, 3, os.SEEK_SET) == 3
        assert os.pread(fd, 4, 5) == b"5678"
        assert os.lseek(fd, 0, os.SEEK_CUR) == 3

        assert os.pwrite(fd, b"AB", 0) == 2
        assert os.lseek(fd, 0, os.SEEK_CUR) == 3
    finally:
        os.close(fd)

    assert path.read_bytes() == b"AB23456789"


@pytest.mark.skipif(not hasattr(os, "writev"), reason="平台不支持 vectored I/O")
def test_writev_processes_buffers_in_order(tmp_path):
    """small regular-file write 通常一次完成；通用代码仍须消费实际 count。"""

    path = tmp_path / "writev.bin"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        written = os.writev(fd, [b"header:", memoryview(b"body"), b":tail"])
    finally:
        os.close(fd)

    assert written == len(b"header:body:tail")
    assert path.read_bytes() == b"header:body:tail"


@pytest.mark.skipif(not hasattr(os, "readv"), reason="平台不支持 vectored I/O")
def test_readv_fills_mutable_buffers_in_sequence_and_can_stop_partway():
    """总 capacity 大于输入时，末尾 buffer 只有 prefix 被覆盖。"""

    read_fd, write_fd = os.pipe()
    first = bytearray(2)
    second = bytearray(b"xxxxx")
    try:
        os.write(write_fd, b"abcdef")
        os.close(write_fd)
        write_fd = None

        count = os.readv(read_fd, [first, second])
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)

    assert count == 6
    assert first == b"ab"
    assert second == b"cdefx"


@pytest.mark.skipif(not hasattr(os, "preadv"), reason="平台不支持 positioned vectors")
def test_preadv_and_pwritev_combine_positioned_and_vectored_semantics(tmp_path):
    """多个 buffers 按序映射到显式 offset，且不会推进当前 cursor。"""

    path = tmp_path / "positioned-vectors.bin"
    path.write_bytes(b"0123456789")
    fd = os.open(path, os.O_RDWR)
    first = bytearray(2)
    second = bytearray(3)
    try:
        os.lseek(fd, 7, os.SEEK_SET)
        assert os.preadv(fd, [first, second], 2) == 5
        assert (first, second) == (b"23", b"456")
        assert os.lseek(fd, 0, os.SEEK_CUR) == 7

        assert os.pwritev(fd, [b"AB", b"CD"], 0) == 4
        assert os.lseek(fd, 0, os.SEEK_CUR) == 7
    finally:
        os.close(fd)

    assert path.read_bytes() == b"ABCD456789"


@pytest.mark.skipif(not hasattr(os, "copy_file_range"), reason="平台不支持 kernel copy")
def test_copy_file_range_loops_because_one_call_may_copy_less(tmp_path):
    """API 返回实际 count；filesystem 不实现 syscall 时按 capability skip。"""

    source_path = tmp_path / "source.bin"
    target_path = tmp_path / "target.bin"
    payload = b"kernel-copy" * 100
    source_path.write_bytes(payload)
    source = os.open(source_path, os.O_RDONLY)
    target = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        total = 0
        try:
            while total < len(payload):
                copied = os.copy_file_range(source, target, len(payload) - total)
                if copied == 0:
                    break
                total += copied
        except OSError as error:
            if error.errno in {errno.ENOSYS, errno.EXDEV, errno.EINVAL, errno.EOPNOTSUPP}:
                pytest.skip(f"filesystem 不支持 copy_file_range: {error}")
            raise
    finally:
        os.close(target)
        os.close(source)

    assert total == len(payload)
    assert target_path.read_bytes() == payload


@pytest.mark.skipif(not hasattr(os, "splice"), reason="平台不支持 splice")
def test_splice_moves_bytes_from_pipe_to_file_without_userspace_buffer(tmp_path):
    """至少一端必须是 pipe；关闭 writer 后 source 不会等待更多输入。"""

    read_fd, write_fd = os.pipe()
    target_path = tmp_path / "spliced.bin"
    target = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(write_fd, b"through-kernel")
        os.close(write_fd)
        write_fd = None

        assert os.splice(read_fd, target, len(b"through-kernel")) == len(
            b"through-kernel"
        )
    finally:
        os.close(target)
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)

    assert target_path.read_bytes() == b"through-kernel"
