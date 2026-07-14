"""361｜find/rfind 范围语义与 move 的重叠复制。

find/rfind 使用与 bytes 切片一致的 start/end 范围，失败返回 -1；needle 可为 writable
bytes-like object。move 在同一映射中复制固定数量字节，并按 memmove 语义正确处理源、目标重叠，
不同于用可能已被覆盖的数据逐字节手写循环。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.find
# polyglot-covers: python.mmap.find-start-end-slice-semantics
# polyglot-covers: python.mmap.find-not-found-minus-one
# polyglot-covers: python.mmap.find-writable-bytes-like-needle
# polyglot-covers: python.mmap.rfind
# polyglot-covers: python.mmap.move
# polyglot-covers: python.mmap.move-overlap-memmove-semantics
# polyglot-covers: python.mmap.move-readonly-typeerror

import mmap

import pytest


def test_find_and_rfind_search_only_the_requested_slice_range():
    content = b"banana bandana"
    with mmap.mmap(-1, len(content)) as mapped:
        mapped[:] = content
        assert mapped.find(b"ana") == 1
        assert mapped.find(bytearray(b"ana"), 2) == 3
        assert mapped.find(b"ana", 4, 8) == -1
        assert mapped.rfind(b"ana") == 11
        assert mapped.rfind(b"ana", 0, 10) == 3
        assert mapped.find(b"missing") == -1


def test_move_uses_memmove_semantics_for_overlapping_regions():
    with mmap.mmap(-1, 6) as mapped:
        mapped[:] = b"abcdef"
        assert mapped.move(2, 0, 4) is None
        assert mapped[:] == b"ababcd"


def test_move_cannot_mutate_a_read_only_mapping(tmp_path):
    path = tmp_path / "readonly-move.bin"
    path.write_bytes(b"abcdef")
    with path.open("rb") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            with pytest.raises(TypeError):
                mapped.move(1, 0, 2)
