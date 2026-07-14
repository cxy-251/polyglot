"""365｜匿名映射、Unix flags/prot 与 access 参数互斥。

fileno=-1 创建不依赖文件的零初始化匿名映射，适合共享内存缓冲区。Unix 还可用 MAP_SHARED/
MAP_PRIVATE 与 PROT_READ/PROT_WRITE 精确描述映射；access 是跨平台的替代入口，不能同时再显式
提供 flags/prot。MAP_* 的完整集合由操作系统决定，使用附加 flag 前应 hasattr 探测。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.mmap.anonymous-mapping-fileno-minus-one
# polyglot-covers: python.mmap.anonymous-mapping-zero-initialized
# polyglot-covers: python.mmap.MAP_SHARED
# polyglot-covers: python.mmap.MAP_PRIVATE
# polyglot-covers: python.mmap.MAP_ANON
# polyglot-covers: python.mmap.MAP_ANONYMOUS
# polyglot-covers: python.mmap.MAP_POPULATE
# polyglot-covers: python.mmap.PROT_READ
# polyglot-covers: python.mmap.PROT_WRITE
# polyglot-covers: python.mmap.flags-prot-versus-access-mutually-exclusive
# polyglot-covers: python.mmap.platform-dependent-map-flags

import mmap
import sys

import pytest


def test_anonymous_mapping_is_zero_initialized_and_writable():
    with mmap.mmap(-1, 8) as mapped:
        assert mapped[:] == b"\0" * 8
        mapped[:4] = b"data"
        assert mapped[:] == b"data\0\0\0\0"


@pytest.mark.skipif(sys.platform == "win32", reason="flags/prot 是 Unix 构造参数")
def test_unix_flags_and_protection_create_an_explicit_shared_anonymous_map():
    with mmap.mmap(
        -1,
        mmap.PAGESIZE,
        flags=mmap.MAP_SHARED,
        prot=mmap.PROT_READ | mmap.PROT_WRITE,
    ) as mapped:
        mapped[:4] = b"unix"
        assert mapped[:4] == b"unix"

    with pytest.raises(ValueError):
        mmap.mmap(
            -1,
            mmap.PAGESIZE,
            flags=mmap.MAP_PRIVATE,
            prot=mmap.PROT_READ | mmap.PROT_WRITE,
            access=mmap.ACCESS_WRITE,
        )


def test_optional_map_constants_are_discovered_instead_of_assumed():
    assert mmap.MAP_SHARED != mmap.MAP_PRIVATE
    anonymous_names = [name for name in ("MAP_ANON", "MAP_ANONYMOUS") if hasattr(mmap, name)]
    if sys.platform != "win32":
        assert anonymous_names
    if sys.platform.startswith("linux"):
        # MAP_POPULATE 在 Python 3.10 的 Linux 构建中加入，但仍取决于系统 header。
        assert hasattr(mmap, "MAP_POPULATE")
