"""359｜mmap 的可变字节序列与 buffer protocol。

mmap 单索引像 bytearray 一样返回 int，切片返回 bytes；单字节赋值使用 0..255 的整数，切片赋值
不能改变映射长度。它同时导出可写 buffer，可直接交给 memoryview 和 re；只要仍有导出的 view，
close 就会抛 BufferError，以防底层地址失效后留下悬空视图。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.bytearray-like-indexing
# polyglot-covers: python.mmap.index-returns-int
# polyglot-covers: python.mmap.slice-returns-bytes
# polyglot-covers: python.mmap.single-byte-assignment-int
# polyglot-covers: python.mmap.slice-assignment-fixed-size
# polyglot-covers: python.mmap.slice-assignment-size-trap
# polyglot-covers: python.mmap.buffer-protocol
# polyglot-covers: python.mmap.memoryview-write-through
# polyglot-covers: python.mmap.re-bytes-like-search
# polyglot-covers: python.mmap.close-with-exported-buffer-buffererror
# polyglot-covers: python.mmap.memoryview-release-before-close

import mmap
import re

import pytest


def test_index_slice_and_assignment_follow_mutable_byte_sequence_rules():
    with mmap.mmap(-1, 8) as mapped:
        mapped[:] = b"abcdefgh"
        assert mapped[0] == ord("a")
        assert mapped[-1] == ord("h")
        assert mapped[1:4] == b"bcd"

        mapped[0] = ord("A")
        mapped[1:4] = b"BCD"
        assert mapped[:] == b"ABCDefgh"
        with pytest.raises(IndexError, match="wrong size"):
            mapped[1:4] = b"too long"


def test_memoryview_and_regular_expression_operate_on_the_mapping_without_copy():
    mapped = mmap.mmap(-1, 16)
    mapped[:] = b"id=0042;done=yes"
    view = memoryview(mapped)
    try:
        view[3:7] = b"9001"
        assert mapped[:] == b"id=9001;done=yes"
        match = re.search(rb"id=(\d+)", mapped)
        assert match is not None
        assert match.group(1) == b"9001"

        with pytest.raises(BufferError):
            mapped.close()
        assert mapped.closed is False
    finally:
        view.release()
        mapped.close()
    assert mapped.closed is True
