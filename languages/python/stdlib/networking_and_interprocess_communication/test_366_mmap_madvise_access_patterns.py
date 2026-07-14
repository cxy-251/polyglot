"""366｜madvise 向内核声明访问模式。

madvise 是性能提示而不是读取正确性的前提：NORMAL、RANDOM、SEQUENTIAL 等只帮助内核选择
readahead/回收策略，不改变字节内容。可用 MADV_* 集合由系统决定；带 start 的范围在 Linux 上
必须页对齐，因此分段提示也应以 PAGESIZE 为单位。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.madvise
# polyglot-covers: python.mmap.MADV_NORMAL
# polyglot-covers: python.mmap.MADV_RANDOM
# polyglot-covers: python.mmap.MADV_SEQUENTIAL
# polyglot-covers: python.mmap.madvise-whole-mapping
# polyglot-covers: python.mmap.madvise-start-length
# polyglot-covers: python.mmap.madvise-page-aligned-range
# polyglot-covers: python.mmap.platform-dependent-madv-constants
# polyglot-covers: python.mmap.madvise-is-performance-hint

import mmap

import pytest


REQUIRED = ("MADV_NORMAL", "MADV_RANDOM", "MADV_SEQUENTIAL")
pytestmark = pytest.mark.skipif(
    not hasattr(mmap.mmap, "madvise") or any(not hasattr(mmap, name) for name in REQUIRED),
    reason="madvise 及其选项由操作系统提供",
)


def test_madvise_accepts_whole_mapping_and_page_aligned_range_hints():
    with mmap.mmap(-1, mmap.PAGESIZE * 2) as mapped:
        mapped[:4] = b"data"
        assert mapped.madvise(mmap.MADV_NORMAL) is None
        assert mapped.madvise(mmap.MADV_RANDOM, 0, mmap.PAGESIZE) is None
        assert mapped.madvise(
            mmap.MADV_SEQUENTIAL,
            mmap.PAGESIZE,
            mmap.PAGESIZE,
        ) is None
        # advice 不应成为业务语义；三次提示都不改变已有字节。
        assert mapped[:4] == b"data"


def test_madv_constants_are_feature_detected_as_a_platform_set():
    options = {
        name: getattr(mmap, name)
        for name in dir(mmap)
        if name.startswith("MADV_")
    }
    assert {"MADV_NORMAL", "MADV_RANDOM", "MADV_SEQUENTIAL"} <= options.keys()
    assert all(isinstance(value, int) for value in options.values())
