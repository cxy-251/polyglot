"""362｜offset 对齐、映射长度与底层文件大小。

非零 offset 必须是 ALLOCATIONGRANULARITY 的倍数；Unix 上它等于 PAGESIZE。len(mapping) 是窗口
长度，size() 则查询整个底层文件，两者在分段映射时不同。窗口中的索引从零开始，并不等于文件的
绝对偏移，分块处理大文件时要单独保留 base offset。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.offset
# polyglot-covers: python.mmap.offset-allocation-granularity-alignment
# polyglot-covers: python.mmap.ALLOCATIONGRANULARITY
# polyglot-covers: python.mmap.PAGESIZE
# polyglot-covers: python.mmap.unix-allocation-granularity-equals-page-size
# polyglot-covers: python.mmap.mapping-window-relative-index
# polyglot-covers: python.mmap.mapping-length
# polyglot-covers: python.mmap.size
# polyglot-covers: python.mmap.size-may-exceed-mapping-length

import mmap
import sys

import pytest


def test_aligned_offset_maps_a_window_whose_size_differs_from_the_file(tmp_path):
    prefix = b"A" * mmap.ALLOCATIONGRANULARITY
    path = tmp_path / "window.bin"
    path.write_bytes(prefix + b"SECOND!!")

    with path.open("rb") as file:
        with mmap.mmap(
            file.fileno(),
            8,
            access=mmap.ACCESS_READ,
            offset=mmap.ALLOCATIONGRANULARITY,
        ) as mapped:
            assert len(mapped) == 8
            assert mapped[0] == ord("S")
            assert mapped[:] == b"SECOND!!"
            assert mapped.size() == mmap.ALLOCATIONGRANULARITY + 8


def test_unaligned_offset_is_rejected_and_unix_granularities_match(tmp_path):
    path = tmp_path / "unaligned.bin"
    path.write_bytes(b"x" * (mmap.ALLOCATIONGRANULARITY + 8))
    with path.open("rb") as file:
        with pytest.raises((OSError, ValueError)):
            mmap.mmap(file.fileno(), 4, access=mmap.ACCESS_READ, offset=1)

    if sys.platform != "win32":
        assert mmap.ALLOCATIONGRANULARITY == mmap.PAGESIZE
