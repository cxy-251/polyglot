"""358｜文件映射的 READ、WRITE、COPY 三种访问语义。

三种映射都从文件读取初始字节：READ 禁止赋值，WRITE 的修改回写文件，COPY 使用 private
copy-on-write，映射内可见但不改变文件。length=0 在 Unix 表示映射调用时的整个非空文件。映射
buffered file 前必须先 flush，否则 Python 缓冲区中的数据可能尚未到达可映射的文件。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.mmap-file-backed
# polyglot-covers: python.mmap.length-zero-whole-file
# polyglot-covers: python.mmap.ACCESS_READ
# polyglot-covers: python.mmap.access-read-assignment-typeerror
# polyglot-covers: python.mmap.ACCESS_WRITE
# polyglot-covers: python.mmap.access-write-updates-file
# polyglot-covers: python.mmap.ACCESS_COPY
# polyglot-covers: python.mmap.access-copy-private-changes
# polyglot-covers: python.mmap.flush-buffered-file-before-mapping

import mmap

import pytest


def test_read_only_mapping_reads_the_whole_file_but_rejects_assignment(tmp_path):
    path = tmp_path / "readonly.bin"
    path.write_bytes(b"abcdefgh")

    with path.open("rb") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            assert len(mapped) == 8
            assert mapped[:] == b"abcdefgh"
            with pytest.raises(TypeError):
                mapped[0] = ord("A")


def test_write_through_and_copy_on_write_have_different_file_effects(tmp_path):
    write_path = tmp_path / "write.bin"
    copy_path = tmp_path / "copy.bin"
    write_path.write_bytes(b"abcdefgh")
    copy_path.write_bytes(b"abcdefgh")

    with write_path.open("r+b") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE) as mapped:
            mapped[:4] = b"WXYZ"
            assert mapped.flush() is None
    assert write_path.read_bytes() == b"WXYZefgh"

    with copy_path.open("r+b") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_COPY) as mapped:
            mapped[:4] = b"COPY"
            assert mapped[:] == b"COPYefgh"
            mapped.flush()
    assert copy_path.read_bytes() == b"abcdefgh"


def test_buffered_file_is_flushed_before_mapping_its_current_contents(tmp_path):
    path = tmp_path / "buffered.bin"
    with path.open("w+b") as file:
        file.write(b"visible after flush")
        # flush 是建立“Python buffer -> OS file -> mapping”可见性的必要工作流。
        file.flush()
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
            assert mapped[:] == b"visible after flush"
