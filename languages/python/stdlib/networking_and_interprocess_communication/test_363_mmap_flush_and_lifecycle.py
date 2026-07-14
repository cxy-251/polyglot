"""363｜flush 范围对齐、context manager 与文件所有权。

WRITE/shared 映射修改的是文件页，但 flush 才请求把指定范围同步到 backing store；Python 3.8+
成功统一返回 None。范围 offset 必须按页或分配粒度对齐。关闭 mapping 不会关闭调用者传入的文件，
而关闭后再使用 mapping 会抛 ValueError；with 能明确管理这两层独立所有权。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.flush
# polyglot-covers: python.mmap.flush-success-none
# polyglot-covers: python.mmap.flush-offset-size
# polyglot-covers: python.mmap.flush-offset-page-aligned
# polyglot-covers: python.mmap.context-manager
# polyglot-covers: python.mmap.close
# polyglot-covers: python.mmap.closed
# polyglot-covers: python.mmap.close-does-not-close-file
# polyglot-covers: python.mmap.use-after-close-valueerror

import mmap

import pytest


def test_page_aligned_partial_flush_persists_a_selected_region(tmp_path):
    path = tmp_path / "flush.bin"
    path.write_bytes(b"\0" * (mmap.PAGESIZE * 2))

    with path.open("r+b") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_WRITE) as mapped:
            mapped[mmap.PAGESIZE : mmap.PAGESIZE + 4] = b"sync"
            assert mapped.flush(mmap.PAGESIZE, 4) is None
            with pytest.raises((OSError, ValueError)):
                mapped.flush(1, 1)
    assert path.read_bytes()[mmap.PAGESIZE : mmap.PAGESIZE + 4] == b"sync"


def test_mapping_and_file_have_independent_lifetimes(tmp_path):
    path = tmp_path / "lifecycle.bin"
    path.write_bytes(b"content")
    with path.open("r+b") as file:
        mapped = mmap.mmap(file.fileno(), 0)
        assert mapped.closed is False
        mapped.close()
        assert mapped.closed is True
        assert file.closed is False
        file.seek(0)
        assert file.read() == b"content"
        with pytest.raises(ValueError):
            mapped.read(1)


def test_context_manager_closes_the_mapping_on_exit():
    mapped = mmap.mmap(-1, 4)
    with mapped as entered:
        assert entered is mapped
        entered[:] = b"data"
    assert mapped.closed is True
