"""170｜``FileIO`` raw ownership、BufferedWriter flush/detach 与 BufferedRandom。

``FileIO`` 每个 positive read/write 最多一次 syscall；``BufferedWriter`` 接受
全部 input 后可暂存在 userspace，直到 flush/close。``detach`` 转移底层 raw stream
所有权，原 buffer 随即不可用，caller 必须负责关闭返回对象。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.io.FileIO python.io.raw-file-io
# polyglot-covers: python.io.FileIO.mode python.io.FileIO.name
# polyglot-covers: python.io.FileIO.readinto python.io.fileio-fd-ownership
# polyglot-covers: python.io.BufferedWriter python.io.buffered-writer-flush
# polyglot-covers: python.io.BufferedIOBase.detach python.io.detached-buffer-unusable
# polyglot-covers: python.io.BufferedRandom python.io.buffered-random-read-write-seek
# polyglot-covers: python.io.BufferedRWPair python.io.buffered-rw-pair-separate-streams

import io
import os

import pytest


def test_fileio_wraps_path_or_existing_fd_and_closefd_controls_ownership(tmp_path):
    """path mode 会拥有新 fd；整数 fd 可用 closefd=False 保留给 caller。"""

    path = tmp_path / "raw.bin"
    with io.FileIO(path, "w+") as raw:
        assert raw.mode == "rb+"
        assert raw.name == path
        assert os.get_inheritable(raw.fileno()) is False
        assert raw.write(b"abcdef") == 6
        raw.seek(0)
        target = bytearray(4)
        assert raw.readinto(target) == 4
        assert target == b"abcd"

    fd = os.open(path, os.O_RDONLY)
    try:
        with io.FileIO(fd, "r", closefd=False) as borrowed:
            assert borrowed.name == fd
            assert borrowed.read(2) == b"ab"
        assert os.fstat(fd).st_size == 6
    finally:
        os.close(fd)


def test_buffered_writer_holds_small_write_until_flush(tmp_path):
    """返回 input length 只表示 buffer 接受，不表示 kernel 已观察 bytes。"""

    path = tmp_path / "buffered.bin"
    raw = io.FileIO(path, "w")
    writer = io.BufferedWriter(raw, buffer_size=16)
    try:
        assert writer.write(b"small") == 5
        assert os.fstat(raw.fileno()).st_size == 0
        assert writer.flush() is None
        assert os.fstat(raw.fileno()).st_size == 5
    finally:
        writer.close()

    assert raw.closed is True
    assert path.read_bytes() == b"small"


def test_detach_returns_raw_and_leaves_buffer_permanently_unusable(tmp_path):
    """detach 前先 flush；返回的 raw 不会随旧 wrapper 自动 close。"""

    path = tmp_path / "detached.bin"
    writer = io.BufferedWriter(io.FileIO(path, "w"), buffer_size=8)
    writer.write(b"data")
    writer.flush()
    raw = writer.detach()
    try:
        assert raw.closed is False
        with pytest.raises(ValueError):
            writer.write(b"unusable")
        raw.write(b"-raw")
    finally:
        raw.close()

    assert path.read_bytes() == b"data-raw"


def test_buffered_random_synchronizes_reads_writes_and_seek(tmp_path):
    """同一 seekable raw 既读又写时用 BufferedRandom，不用同对象构造 RWPair。"""

    path = tmp_path / "random.bin"
    with io.BufferedRandom(io.FileIO(path, "w+"), buffer_size=4) as stream:
        stream.write(b"abcdef")
        stream.seek(2)
        assert stream.read(2) == b"cd"
        stream.seek(2)
        stream.write(b"XY")
        stream.seek(0)
        assert stream.read() == b"abXYef"


def test_buffered_rw_pair_uses_distinct_reader_and_writer(tmp_path):
    """RWPair 不同步同一个 raw；这里明确提供 input/output 两个 stream。"""

    source = tmp_path / "source.bin"
    target = tmp_path / "target.bin"
    source.write_bytes(b"input")
    reader = io.FileIO(source, "r")
    writer = io.FileIO(target, "w")
    pair = io.BufferedRWPair(reader, writer, 4)
    try:
        assert pair.read(3) == b"inp"
        assert pair.write(b"out") == 3
        pair.flush()
    finally:
        pair.close()

    assert target.read_bytes() == b"out"
