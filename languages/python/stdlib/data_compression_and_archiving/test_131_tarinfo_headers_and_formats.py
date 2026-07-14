"""131｜``TarInfo`` header 编解码、成员类型、PAX metadata 与格式边界。

TarInfo 只描述 header，不携带 payload。USTAR 兼容性高但名称/数值范围受限；GNU 用扩展
header 支持长名称，PAX 用 UTF-8 key-value header 表达可移植 metadata，并且是 3.8+
默认写格式。``replace`` 可在解压过滤器中复制并消除不可信 metadata。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import io
import tarfile

import pytest


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
