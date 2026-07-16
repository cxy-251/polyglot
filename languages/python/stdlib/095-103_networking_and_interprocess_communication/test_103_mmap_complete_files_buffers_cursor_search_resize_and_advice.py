"""103｜文件映射的 READ、WRITE、COPY 三种访问语义。

三种映射都从文件读取初始字节：READ 禁止赋值，WRITE 的修改回写文件，COPY 使用 private
copy-on-write，映射内可见但不改变文件。length=0 在 Unix 表示映射调用时的整个非空文件。映射
buffered file 前必须先 flush，否则 Python 缓冲区中的数据可能尚未到达可映射的文件。

这些案例面向 Python 3.10 当前补丁系列。
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
import re
import os
import sys

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


# mmap 的可变字节序列与 buffer protocol。
#
# mmap 单索引像 bytearray 一样返回 int，切片返回 bytes；单字节赋值使用 0..255 的整数，切片赋值
# 不能改变映射长度。它同时导出可写 buffer，可直接交给 memoryview 和 re；只要仍有导出的 view，
# close 就会抛 BufferError，以防底层地址失效后留下悬空视图。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


# mmap 的 read/write、seek/tell 与逐行游标接口。
#
# 同一 mmap 既有随机索引，也维护独立的“当前位置”。read、readline、read_byte、write 和
# write_byte 都推进游标；切片访问不推进。write 不会自动扩容，越过映射末尾时整体失败并抛
# ValueError。混用两套接口时必须显式管理 seek，不能把索引位置误当成当前文件位置。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


# find/rfind 范围语义与 move 的重叠复制。
#
# find/rfind 使用与 bytes 切片一致的 start/end 范围，失败返回 -1；needle 可为 writable
# bytes-like object。move 在同一映射中复制固定数量字节，并按 memmove 语义正确处理源、目标重叠，
# 不同于用可能已被覆盖的数据逐字节手写循环。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.mmap.find
# polyglot-covers: python.mmap.find-start-end-slice-semantics
# polyglot-covers: python.mmap.find-not-found-minus-one
# polyglot-covers: python.mmap.find-writable-bytes-like-needle
# polyglot-covers: python.mmap.rfind
# polyglot-covers: python.mmap.move
# polyglot-covers: python.mmap.move-overlap-memmove-semantics
# polyglot-covers: python.mmap.move-readonly-typeerror




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


# offset 对齐、映射长度与底层文件大小。
#
# 非零 offset 必须是 ALLOCATIONGRANULARITY 的倍数；Unix 上它等于 PAGESIZE。len(mapping) 是窗口
# 长度，size() 则查询整个底层文件，两者在分段映射时不同。窗口中的索引从零开始，并不等于文件的
# 绝对偏移，分块处理大文件时要单独保留 base offset。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.mmap.offset
# polyglot-covers: python.mmap.offset-allocation-granularity-alignment
# polyglot-covers: python.mmap.ALLOCATIONGRANULARITY
# polyglot-covers: python.mmap.PAGESIZE
# polyglot-covers: python.mmap.unix-allocation-granularity-equals-page-size
# polyglot-covers: python.mmap.mapping-window-relative-index
# polyglot-covers: python.mmap.mapping-length
# polyglot-covers: python.mmap.size
# polyglot-covers: python.mmap.size-may-exceed-mapping-length




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


# flush 范围对齐、context manager 与文件所有权。
#
# WRITE/shared 映射修改的是文件页，但 flush 才请求把指定范围同步到 backing store；Python 3.8+
# 成功统一返回 None。范围 offset 必须按页或分配粒度对齐。关闭 mapping 不会关闭调用者传入的文件，
# 而关闭后再使用 mapping 会抛 ValueError；with 能明确管理这两层独立所有权。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.mmap.flush
# polyglot-covers: python.mmap.flush-success-none
# polyglot-covers: python.mmap.flush-offset-size
# polyglot-covers: python.mmap.flush-offset-page-aligned
# polyglot-covers: python.mmap.context-manager
# polyglot-covers: python.mmap.close
# polyglot-covers: python.mmap.closed
# polyglot-covers: python.mmap.close-does-not-close-file
# polyglot-covers: python.mmap.use-after-close-valueerror




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


# resize 同步改变映射与文件，以及 exported buffer 限制。
#
# 可写文件映射的 resize 同时改变映射窗口和底层文件；READ/COPY 映射禁止 resize。任何 memoryview
# 仍导出底层地址时也不能 resize，因为移动映射会让 view 悬空。正确顺序是 release 所有视图，再
# resize，最后重新取得新范围的 view。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.mmap.resize
# polyglot-covers: python.mmap.resize-updates-mapping-length
# polyglot-covers: python.mmap.resize-updates-underlying-file
# polyglot-covers: python.mmap.resize-readonly-typeerror
# polyglot-covers: python.mmap.resize-copy-on-write-typeerror
# polyglot-covers: python.mmap.resize-with-exported-buffer-buffererror
# polyglot-covers: python.mmap.release-view-before-resize




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


# 匿名映射、Unix flags/prot 与 access 参数互斥。
#
# fileno=-1 创建不依赖文件的零初始化匿名映射，适合共享内存缓冲区。Unix 还可用 MAP_SHARED/
# MAP_PRIVATE 与 PROT_READ/PROT_WRITE 精确描述映射；access 是跨平台的替代入口，不能同时再显式
# 提供 flags/prot。MAP_* 的完整集合由操作系统决定，使用附加 flag 前应 hasattr 探测。
#
# 这些案例面向 Python 3.10 当前补丁系列。

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


# madvise 向内核声明访问模式。
#
# madvise 是性能提示而不是读取正确性的前提：NORMAL、RANDOM、SEQUENTIAL 等只帮助内核选择
# readahead/回收策略，不改变字节内容。可用 MADV_* 集合由系统决定；带 start 的范围在 Linux 上
# 必须页对齐，因此分段提示也应以 PAGESIZE 为单位。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.mmap.madvise
# polyglot-covers: python.mmap.MADV_NORMAL
# polyglot-covers: python.mmap.MADV_RANDOM
# polyglot-covers: python.mmap.MADV_SEQUENTIAL
# polyglot-covers: python.mmap.madvise-whole-mapping
# polyglot-covers: python.mmap.madvise-start-length
# polyglot-covers: python.mmap.madvise-page-aligned-range
# polyglot-covers: python.mmap.platform-dependent-madv-constants
# polyglot-covers: python.mmap.madvise-is-performance-hint




REQUIRED = ("MADV_NORMAL", "MADV_RANDOM", "MADV_SEQUENTIAL")
_section_366_pytestmark = pytest.mark.skipif(
    not hasattr(mmap.mmap, "madvise") or any(not hasattr(mmap, name) for name in REQUIRED),
    reason="madvise 及其选项由操作系统提供",
)


@_section_366_pytestmark
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


@_section_366_pytestmark
def test_madv_constants_are_feature_detected_as_a_platform_set():
    options = {
        name: getattr(mmap, name)
        for name in dir(mmap)
        if name.startswith("MADV_")
    }
    assert {"MADV_NORMAL", "MADV_RANDOM", "MADV_SEQUENTIAL"} <= options.keys()
    assert all(isinstance(value, int) for value in options.values())
