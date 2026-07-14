"""364｜resize 同步改变映射与文件，以及 exported buffer 限制。

可写文件映射的 resize 同时改变映射窗口和底层文件；READ/COPY 映射禁止 resize。任何 memoryview
仍导出底层地址时也不能 resize，因为移动映射会让 view 悬空。正确顺序是 release 所有视图，再
resize，最后重新取得新范围的 view。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.resize
# polyglot-covers: python.mmap.resize-updates-mapping-length
# polyglot-covers: python.mmap.resize-updates-underlying-file
# polyglot-covers: python.mmap.resize-readonly-typeerror
# polyglot-covers: python.mmap.resize-copy-on-write-typeerror
# polyglot-covers: python.mmap.resize-with-exported-buffer-buffererror
# polyglot-covers: python.mmap.release-view-before-resize

import mmap

import pytest


def test_writable_file_mapping_resize_extends_both_mapping_and_file(tmp_path):
    path = tmp_path / "resize.bin"
    path.write_bytes(b"12345678")
    with path.open("r+b") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE) as mapped:
            assert mapped.resize(12) is None
            assert len(mapped) == 12
            assert mapped.size() == 12
            mapped[8:] = b"ABCD"
    assert path.read_bytes() == b"12345678ABCD"


@pytest.mark.parametrize("access", [mmap.ACCESS_READ, mmap.ACCESS_COPY])
def test_read_only_and_copy_on_write_mappings_cannot_resize(tmp_path, access):
    path = tmp_path / f"no-resize-{access}.bin"
    path.write_bytes(b"12345678")
    mode = "rb" if access == mmap.ACCESS_READ else "r+b"
    with path.open(mode) as file:
        with mmap.mmap(file.fileno(), 0, access=access) as mapped:
            with pytest.raises(TypeError):
                mapped.resize(12)


def test_exported_memoryview_must_be_released_before_resize(tmp_path):
    path = tmp_path / "exported.bin"
    path.write_bytes(b"12345678")
    with path.open("r+b") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE) as mapped:
            view = memoryview(mapped)
            try:
                with pytest.raises(BufferError):
                    mapped.resize(12)
            finally:
                view.release()
            mapped.resize(12)
            assert len(mapped) == 12
