"""360｜mmap 的 read/write、seek/tell 与逐行游标接口。

同一 mmap 既有随机索引，也维护独立的“当前位置”。read、readline、read_byte、write 和
write_byte 都推进游标；切片访问不推进。write 不会自动扩容，越过映射末尾时整体失败并抛
ValueError。混用两套接口时必须显式管理 seek，不能把索引位置误当成当前文件位置。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.write
# polyglot-covers: python.mmap.write-returns-byte-count
# polyglot-covers: python.mmap.read
# polyglot-covers: python.mmap.read-none-to-end
# polyglot-covers: python.mmap.read-negative-to-end
# polyglot-covers: python.mmap.readline
# polyglot-covers: python.mmap.read_byte
# polyglot-covers: python.mmap.write_byte
# polyglot-covers: python.mmap.seek
# polyglot-covers: python.mmap.seek-set-cur-end
# polyglot-covers: python.mmap.tell
# polyglot-covers: python.mmap.cursor-independent-from-slicing
# polyglot-covers: python.mmap.write-past-end-valueerror
# polyglot-covers: python.mmap.read-byte-at-end-valueerror

import mmap
import os

import pytest


def test_file_like_reads_writes_and_seeks_share_one_cursor():
    data = b"one\ntwo\n"
    with mmap.mmap(-1, len(data)) as mapped:
        assert mapped.write(data) == len(data)
        assert mapped.tell() == len(data)

        mapped.seek(0)
        assert mapped.read(3) == b"one"
        assert mapped.read_byte() == ord("\n")
        assert mapped.tell() == 4
        assert mapped[:] == data
        assert mapped.tell() == 4  # 切片没有改变 cursor。

        assert mapped.readline() == b"two\n"
        mapped.seek(-4, os.SEEK_END)
        assert mapped.read(None) == b"two\n"
        mapped.seek(-4, os.SEEK_CUR)
        assert mapped.read(-1) == b"two\n"

        mapped.seek(0, os.SEEK_SET)
        mapped.write_byte(ord("O"))
        assert mapped.tell() == 1
        assert mapped[:4] == b"One\n"


def test_cursor_operations_cannot_cross_the_fixed_mapping_end():
    with mmap.mmap(-1, 4) as mapped:
        mapped.seek(3)
        with pytest.raises(ValueError):
            mapped.write(b"XY")
        mapped.seek(4)
        with pytest.raises(ValueError):
            mapped.read_byte()
