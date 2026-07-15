"""071｜``tarfile.open`` 模式、透明压缩、fileobj ownership 与流式归档。

普通 ``:`` 模式提供随机访问，``r:*`` 自动探测 gzip/bz2/xz；``|`` 模式则只顺序处理
blocks，可连接 pipe、socket 或 tape-like 对象。append 只适用于未压缩 TAR，caller 提供的
fileobj 不由 TarFile 关闭。模式字符串决定格式，不能只依赖文件扩展名。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tarfile.open python.tarfile.path-like
# polyglot-covers: python.tarfile.mode-r-auto python.tarfile.mode-r-uncompressed
# polyglot-covers: python.tarfile.mode-gz python.tarfile.mode-bz2 python.tarfile.mode-xz
# polyglot-covers: python.tarfile.compresslevel python.tarfile.preset
# polyglot-covers: python.tarfile.mode-w python.tarfile.mode-a python.tarfile.mode-x
# polyglot-covers: python.tarfile.no-compressed-append python.tarfile.ReadError
# polyglot-covers: python.tarfile.CompressionError python.tarfile.is_tarfile
# polyglot-covers: python.tarfile.fileobj-not-closed python.tarfile.context-manager
# polyglot-covers: python.tarfile.stream-read python.tarfile.stream-write
# polyglot-covers: python.tarfile.non-seekable python.tarfile.StreamError




import io
import tarfile
import pytest
import os
import copy
import stat
import subprocess
import sys

class _WriteOnlyStream:
    """不提供 seek/tell，模拟只能顺序发送的 transport。"""

    def __init__(self, raw):
        self.raw = raw

    def write(self, data):
        return self.raw.write(data)


class _ReadOnlyStream:
    """只提供 read；流式 reader 不应向后 seek。"""

    def __init__(self, data):
        self.raw = io.BytesIO(data)

    def read(self, size=-1):
        return self.raw.read(size)


def _add_stream_member(archive, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


@pytest.mark.parametrize(
    ("write_mode", "magic"),
    [
        ("w:", None),
        ("w:gz", b"\x1f\x8b"),
        ("w:bz2", b"BZh"),
        ("w:xz", b"\xfd7zXZ\x00"),
    ],
)
def test_write_modes_round_trip_with_transparent_read(write_mode, magic):
    """r:* 根据 header 探测压缩；suffix 不参与 fileobj 场景的格式选择。"""

    buffer = io.BytesIO()
    kwargs = {}
    if write_mode in {"w:gz", "w:bz2"}:
        kwargs["compresslevel"] = 1
    elif write_mode == "w:xz":
        kwargs["preset"] = 0
    with tarfile.open(fileobj=buffer, mode=write_mode, **kwargs) as archive:
        _add_stream_member(archive, "payload.txt", b"content")

    raw = buffer.getvalue()
    if magic is not None:
        assert raw.startswith(magic)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as archive:
        member = archive.extractfile("payload.txt")
        assert member is not None
        assert member.read() == b"content"


def test_explicit_uncompressed_reader_rejects_compressed_data():
    """r: 禁止自动解压；若调用方不确定格式，应使用 r 或 r:*。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        _add_stream_member(archive, "member", b"content")

    with pytest.raises(tarfile.ReadError):
        tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:")


def test_invalid_bytes_are_not_a_tar_archive():
    """is_tarfile 提供布尔探测；直接 open 则以 ReadError 暴露解析失败。"""

    raw = b"not a tar archive"

    assert tarfile.is_tarfile(io.BytesIO(raw)) is False
    with pytest.raises(tarfile.ReadError):
        tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")


def test_is_tarfile_accepts_a_path_like_object(tmp_path):
    """3.9+ 的探测 API 同时接受 path、文件对象和 file-like object。"""

    path = tmp_path / "archive.data"
    with tarfile.open(path, "w:") as archive:
        _add_stream_member(archive, "member", b"content")

    assert tarfile.is_tarfile(path) is True


def test_w_mode_replaces_and_append_mode_preserves_members(tmp_path):
    """w 重建 archive；a 定位结尾 block 后追加 header/data，并保留旧成员顺序。"""

    path = tmp_path / "modes.tar"
    with tarfile.open(path, "w:") as archive:
        _add_stream_member(archive, "old.txt", b"old")
    with tarfile.open(path, "w:") as archive:
        _add_stream_member(archive, "replacement.txt", b"replacement")
    with tarfile.open(path, "a:") as archive:
        _add_stream_member(archive, "appended.txt", b"appended")

    with tarfile.open(path, "r:") as archive:
        assert archive.getnames() == ["replacement.txt", "appended.txt"]


def test_append_creates_a_missing_uncompressed_archive(tmp_path):
    """a 模式兼有 create-if-missing 语义，但不能用于任何压缩 TAR。"""

    path = tmp_path / "new.tar"
    with tarfile.open(path, "a:") as archive:
        _add_stream_member(archive, "member", b"content")

    assert tarfile.is_tarfile(path) is True


def test_compressed_append_mode_is_not_supported(tmp_path):
    """压缩流不能原地定位并改写结尾；需要解包重建或使用未压缩 a:。"""

    with pytest.raises(ValueError, match="mode must be"):
        tarfile.open(tmp_path / "archive.tar.gz", "a:gz")


def test_unknown_compression_name_raises_compression_error():
    """已知算法但错误 action 是 ValueError；未知算法本身则是 CompressionError。"""

    with pytest.raises(tarfile.CompressionError, match="unknown compression type"):
        tarfile.open(fileobj=io.BytesIO(), mode="w:unknown")


def test_exclusive_create_refuses_an_existing_path(tmp_path):
    """x 及 x:gz/x:bz2/x:xz 都执行 fail-if-exists；这里用基础格式展示。"""

    path = tmp_path / "existing.tar"
    path.write_bytes(b"preserve")

    with pytest.raises(FileExistsError):
        tarfile.open(path, "x:")
    assert path.read_bytes() == b"preserve"


def test_closing_tarfile_does_not_close_a_caller_owned_fileobj():
    """TarFile 只完成自己的零 block；fileobj 的生命周期仍由 caller 管理。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_stream_member(archive, "member", b"content")

    assert buffer.closed is False
    assert tarfile.is_tarfile(io.BytesIO(buffer.getvalue())) is True


def test_stream_modes_round_trip_without_seek_or_tell():
    """w|gz/r|* 只依赖 write/read，适合 transport；成员必须按归档顺序消费。"""

    raw = io.BytesIO()
    with tarfile.open(fileobj=_WriteOnlyStream(raw), mode="w|gz") as archive:
        _add_stream_member(archive, "first.txt", b"first")
        _add_stream_member(archive, "second.txt", b"second")

    with tarfile.open(fileobj=_ReadOnlyStream(raw.getvalue()), mode="r|*") as archive:
        contents = []
        for info in archive:
            member = archive.extractfile(info)
            assert member is not None
            contents.append((info.name, member.read()))

    assert contents == [("first.txt", b"first"), ("second.txt", b"second")]


def test_stream_reader_rejects_random_access_to_an_earlier_member():
    """流已越过 first 的 data blocks 后不能倒带；错误类型是 StreamError。"""

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:") as archive:
        _add_stream_member(archive, "first.txt", b"first")
        _add_stream_member(archive, "second.txt", b"second")

    with tarfile.open(fileobj=_ReadOnlyStream(raw.getvalue()), mode="r|") as archive:
        first = archive.next()
        second = archive.next()
        assert first is not None and second is not None
        with pytest.raises(tarfile.StreamError, match="backward"):
            archive.extractfile(first).read()
        # extractfile 只创建延迟读取对象；真正需要倒带时才报告 StreamError。


# ``TarFile.add``、``gettarinfo``/``addfile``、归档过滤与链接语义。
#
# ``add`` 从文件系统递归采集并在 3.7+ 按名称排序；``filter`` 可在写入前修改 metadata
# 或排除成员/整棵目录。``gettarinfo`` 与 ``addfile`` 把 metadata 和 payload 分离，适合
# 内存或生成式数据。``dereference`` 决定记录链接本身还是目标内容。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.tarfile.TarFile.add python.tarfile.add-arcname
# polyglot-covers: python.tarfile.add-recursive python.tarfile.add-sorted
# polyglot-covers: python.tarfile.add-recursive-false python.tarfile.add-filter
# polyglot-covers: python.tarfile.filter-modify python.tarfile.filter-exclude
# polyglot-covers: python.tarfile.filter-directory-subtree
# polyglot-covers: python.tarfile.gettarinfo python.tarfile.addfile
# polyglot-covers: python.tarfile.addfile-size python.tarfile.addfile-short-input
# polyglot-covers: python.tarfile.dereference python.tarfile.symbolic-link
# polyglot-covers: python.tarfile.hard-link python.tarfile.linkname
# polyglot-covers: python.tarfile.path-like-member python.tarfile.member-metadata




def test_add_uses_arcname_and_recurses_in_sorted_order(tmp_path):
    """arcname 隔离本机绝对路径；递归顺序稳定，便于生成可重现的 archive。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "zeta.txt").write_bytes(b"z")
    (source / "alpha.txt").write_bytes(b"a")
    nested = source / "nested"
    nested.mkdir()
    (nested / "child.txt").write_bytes(b"child")
    buffer = io.BytesIO()

    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == [
            "bundle",
            "bundle/alpha.txt",
            "bundle/nested",
            "bundle/nested/child.txt",
            "bundle/zeta.txt",
        ]
        member = archive.extractfile("bundle/nested/child.txt")
        assert member is not None
        assert member.read() == b"child"


def test_recursive_false_adds_only_the_directory_entry(tmp_path):
    """recursive=False 仍保存目录自身的 metadata，但不遍历 children。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "child.txt").write_bytes(b"child")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle", recursive=False)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == ["bundle"]
        assert archive.getmember("bundle").isdir() is True


def test_add_filter_can_normalize_metadata_and_exclude_members(tmp_path):
    """filter 在 header 写入前运行；返回 None 排除成员，返回 TarInfo 保存修改。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_bytes(b"keep")
    (source / "discard.tmp").write_bytes(b"discard")

    def reproducible(info):
        if info.name.endswith(".tmp"):
            return None
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mtime = 0
        return info

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle", filter=reproducible)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == ["bundle", "bundle/keep.txt"]
        for info in archive.getmembers():
            assert (info.uid, info.gid) == (0, 0)
            assert (info.uname, info.gname) == ("root", "root")
            assert info.mtime == 0


def test_rejecting_a_directory_in_filter_skips_its_entire_subtree(tmp_path):
    """目录返回 None 后不会访问 descendants；可避免先递归再逐文件过滤的成本。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_bytes(b"keep")
    cache = source / "cache"
    cache.mkdir()
    (cache / "hidden.bin").write_bytes(b"hidden")
    seen = []

    def exclude_cache(info):
        seen.append(info.name)
        if info.name == "bundle/cache":
            return None
        return info

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle", filter=exclude_cache)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == ["bundle", "bundle/keep.txt"]
    assert "bundle/cache" in seen
    assert "bundle/cache/hidden.bin" not in seen


def test_gettarinfo_then_addfile_allows_metadata_customization(tmp_path):
    """gettarinfo 只读取 stat；caller 修改 header 后，再提供位于开头的 binary fileobj。"""

    source = tmp_path / "source.txt"
    source.write_bytes(b"content")
    buffer = io.BytesIO()
    with source.open("rb") as payload:
        with tarfile.open(fileobj=buffer, mode="w:") as archive:
            info = archive.gettarinfo(source, arcname="renamed.txt")
            info.mode = 0o640
            info.uid = 123
            archive.addfile(info, payload)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        info = archive.getmember("renamed.txt")
        member = archive.extractfile(info)
        assert info.mode == 0o640
        assert info.uid == 123
        assert member is not None
        assert member.read() == b"content"


def test_addfile_reads_exactly_tarinfo_size_bytes():
    """TarInfo.size 是协议边界；fileobj 的额外 bytes 不属于该成员。"""

    info = tarfile.TarInfo("prefix.bin")
    info.size = 4
    source = io.BytesIO(b"data trailing bytes")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(info, source)

    assert source.tell() == 4
    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        member = archive.extractfile("prefix.bin")
        assert member is not None
        assert member.read() == b"data"


def test_addfile_rejects_payload_shorter_than_declared_size():
    """header 宣称的 size 必须有对应 bytes；短输入是 OSError，而不是自动缩小 metadata。"""

    info = tarfile.TarInfo("truncated.bin")
    info.size = 10

    with tarfile.open(fileobj=io.BytesIO(), mode="w:") as archive:
        with pytest.raises(OSError, match="unexpected end of data"):
            archive.addfile(info, io.BytesIO(b"short"))


def test_dereference_false_archives_a_symbolic_link_itself(tmp_path):
    """默认保留 symlink 类型和相对 linkname，不复制目标 payload。"""

    target = tmp_path / "target.txt"
    target.write_bytes(b"target content")
    link = tmp_path / "link.txt"
    link.symlink_to(target.name)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", dereference=False) as archive:
        archive.add(link, arcname="link.txt")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        info = archive.getmember("link.txt")
        assert info.issym() is True
        assert info.linkname == "target.txt"
        assert info.size == 0


def test_dereference_true_archives_symbolic_link_target_content(tmp_path):
    """dereference=True 把 symlink 当作目标文件采集，读取方不再需要链接目标。"""

    target = tmp_path / "target.txt"
    target.write_bytes(b"target content")
    link = tmp_path / "link.txt"
    link.symlink_to(target.name)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", dereference=True) as archive:
        archive.add(link, arcname="copied.txt")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        info = archive.getmember("copied.txt")
        member = archive.extractfile(info)
        assert info.isfile() is True
        assert member is not None
        assert member.read() == b"target content"


def test_repeated_inode_can_be_stored_as_a_tar_hard_link(tmp_path):
    """dereference=False 的 inode cache 将后续 hard link 写为 LNKTYPE，避免重复 payload。"""

    first = tmp_path / "first.txt"
    first.write_bytes(b"shared content")
    second = tmp_path / "second.txt"
    os.link(first, second)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", dereference=False) as archive:
        archive.add(first, arcname="first.txt")
        archive.add(second, arcname="second.txt")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        first_info, second_info = archive.getmembers()
        assert first_info.isfile() is True
        assert second_info.islnk() is True
        assert second_info.linkname == "first.txt"


# ``TarInfo`` header 编解码、成员类型、PAX metadata 与格式边界。
#
# TarInfo 只描述 header，不携带 payload。USTAR 兼容性高但名称/数值范围受限；GNU 用扩展
# header 支持长名称，PAX 用 UTF-8 key-value header 表达可移植 metadata，并且是 3.8+
# 默认写格式。``replace`` 可在解压过滤器中复制并消除不可信 metadata。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.tarfile.TarInfo python.tarfile.TarInfo-metadata
# polyglot-covers: python.tarfile.TarInfo.tobuf python.tarfile.TarInfo.frombuf
# polyglot-covers: python.tarfile.HeaderError python.tarfile.header-checksum
# polyglot-covers: python.tarfile.USTAR_FORMAT python.tarfile.GNU_FORMAT
# polyglot-covers: python.tarfile.PAX_FORMAT python.tarfile.DEFAULT_FORMAT
# polyglot-covers: python.tarfile.long-name python.tarfile.pax-utf8
# polyglot-covers: python.tarfile.pax-global-header python.tarfile.pax-member-header
# polyglot-covers: python.tarfile.TarInfo.replace python.tarfile.replace-deep
# polyglot-covers: python.tarfile.REGTYPE python.tarfile.AREGTYPE python.tarfile.DIRTYPE
# polyglot-covers: python.tarfile.SYMTYPE python.tarfile.LNKTYPE
# polyglot-covers: python.tarfile.CHRTYPE python.tarfile.BLKTYPE python.tarfile.FIFOTYPE
# polyglot-covers: python.tarfile.CONTTYPE python.tarfile.GNUTYPE_SPARSE
# polyglot-covers: python.tarfile.isfile python.tarfile.isreg python.tarfile.isdir
# polyglot-covers: python.tarfile.issym python.tarfile.islnk python.tarfile.isdev
# polyglot-covers: python.tarfile.ischr python.tarfile.isblk python.tarfile.isfifo




def _archive_with_member(name, *, format):
    buffer = io.BytesIO()
    info = tarfile.TarInfo(name)
    info.size = len(b"content")
    with tarfile.open(fileobj=buffer, mode="w:", format=format) as archive:
        archive.addfile(info, io.BytesIO(b"content"))
    return buffer.getvalue()


def test_tobuf_and_frombuf_round_trip_an_ustar_header():
    """单个基础 header 恰为 512 bytes；payload 和 padding 不属于 TarInfo。"""

    original = tarfile.TarInfo("devices/console")
    original.mode = 0o620
    original.uid = 1000
    original.gid = 100
    original.size = 0
    original.mtime = 1_600_000_000
    original.type = tarfile.CHRTYPE
    original.uname = "alice"
    original.gname = "staff"
    original.devmajor = 5
    original.devminor = 1

    header = original.tobuf(format=tarfile.USTAR_FORMAT)
    restored = tarfile.TarInfo.frombuf(
        header,
        encoding=tarfile.ENCODING,
        errors="surrogateescape",
    )

    assert len(header) == tarfile.BLOCKSIZE == 512
    assert restored.name == "devices/console"
    assert restored.mode == 0o620
    assert (restored.uid, restored.gid) == (1000, 100)
    assert restored.type == tarfile.CHRTYPE
    assert (restored.uname, restored.gname) == ("alice", "staff")
    assert (restored.devmajor, restored.devminor) == (5, 1)


def test_frombuf_rejects_a_header_with_a_bad_checksum():
    """header 任意字段变化都必须同步 checksum；否则 frombuf 抛 HeaderError 子类。"""

    header = bytearray(tarfile.TarInfo("member.txt").tobuf())
    header[0] ^= 1

    with pytest.raises(tarfile.HeaderError):
        tarfile.TarInfo.frombuf(
            bytes(header),
            encoding=tarfile.ENCODING,
            errors="surrogateescape",
        )


def test_default_write_format_is_pax():
    """3.8 起默认从 GNU 改为 PAX；需要旧工具兼容时应显式选 USTAR/GNU。"""

    assert tarfile.DEFAULT_FORMAT == tarfile.PAX_FORMAT


def test_ustar_rejects_a_name_outside_its_header_capacity():
    """USTAR 的 prefix/name 拆分仍有上限；无 slash 的 300 字符名称无法表示。"""

    info = tarfile.TarInfo("x" * 300)

    with pytest.raises(ValueError, match="name is too long"):
        info.tobuf(format=tarfile.USTAR_FORMAT)


@pytest.mark.parametrize("format", [tarfile.GNU_FORMAT, tarfile.PAX_FORMAT])
def test_gnu_and_pax_formats_round_trip_a_long_name(format):
    """GNU 使用 longname extension，PAX 使用 path record；读取 API 统一还原最终名称。"""

    name = "directory/" + "long-name-" * 30 + "report.txt"
    raw = _archive_with_member(name, format=format)

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as archive:
        info = archive.getmembers()[0]
        member = archive.extractfile(info)
        assert info.name == name
        assert member is not None
        assert member.read() == b"content"


def test_pax_preserves_unicode_name_as_utf8_extended_metadata():
    """PAX 不依赖本机 filesystem encoding；非 ASCII path 存在 per-member pax_headers。"""

    name = "文档/报告-甲.txt"
    raw = _archive_with_member(name, format=tarfile.PAX_FORMAT)

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        info = archive.getmembers()[0]
        assert info.name == name
        assert info.pax_headers["path"] == name


def test_global_and_member_pax_headers_have_different_scope():
    """global header 影响后续成员；per-member header 只补充当前 TarInfo。"""

    buffer = io.BytesIO()
    info = tarfile.TarInfo("member.txt")
    info.size = 0
    info.pax_headers = {"comment": "member-specific"}
    with tarfile.open(
        fileobj=buffer,
        mode="w:",
        format=tarfile.PAX_FORMAT,
        pax_headers={"vendor.polyglot": "global"},
    ) as archive:
        archive.addfile(info, io.BytesIO())

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        restored = archive.getmembers()[0]
        assert archive.pax_headers["vendor.polyglot"] == "global"
        assert restored.pax_headers["vendor.polyglot"] == "global"
        assert restored.pax_headers["comment"] == "member-specific"


def test_replace_returns_a_copy_and_deep_copies_pax_headers_by_default():
    """过滤器可用 replace 去除 owner/mode；默认 deep=True 避免共享 metadata dict。"""

    original = tarfile.TarInfo("original.txt")
    original.uid = 1000
    original.mode = 0o6755
    original.pax_headers = {"comment": "original"}

    sanitized = original.replace(
        name="safe.txt",
        uid=None,
        mode=None,
    )
    sanitized.pax_headers["comment"] = "sanitized"

    assert original.name == "original.txt"
    assert original.uid == 1000
    assert original.mode == 0o6755
    assert original.pax_headers == {"comment": "original"}
    assert sanitized.name == "safe.txt"
    assert sanitized.uid is None
    assert sanitized.mode is None


def test_replace_deep_false_shares_nested_metadata():
    """deep=False 更便宜但 pax_headers/custom attrs 共享；修改副本会反映到原对象。"""

    original = tarfile.TarInfo("member.txt")
    original.pax_headers = {"comment": "before"}
    shallow = original.replace(deep=False)

    shallow.pax_headers["comment"] = "after"

    assert original.pax_headers["comment"] == "after"


@pytest.mark.parametrize(
    ("type_code", "predicate"),
    [
        (tarfile.REGTYPE, "isfile"),
        (tarfile.AREGTYPE, "isreg"),
        (tarfile.CONTTYPE, "isfile"),
        (tarfile.GNUTYPE_SPARSE, "isfile"),
        (tarfile.DIRTYPE, "isdir"),
        (tarfile.SYMTYPE, "issym"),
        (tarfile.LNKTYPE, "islnk"),
        (tarfile.CHRTYPE, "ischr"),
        (tarfile.BLKTYPE, "isblk"),
        (tarfile.FIFOTYPE, "isfifo"),
    ],
)
def test_type_query_methods_map_header_codes_to_semantics(type_code, predicate):
    """业务代码应使用 is* predicate，不直接比较 byte type code。"""

    info = tarfile.TarInfo("member")
    info.type = type_code

    assert getattr(info, predicate)() is True
    if type_code in {tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE}:
        assert info.isdev() is True


def test_isfile_and_isreg_are_aliases_for_regular_members():
    """两个名称表达相同判断；AREGTYPE 是旧式 regular-file code。"""

    for type_code in (tarfile.REGTYPE, tarfile.AREGTYPE):
        info = tarfile.TarInfo("member")
        info.type = type_code
        assert info.isfile() is info.isreg() is True


# TAR 成员索引、顺序迭代、``extractfile`` 与损坏/拼接归档读取。
#
# TAR 允许重复成员名，``getmember`` 选择最后一次出现；``getmembers``/``getnames`` 保持
# 物理顺序。``extractfile`` 只返回 file-like payload，不写磁盘，并能解析 hard-link target。
# ``ignore_zeros`` 可恢复拼接或部分损坏归档，但不应作为默认容错策略。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.tarfile.getmember python.tarfile.duplicate-members
# polyglot-covers: python.tarfile.getmembers python.tarfile.getnames
# polyglot-covers: python.tarfile.member-order python.tarfile.member-mutation
# polyglot-covers: python.tarfile.next python.tarfile.iteration
# polyglot-covers: python.tarfile.list python.tarfile.list-members
# polyglot-covers: python.tarfile.extractfile python.tarfile.extractfile-buffered
# polyglot-covers: python.tarfile.extractfile-directory python.tarfile.extractfile-link
# polyglot-covers: python.tarfile.extractfile-missing python.tarfile.ignore-zeros
# polyglot-covers: python.tarfile.concatenated-archive python.tarfile.tarinfo-factory




def _add_read_member(archive, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def _build_read_archive(*members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        for name, payload in members:
            _add_read_member(archive, name, payload)
    return buffer.getvalue()


def test_getmember_uses_the_last_occurrence_of_a_duplicate_name():
    """更新式 TAR 可重复保存同名成员；名称 lookup 视最后一份为最新版本。"""

    raw = _build_read_archive(
        ("same.txt", b"first"),
        ("other.txt", b"other"),
        ("same.txt", b"latest"),
    )
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        all_versions = [info for info in archive.getmembers() if info.name == "same.txt"]
        latest = archive.getmember("same.txt")
        member = archive.extractfile(latest)

        assert latest is all_versions[-1]
        assert member is not None
        assert member.read() == b"latest"
        with pytest.raises(KeyError, match="missing.txt"):
            archive.getmember("missing.txt")


def test_getmembers_and_getnames_preserve_physical_order():
    """list 结果不是去重索引；审计/安全预检必须检查每一次出现。"""

    raw = _build_read_archive(
        ("second.txt", b"2"),
        ("first.txt", b"1"),
        ("second.txt", b"updated"),
    )
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        members = archive.getmembers()
        assert archive.getnames() == ["second.txt", "first.txt", "second.txt"]
        assert [info.name for info in members] == archive.getnames()


def test_next_and_iteration_walk_members_sequentially():
    """next 返回 TarInfo/None；for archive 是同一顺序协议的惯用形式。"""

    raw = _build_read_archive(("a.txt", b"a"), ("b.txt", b"b"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        assert archive.next().name == "a.txt"
        assert archive.next().name == "b.txt"
        assert archive.next() is None

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        assert [info.name for info in archive] == ["a.txt", "b.txt"]


def test_list_supports_compact_output_and_member_subset(capsys):
    """list 是人读输出；members 接 TarInfo 子集，结构化处理仍应使用 getmembers。"""

    raw = _build_read_archive(("first.txt", b"1"), ("second.txt", b"22"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        selected = [archive.getmember("second.txt")]
        archive.list(verbose=False, members=selected)

    output = capsys.readouterr().out
    assert output.strip() == "second.txt"


def test_extractfile_returns_a_buffered_reader_for_regular_content():
    """TarInfo 只有 offset/size metadata；extractfile 才创建按成员边界读取的 BufferedReader。"""

    raw = _build_read_archive(("lines.txt", b"first\nsecond\n"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        member = archive.extractfile("lines.txt")

        assert isinstance(member, io.BufferedReader)
        assert member.readline() == b"first\n"
        assert member.read() == b"second\n"


def test_extractfile_returns_none_for_a_directory():
    """directory/device 等无普通 payload 的成员返回 None，不返回空 BytesIO。"""

    buffer = io.BytesIO()
    directory = tarfile.TarInfo("empty/")
    directory.type = tarfile.DIRTYPE
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(directory)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.extractfile("empty/") is None
        with pytest.raises(KeyError, match="missing"):
            archive.extractfile("missing")


def test_extractfile_resolves_a_hard_link_to_its_archived_target():
    """LNKTYPE 没有重复 payload；extractfile 根据 archive-root-relative linkname 找目标。"""

    buffer = io.BytesIO()
    target = tarfile.TarInfo("target.txt")
    target.size = len(b"shared")
    link = tarfile.TarInfo("alias.txt")
    link.type = tarfile.LNKTYPE
    link.linkname = "target.txt"
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(target, io.BytesIO(b"shared"))
        archive.addfile(link)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        member = archive.extractfile("alias.txt")
        assert member is not None
        assert member.read() == b"shared"


def test_ignore_zeros_reads_a_second_concatenated_archive():
    """默认首个 zero block 即 EOF；ignore_zeros=True 跳过 padding 继续搜索后续 header。"""

    concatenated = _build_read_archive(("first.txt", b"first")) + _build_read_archive(
        ("second.txt", b"second")
    )

    with tarfile.open(fileobj=io.BytesIO(concatenated), mode="r:") as archive:
        assert archive.getnames() == ["first.txt"]
    with tarfile.open(
        fileobj=io.BytesIO(concatenated),
        mode="r:",
        ignore_zeros=True,
    ) as archive:
        assert archive.getnames() == ["first.txt", "second.txt"]


def test_mutating_cached_tarinfo_changes_subsequent_archive_views():
    """getmember/getmembers 返回 archive 持有的对象；只想展示修改时先 copy。"""

    raw = _build_read_archive(("member.txt", b"content"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        cached = archive.getmember("member.txt")
        detached = copy.copy(cached)
        detached.mode = 0o600
        assert archive.getmember("member.txt").mode != 0o600

        cached.mode = 0o640
        assert archive.getmembers()[0].mode == 0o640


def test_tarinfo_constructor_argument_customizes_read_member_objects():
    """tarinfo factory 支持附加领域行为；解析出来的每个 member 都是该 subclass。"""

    class TaggedTarInfo(tarfile.TarInfo):
        def display_name(self):
            return f"tar:{self.name}"

    raw = _build_read_archive(("member.txt", b"content"))
    with tarfile.open(
        fileobj=io.BytesIO(raw),
        mode="r:",
        tarinfo=TaggedTarInfo,
    ) as archive:
        info = archive.getmembers()[0]
        assert isinstance(info, TaggedTarInfo)
        assert info.display_name() == "tar:member.txt"


# TAR 选择性解压、metadata 恢复、目录收尾与链接落盘。
#
# ``extractfile`` 只读 payload；``extract``/``extractall`` 才写文件系统并可恢复 mode、mtime、
# 链接和目录。extractall 在 children 完成后再设置目录 metadata，避免只读目录阻断写入。
# 重复成员按顺序覆盖。安全策略必须显式传 filter，本文件使用可信或 data 场景。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.tarfile.extract python.tarfile.extract-return-none
# polyglot-covers: python.tarfile.extractall python.tarfile.extract-subset-generator
# polyglot-covers: python.tarfile.extract-path-like python.tarfile.extract-create-parent
# polyglot-covers: python.tarfile.set-attrs python.tarfile.set-attrs-false
# polyglot-covers: python.tarfile.extract-mode python.tarfile.extract-mtime
# polyglot-covers: python.tarfile.directory-metadata-after-children
# polyglot-covers: python.tarfile.extract-duplicate-overwrite
# polyglot-covers: python.tarfile.extract-hard-link python.tarfile.extract-symbolic-link
# polyglot-covers: python.tarfile.numeric-owner python.tarfile.named-owner



def _add_extraction_member(archive, name, payload, *, mode=0o644, mtime=0):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = mode
    info.mtime = mtime
    archive.addfile(info, io.BytesIO(payload))


def test_extractall_accepts_a_generator_for_a_member_subset(tmp_path):
    """members 可以惰性过滤 getmembers/iterator；仍应独立传入可信边界所需 filter。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_extraction_member(archive, "keep.py", b"print('keep')\n")
        _add_extraction_member(archive, "skip.txt", b"skip")

    def python_members(members):
        for info in members:
            if info.name.endswith(".py"):
                yield info

    destination = tmp_path / "selected"
    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(
            destination,
            members=python_members(archive),
            filter="data",
        )

    assert (destination / "keep.py").read_bytes() == b"print('keep')\n"
    assert not (destination / "skip.txt").exists()


def test_extract_returns_none_and_creates_parent_directories(tmp_path):
    """与 zipfile.extract 不同，tarfile.extract 的返回值固定为 None。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_extraction_member(archive, "nested/report.txt", b"report")

    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        result = archive.extract("nested/report.txt", destination, filter="data")

    assert result is None
    assert (destination / "nested" / "report.txt").read_bytes() == b"report"


def test_extract_restores_mode_and_mtime_when_set_attrs_is_true(tmp_path):
    """可信归档可恢复 permission/mtime；owner 处理还受权限、numeric_owner 与系统账户影响。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_extraction_member(
            archive,
            "script.sh",
            b"#!/bin/sh\n",
            mode=0o750,
            mtime=1_600_000_000,
        )

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extract(
            "script.sh",
            tmp_path,
            set_attrs=True,
            numeric_owner=False,
            filter="fully_trusted",
        )

    status = (tmp_path / "script.sh").stat()
    assert stat.S_IMODE(status.st_mode) == 0o750
    assert int(status.st_mtime) == 1_600_000_000


def test_set_attrs_false_leaves_new_filesystem_metadata_in_place(tmp_path):
    """set_attrs=False 仍写内容，但跳过 archive mode/owner/mtime 的恢复。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_extraction_member(archive, "plain.txt", b"content", mode=0o700, mtime=123)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extract(
            "plain.txt",
            tmp_path,
            set_attrs=False,
            filter="fully_trusted",
        )

    status = (tmp_path / "plain.txt").stat()
    assert int(status.st_mtime) != 123


def test_extractall_applies_directory_metadata_after_children(tmp_path):
    """目录 header 即使是只读 mode，也先以可写状态创建；children 完成后再收紧。"""

    directory = tarfile.TarInfo("locked/")
    directory.type = tarfile.DIRTYPE
    directory.mode = 0o500
    directory.mtime = 1_500_000_000
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(directory)
        _add_extraction_member(archive, "locked/child.txt", b"child")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(tmp_path, filter="fully_trusted")

    assert (tmp_path / "locked" / "child.txt").read_bytes() == b"child"
    directory_status = (tmp_path / "locked").stat()
    assert stat.S_IMODE(directory_status.st_mode) == 0o500
    assert int(directory_status.st_mtime) == 1_500_000_000
    # 恢复 owner write，避免 pytest 清理 tmp_path 时无法 unlink child。
    (tmp_path / "locked").chmod(0o700)


def test_later_duplicate_member_overwrites_earlier_content(tmp_path):
    """extractall 按物理顺序执行；同名最新成员覆盖旧内容，安全审计不能先去重。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_extraction_member(archive, "same.txt", b"first")
        _add_extraction_member(archive, "same.txt", b"latest")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(tmp_path, filter="data")

    assert (tmp_path / "same.txt").read_bytes() == b"latest"


def test_data_filter_allows_links_that_stay_inside_destination(tmp_path):
    """data 并非禁止全部链接；它拒绝越界 target，并允许归档内部的安全链接。"""

    target = tarfile.TarInfo("target.txt")
    target.size = len(b"shared")
    hard_link = tarfile.TarInfo("hard.txt")
    hard_link.type = tarfile.LNKTYPE
    hard_link.linkname = "target.txt"
    symbolic_link = tarfile.TarInfo("symbolic.txt")
    symbolic_link.type = tarfile.SYMTYPE
    symbolic_link.linkname = "target.txt"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(target, io.BytesIO(b"shared"))
        archive.addfile(hard_link)
        archive.addfile(symbolic_link)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(tmp_path, filter="data")

    assert (tmp_path / "hard.txt").read_bytes() == b"shared"
    assert os.stat(tmp_path / "hard.txt").st_ino == os.stat(tmp_path / "target.txt").st_ino
    assert (tmp_path / "symbolic.txt").is_symlink()
    assert os.readlink(tmp_path / "symbolic.txt") == "target.txt"


# TAR extraction filters、安全默认值、异常策略与有状态限制。
#
# Python 3.10 的安全补丁系列回移了 PEP 706 filters。``fully_trusted`` 保留传统 TAR
# 能力，``tar`` 阻止明显路径越界并收紧 mode，``data`` 进一步限制链接、特殊文件和 owner
# metadata。filter 不是 DoS 沙箱；文件数/总体积等预算仍需应用补充，失败后也可能已部分解压。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.tarfile.extraction-filter python.tarfile.filter-availability
# polyglot-covers: python.tarfile.fully-trusted-filter python.tarfile.tar-filter
# polyglot-covers: python.tarfile.data-filter python.tarfile.filter-string-name
# polyglot-covers: python.tarfile.OutsideDestinationError
# polyglot-covers: python.tarfile.SpecialFileError python.tarfile.AbsoluteLinkError
# polyglot-covers: python.tarfile.LinkOutsideDestinationError python.tarfile.FilterError
# polyglot-covers: python.tarfile.filter-skip python.tarfile.filter-replace-metadata
# polyglot-covers: python.tarfile.extraction-filter-attribute
# polyglot-covers: python.tarfile.extraction-filter-callable-only
# polyglot-covers: python.tarfile.errorlevel-zero python.tarfile.errorlevel-one
# polyglot-covers: python.tarfile.partial-extraction python.tarfile.stateful-filter
# polyglot-covers: python.tarfile.resource-budget python.tarfile.filter-not-sandbox




_HAS_FILTERS = hasattr(tarfile, "data_filter")
_section_134_pytestmark = pytest.mark.skipif(
    not _HAS_FILTERS,
    reason="extraction filters require a Python 3.10 security patch release",
)


def _add_filter_member(archive, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def _build_filter_archive(*members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        for name, payload in members:
            _add_filter_member(archive, name, payload)
    return buffer.getvalue()


@_section_134_pytestmark
def test_feature_detection_uses_capability_not_python_minor_version():
    """filters 是安全补丁回移功能；兼容代码应 hasattr，而不是假设所有 3.10 都相同。"""

    assert _HAS_FILTERS is True
    assert callable(tarfile.data_filter)


@_section_134_pytestmark
def test_fully_trusted_can_write_a_parent_path_but_data_filter_refuses(tmp_path):
    """传统行为允许 ``..``；data 在落盘前解析目标并抛 OutsideDestinationError。"""

    trusted_raw = _build_filter_archive(("../trusted-escape.txt", b"escaped"))
    trusted_destination = tmp_path / "trusted"
    trusted_destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(trusted_raw), mode="r:") as archive:
        archive.extractall(trusted_destination, filter="fully_trusted")

    assert (tmp_path / "trusted-escape.txt").read_bytes() == b"escaped"

    blocked_raw = _build_filter_archive(("../blocked-escape.txt", b"blocked"))
    blocked_destination = tmp_path / "blocked"
    with tarfile.open(fileobj=io.BytesIO(blocked_raw), mode="r:") as archive:
        with pytest.raises(tarfile.OutsideDestinationError):
            archive.extractall(blocked_destination, filter="data")
    assert not (tmp_path / "blocked-escape.txt").exists()


@_section_134_pytestmark
def test_fully_trusted_filter_returns_the_original_member():
    """该 filter 不复制、不清理 metadata，适用于来源确实完全可信的 archive。"""

    info = tarfile.TarInfo("member.txt")

    assert tarfile.fully_trusted_filter(info, "/unused") is info


@_section_134_pytestmark
def test_tar_filter_strips_leading_slash_and_dangerous_mode_bits(tmp_path):
    """tar profile 保留 Unix TAR 能力，但清掉 set-id/sticky 与 group/other write。"""

    info = tarfile.TarInfo("/leading.txt")
    info.mode = 0o7777

    filtered = tarfile.tar_filter(info, str(tmp_path))

    assert filtered.name == "leading.txt"
    assert filtered.mode == 0o755
    assert info.name == "/leading.txt"


@_section_134_pytestmark
def test_data_filter_removes_owner_and_normalizes_regular_file_mode(tmp_path):
    """data profile 保证 owner 可读写，并在 owner 不可执行时清除所有 execute bits。"""

    info = tarfile.TarInfo("document.txt")
    info.mode = 0o477
    info.uid = 1000
    info.gid = 100
    info.uname = "alice"
    info.gname = "staff"

    filtered = tarfile.data_filter(info, str(tmp_path))

    assert filtered.mode == 0o644
    assert filtered.uid is None
    assert filtered.gid is None
    assert filtered.uname is None
    assert filtered.gname is None


@_section_134_pytestmark
def test_data_filter_leaves_directory_mode_unspecified(tmp_path):
    """跨平台数据目录不强制 archive permission；mode=None 让 extract 跳过 chmod。"""

    info = tarfile.TarInfo("directory/")
    info.type = tarfile.DIRTYPE
    info.mode = 0o700

    filtered = tarfile.data_filter(info, str(tmp_path))

    assert filtered.mode is None


@_section_134_pytestmark
def test_data_filter_refuses_special_files(tmp_path):
    """FIFO、character/block device 可产生系统副作用，data profile 一律拒绝。"""

    fifo = tarfile.TarInfo("pipe")
    fifo.type = tarfile.FIFOTYPE

    with pytest.raises(tarfile.SpecialFileError) as captured:
        tarfile.data_filter(fifo, str(tmp_path))
    assert isinstance(captured.value, tarfile.FilterError)
    assert captured.value.tarinfo is fifo


@_section_134_pytestmark
def test_data_filter_refuses_absolute_and_outside_link_targets(tmp_path):
    """symlink 相对所在目录，hard link 相对 archive root；两种 linkname 分别计算。"""

    symbolic = tarfile.TarInfo("nested/link")
    symbolic.type = tarfile.SYMTYPE
    symbolic.linkname = "/etc/passwd"
    with pytest.raises(tarfile.AbsoluteLinkError):
        tarfile.data_filter(symbolic, str(tmp_path))

    hard = tarfile.TarInfo("hard-link")
    hard.type = tarfile.LNKTYPE
    hard.linkname = "../outside"
    with pytest.raises(tarfile.LinkOutsideDestinationError):
        tarfile.data_filter(hard, str(tmp_path))


@_section_134_pytestmark
def test_custom_filter_can_skip_members_and_replace_metadata(tmp_path):
    """callable 在每个成员落盘前运行；返回 None 跳过，返回副本替换实际 metadata。"""

    raw = _build_filter_archive(("keep.txt", b"keep"), ("discard.tmp", b"discard"))
    seen_destinations = []

    def application_filter(info, destination):
        seen_destinations.append(destination)
        if info.name.endswith(".tmp"):
            return None
        return info.replace(
            mode=0o600,
            uid=None,
            gid=None,
            uname=None,
            gname=None,
        )

    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extractall(destination, filter=application_filter)

    assert (destination / "keep.txt").read_bytes() == b"keep"
    assert stat.S_IMODE((destination / "keep.txt").stat().st_mode) == 0o600
    assert not (destination / "discard.tmp").exists()
    assert seen_destinations == [destination, destination]


@_section_134_pytestmark
def test_instance_extraction_filter_supplies_the_default_policy(tmp_path):
    """省略 extractall(filter=...) 时使用实例属性；适合封装后的 application boundary。"""

    raw = _build_filter_archive(("../outside.txt", b"outside"))
    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extraction_filter = tarfile.data_filter
        with pytest.raises(tarfile.OutsideDestinationError):
            archive.extractall(destination)


@_section_134_pytestmark
def test_extraction_filter_attribute_rejects_a_string_name(tmp_path):
    """extract 参数接受 'data'；实例属性必须是 callable，避免配置字符串被静默绑定。"""

    raw = _build_filter_archive(("member.txt", b"content"))
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extraction_filter = "data"
        with pytest.raises(TypeError):
            archive.extractall(tmp_path)


@_section_134_pytestmark
def test_errorlevel_zero_skips_rejected_member_and_continues(tmp_path):
    """errorlevel=0 将 FilterError 记为 debug 信息并跳过该成员；后续安全成员仍展开。"""

    raw = _build_filter_archive(
        ("../outside.txt", b"outside"),
        ("safe.txt", b"safe"),
    )
    destination = tmp_path / "output"
    with tarfile.open(
        fileobj=io.BytesIO(raw),
        mode="r:",
        errorlevel=0,
    ) as archive:
        archive.extractall(destination, filter="data")

    assert not (tmp_path / "outside.txt").exists()
    assert (destination / "safe.txt").read_bytes() == b"safe"


@_section_134_pytestmark
def test_errorlevel_one_aborts_but_does_not_roll_back_prior_members(tmp_path):
    """默认 fatal filter error 终止流程；此前已写入的文件由 caller 负责清理。"""

    raw = _build_filter_archive(
        ("safe.txt", b"safe"),
        ("../outside.txt", b"outside"),
    )
    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        with pytest.raises(tarfile.OutsideDestinationError):
            archive.extractall(destination, filter="data")

    assert (destination / "safe.txt").read_bytes() == b"safe"
    assert not (tmp_path / "outside.txt").exists()


@_section_134_pytestmark
def test_stateful_filter_enforces_count_and_total_size_budgets(tmp_path):
    """named filters不防资源耗尽；stateful callable 可按业务预算跳过后续成员。"""

    raw = _build_filter_archive(
        ("first.bin", b"1234"),
        ("second.bin", b"5678"),
        ("third.bin", b"90"),
    )

    class BudgetFilter:
        def __init__(self, max_files, max_size):
            self.max_files = max_files
            self.max_size = max_size
            self.files = 0
            self.size = 0

        def __call__(self, info, destination):
            if self.files + 1 > self.max_files:
                return None
            if self.size + info.size > self.max_size:
                return None
            self.files += 1
            self.size += info.size
            return tarfile.data_filter(info, destination)

    budget = BudgetFilter(max_files=2, max_size=8)
    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        archive.extractall(destination, filter=budget)

    assert budget.files == 2
    assert budget.size == 8
    assert (destination / "first.bin").exists()
    assert (destination / "second.bin").exists()
    assert not (destination / "third.bin").exists()


# ``python -m tarfile`` 创建、列出、校验、过滤解压与退出状态。
#
# CLI 根据目标 suffix 选择 gzip/bz2/xz，``--verbose`` 控制人读反馈，``--filter`` 只对解压
# 有效。它适合轻量脚本，不替代应用级资源预算。测试通过 ``sys.executable`` 调用相同容器
# 解释器；宿主机仍只使用仓库统一 Docker 入口。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.tarfile.cli python.tarfile.python-m-tarfile
# polyglot-covers: python.tarfile.cli-create python.tarfile.cli-suffix-compression
# polyglot-covers: python.tarfile.cli-list python.tarfile.cli-test
# polyglot-covers: python.tarfile.cli-extract python.tarfile.cli-filter
# polyglot-covers: python.tarfile.cli-verbose python.tarfile.cli-invalid-usage
# polyglot-covers: python.tarfile.cli-exit-status python.tarfile.cli-security-boundary



def _run_tarfile_cli(*arguments, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "tarfile", *map(str, arguments)],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_create_uses_suffix_compression_and_adds_directory_tree(tmp_path):
    """CLI 用 output extension 选择压缩；在 cwd 传相对 source 避免归档本机绝对前缀。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "member.txt").write_text("content", encoding="utf-8")

    result = _run_tarfile_cli(
        "--create",
        "created.tar.gz",
        "source",
        cwd=tmp_path,
    )

    archive_path = tmp_path / "created.tar.gz"
    assert result.returncode == 0
    assert result.stdout == ""
    assert archive_path.read_bytes().startswith(b"\x1f\x8b")
    with tarfile.open(archive_path, "r:*") as archive:
        assert archive.getnames() == ["source", "source/member.txt"]
        member = archive.extractfile("source/member.txt")
        assert member is not None
        assert member.read() == b"content"


def test_list_and_verbose_test_commands_report_archive_state(tmp_path):
    """list 默认只输出名称；test 只有 -v 时打印成功说明，status 始终是自动化依据。"""

    archive_path = tmp_path / "sample.tar"
    with tarfile.open(archive_path, "w:") as archive:
        archive.addfile(tarfile.TarInfo("member.txt"))

    listed = _run_tarfile_cli("--list", archive_path)
    tested = _run_tarfile_cli("--test", archive_path)
    verbose_test = _run_tarfile_cli("--verbose", "--test", archive_path)

    assert listed.returncode == 0
    assert listed.stdout.strip() == "member.txt"
    assert tested.returncode == 0
    assert tested.stdout == ""
    assert verbose_test.returncode == 0
    assert "is a tar archive" in verbose_test.stdout


def test_extract_with_data_filter_writes_safe_members(tmp_path):
    """--filter data 把命令行入口放到与 API 相同的安全 profile 下。"""

    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")
    archive_path = tmp_path / "sample.tar"
    with tarfile.open(archive_path, "w:") as archive:
        archive.add(source, arcname="nested/source.txt")
    destination = tmp_path / "output"

    result = _run_tarfile_cli(
        "--extract",
        archive_path,
        destination,
        "--filter",
        "data",
    )

    assert result.returncode == 0
    assert (destination / "nested" / "source.txt").read_text(encoding="utf-8") == "content"


def test_data_filter_causes_nonzero_exit_for_a_traversal_member(tmp_path):
    """filter exception 使 process 失败且不写越界成员；CLI 不负责吞掉安全错误。"""

    archive_path = tmp_path / "unsafe.tar"
    info = tarfile.TarInfo("../outside.txt")
    info.size = len(b"outside")

    with tarfile.open(archive_path, "w:") as archive:
        archive.addfile(info, io.BytesIO(b"outside"))
    destination = tmp_path / "output"

    result = _run_tarfile_cli(
        "--extract",
        archive_path,
        destination,
        "--filter",
        "data",
    )

    assert result.returncode != 0
    assert not (tmp_path / "outside.txt").exists()


def test_filter_option_is_rejected_for_non_extraction_operation(tmp_path):
    """--filter 不是 create/list/test 的通用开关，错误组合返回非零状态。"""

    archive_path = tmp_path / "sample.tar"
    with tarfile.open(archive_path, "w:"):
        pass

    result = _run_tarfile_cli("--filter", "data", "--list", archive_path)

    assert result.returncode != 0
    assert "only valid for extraction" in result.stderr


def test_missing_operation_returns_usage_error():
    """create/extract/list/test 属于 required mutually-exclusive group。"""

    result = _run_tarfile_cli()

    assert result.returncode != 0
    assert "usage:" in result.stderr.lower()
