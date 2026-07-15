"""070｜``zipfile`` 创建归档、压缩选择与文件模式。

ZIP 是成员容器而不是单一压缩流：归档可以同时保存未压缩、DEFLATE、BZIP2 和 LZMA
成员，``write``/``writestr`` 决定成员名与内容，``w``/``a``/``x`` 决定容器生命周期。
追加到非 ZIP 文件还可形成带前缀的数据文件；读取方会从末尾目录定位成员。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.zipfile.ZipFile python.zipfile.context-manager
# polyglot-covers: python.zipfile.write python.zipfile.writestr python.zipfile.arcname
# polyglot-covers: python.zipfile.ZIP_STORED python.zipfile.ZIP_DEFLATED
# polyglot-covers: python.zipfile.ZIP_BZIP2 python.zipfile.ZIP_LZMA
# polyglot-covers: python.zipfile.member-compression python.zipfile.compresslevel
# polyglot-covers: python.zipfile.mode-w python.zipfile.mode-a python.zipfile.mode-x
# polyglot-covers: python.zipfile.append-prefix python.zipfile.is_zipfile
# polyglot-covers: python.zipfile.BadZipFile python.zipfile.closed-archive
# polyglot-covers: python.zipfile.allowZip64 python.zipfile.force_zip64
# polyglot-covers: python.zipfile.empty-archive python.zipfile.unseekable-output
# polyglot-covers: python.zipfile.strict-timestamps python.zipfile.timestamp-clamping
# polyglot-covers: python.zipfile.unsupported-compression




import io
import os
import zipfile
import pytest
import struct
from pathlib import PurePosixPath
import stat
import importlib
import importlib.util
from pathlib import Path
import sys
import subprocess

class _UnseekableWriter:
    """只暴露顺序 write/flush，用来模拟 pipe 或 network-like sink。"""

    def __init__(self, raw):
        self.raw = raw

    def write(self, data):
        return self.raw.write(data)

    def flush(self):
        self.raw.flush()


def test_write_uses_arcname_instead_of_leaking_the_source_path(tmp_path):
    """write 默认保存传入路径；明确 arcname 可避免把临时目录结构写进归档。"""

    source = tmp_path / "source" / "report.txt"
    source.parent.mkdir()
    source.write_text("报告内容", encoding="utf-8")
    archive_path = tmp_path / "reports.zip"

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(source, arcname="docs/report.txt")

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["docs/report.txt"]
        assert archive.read("docs/report.txt").decode("utf-8") == "报告内容"


def test_writestr_encodes_text_as_utf8_and_accepts_bytes():
    """str 由 zipfile 按 UTF-8 编码；bytes 则原样作为成员 payload。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("text.txt", "你好")
        archive.writestr("binary.bin", b"\x00\xff")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.read("text.txt") == "你好".encode()
        assert archive.read("binary.bin") == b"\x00\xff"


@pytest.mark.parametrize(
    ("compression", "magic"),
    [
        (zipfile.ZIP_STORED, b"stored"),
        (zipfile.ZIP_DEFLATED, b"deflated"),
        (zipfile.ZIP_BZIP2, b"bzip2"),
        (zipfile.ZIP_LZMA, b"lzma"),
    ],
)
def test_supported_compression_methods_round_trip(compression, magic):
    """四个常量选择成员编码；读取 API 始终交付解压后的 bytes。"""

    buffer = io.BytesIO()
    payload = magic * 200
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        archive.writestr("payload.bin", payload)

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        info = archive.getinfo("payload.bin")
        assert info.compress_type == compression
        assert archive.read(info) == payload


def test_member_override_can_mix_compression_methods_in_one_archive():
    """构造器给默认算法，单次 writestr 的 compress_type/compresslevel 可覆盖它。"""

    payload = b"compressible content " * 200
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=1,
    ) as archive:
        archive.writestr("default.txt", payload)
        archive.writestr("stored.txt", payload, compress_type=zipfile.ZIP_STORED)
        archive.writestr(
            "maximum.txt",
            payload,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.getinfo("default.txt").compress_type == zipfile.ZIP_DEFLATED
        assert archive.getinfo("stored.txt").compress_type == zipfile.ZIP_STORED
        assert archive.getinfo("maximum.txt").compress_type == zipfile.ZIP_DEFLATED
        assert archive.read("maximum.txt") == payload


def test_w_mode_truncates_while_append_mode_preserves_members(tmp_path):
    """w 重建中央目录并清除旧成员；a 读取旧目录后把新成员追加进去。"""

    path = tmp_path / "modes.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("old.txt", b"old")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("replacement.txt", b"replacement")
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("appended.txt", b"appended")

    with zipfile.ZipFile(path) as archive:
        assert archive.namelist() == ["replacement.txt", "appended.txt"]


def test_exclusive_create_refuses_an_existing_path(tmp_path):
    """x 模式把覆盖风险变成 FileExistsError，适合必须原子拒绝旧文件的流程。"""

    path = tmp_path / "existing.zip"
    path.write_bytes(b"do not replace")

    with pytest.raises(FileExistsError):
        zipfile.ZipFile(path, "x")

    assert path.read_bytes() == b"do not replace"


def test_append_to_non_zip_file_preserves_the_prefix(tmp_path):
    """a 遇到非 ZIP 时在尾部写入归档，常用于 self-extracting/带前缀容器。"""

    path = tmp_path / "prefixed.bin"
    prefix = b"launcher-or-custom-header\n"
    path.write_bytes(prefix)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("inside.txt", b"payload")

    assert path.read_bytes().startswith(prefix)
    assert zipfile.is_zipfile(path) is True
    with zipfile.ZipFile(path) as archive:
        assert archive.read("inside.txt") == b"payload"


def test_is_zipfile_accepts_a_seekable_file_like_object():
    """探测可用于 path 或 seekable file object；无效数据返回 False，不负责抛解析错误。"""

    valid = io.BytesIO()
    with zipfile.ZipFile(valid, "w") as archive:
        archive.writestr("member", b"content")

    assert zipfile.is_zipfile(io.BytesIO(valid.getvalue())) is True
    assert zipfile.is_zipfile(io.BytesIO(b"not a zip archive")) is False


def test_invalid_archive_raises_bad_zip_file_when_opened():
    """is_zipfile 适合布尔探测；直接构造 ZipFile 则以 BadZipFile 报告格式错误。"""

    with pytest.raises(zipfile.BadZipFile):
        zipfile.ZipFile(io.BytesIO(b"broken"))

    assert zipfile.BadZipfile is zipfile.BadZipFile


def test_context_manager_closes_archive_and_rejects_later_operations():
    """退出 with 后中央目录已落盘；同一 ZipFile 对象不能继续读取或写入。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("member.txt", b"content")

    with pytest.raises(ValueError, match="closed"):
        archive.writestr("too-late.txt", b"content")


def test_closing_without_members_still_writes_a_valid_empty_archive():
    """即使没有成员，close 也写 EOCD；得到的是可再次打开的空 ZIP，而非零字节文件。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass

    assert buffer.getvalue().startswith(b"PK\x05\x06")
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.namelist() == []


def test_writer_supports_a_non_seekable_output_stream():
    """3.5+ 可向 pipe-like sink 顺序写入；成员尺寸/CRC 通过 data descriptor 收尾。"""

    raw = io.BytesIO()
    with zipfile.ZipFile(_UnseekableWriter(raw), "w") as archive:
        archive.writestr("member.txt", b"content")

    with zipfile.ZipFile(io.BytesIO(raw.getvalue())) as archive:
        assert archive.read("member.txt") == b"content"


def test_strict_timestamps_can_clamp_a_pre_1980_filesystem_time(tmp_path):
    """ZIP 时间下限是 1980；默认拒绝更早值，strict_timestamps=False 明确选择钳制。"""

    source = tmp_path / "historical.txt"
    source.write_bytes(b"historical")
    os.utime(source, (0, 0))

    with zipfile.ZipFile(io.BytesIO(), "w") as archive:
        with pytest.raises(ValueError, match="before 1980"):
            archive.write(source, arcname="historical.txt")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", strict_timestamps=False) as archive:
        archive.write(source, arcname="historical.txt")
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.getinfo("historical.txt").date_time == (1980, 1, 1, 0, 0, 0)


def test_unknown_compression_method_is_rejected_when_writing():
    """ZIP 规范还有其他 method ID；标准库 writer 只接受当前公开的四个常量。"""

    with pytest.raises(NotImplementedError, match="not supported"):
        zipfile.ZipFile(io.BytesIO(), "w", compression=999)


def test_force_zip64_requires_allow_zip64():
    """未知大小的大成员可预先 force ZIP64；禁用 ZIP64 的归档会立即拒绝该组合。"""

    with zipfile.ZipFile(io.BytesIO(), "w", allowZip64=False) as archive:
        with pytest.raises(ValueError, match="allowZip64"):
            archive.open("large.bin", "w", force_zip64=True)


# ZIP 成员流、``ZipInfo`` 元数据、重复名称与完整性检查。
#
# 中央目录允许按名称快速定位，但名称不保证唯一；需要区分同名成员时，应把 ``ZipInfo``
# 对象传给 ``open``/``read``。写成员流适合未知长度的数据，读成员流支持常用 buffered
# 操作；归档关闭前必须先关闭活动 writer。CRC 检查可发现内容损坏，但不是恶意输入防线。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.zipfile.ZipInfo python.zipfile.ZipInfo.is_dir
# polyglot-covers: python.zipfile.ZipInfo.from_file python.zipfile.member-metadata
# polyglot-covers: python.zipfile.namelist python.zipfile.infolist python.zipfile.getinfo
# polyglot-covers: python.zipfile.open-read python.zipfile.open-write
# polyglot-covers: python.zipfile.ZipExtFile python.zipfile.member-seek
# polyglot-covers: python.zipfile.duplicate-names python.zipfile.read-ZipInfo
# polyglot-covers: python.zipfile.archive-comment python.zipfile.comment-limit
# polyglot-covers: python.zipfile.testzip python.zipfile.CRC
# polyglot-covers: python.zipfile.writer-exclusion python.zipfile.missing-member
# polyglot-covers: python.zipfile.printdir python.zipfile.null-name-truncation
# polyglot-covers: python.zipfile.unicode-name python.zipfile.utf8-flag
# polyglot-covers: python.zipfile.encrypted-read python.zipfile.setpassword
# polyglot-covers: python.zipfile.password-override python.zipfile.password-bytes
# polyglot-covers: python.zipfile.no-encrypted-write python.zipfile.no-AES-write




# Python 3.10 的 zipfile 不能生成加密成员，因此沿用 CPython 回归测试预生成的
# traditional ZipCrypto fixture；密码是 b"python"，明文见下面的断言。
_ENCRYPTED_ZIP = (
    b"PK\x03\x04\x14\x00\x01\x00\x00\x00n\x92i.#y\xef?&\x00\x00\x00\x1a\x00"
    b"\x00\x00\x08\x00\x00\x00test.txt\xfa\x10\xa0gly|\xfa-\xc5\xc0=\xf9y"
    b"\x18\xe0\xa8r\xb3Z}Lg\xbc\xae\xf9|\x9b\x19\xe4\x8b\xba\xbb)\x8c\xb0\xdbl"
    b"PK\x01\x02\x14\x00\x14\x00\x01\x00\x00\x00n\x92i.#y\xef?&\x00\x00\x00"
    b"\x1a\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x01\x00 \x00\xb6\x81"
    b"\x00\x00\x00\x00test.txtPK\x05\x06\x00\x00\x00\x00\x01\x00\x01\x006\x00"
    b"\x00\x00L\x00\x00\x00\x00\x00"
)


def test_zipinfo_controls_member_metadata_and_directory_marker():
    """ZipInfo 可显式指定时间、压缩、comment 与权限；尾随 slash 表示目录成员。"""

    file_info = zipfile.ZipInfo("bin/tool.sh", date_time=(2020, 5, 4, 3, 2, 0))
    file_info.compress_type = zipfile.ZIP_DEFLATED
    file_info.comment = b"executable script"
    file_info.create_system = 3
    file_info.external_attr = 0o755 << 16
    directory_info = zipfile.ZipInfo("empty/")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(file_info, b"#!/bin/sh\n")
        archive.writestr(directory_info, b"")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        restored = archive.getinfo("bin/tool.sh")
        assert restored.date_time == (2020, 5, 4, 3, 2, 0)
        assert restored.comment == b"executable script"
        assert restored.external_attr >> 16 == 0o755
        assert restored.file_size == len(b"#!/bin/sh\n")
        assert restored.compress_size > 0
        assert restored.CRC != 0
        assert archive.getinfo("empty/").is_dir() is True


def test_zipinfo_from_file_uses_arcname_and_filesystem_metadata(tmp_path):
    """from_file 建立 metadata 但不读取内容；caller 仍须把内容交给 writestr/write。"""

    source = tmp_path / "source.txt"
    source.write_bytes(b"content")
    info = zipfile.ZipInfo.from_file(source, arcname="renamed.txt")

    assert info.filename == "renamed.txt"
    assert info.file_size == 7
    assert info.is_dir() is False


def test_name_and_info_views_expose_order_and_metadata():
    """namelist 只给名称；infolist 保留归档顺序并提供每个成员的完整元数据。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("first.txt", b"first")
        archive.writestr("second.txt", b"second")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.namelist() == ["first.txt", "second.txt"]
        assert [info.filename for info in archive.infolist()] == archive.namelist()
        assert archive.getinfo("second.txt").file_size == 6
        with pytest.raises(KeyError, match="missing.txt"):
            archive.getinfo("missing.txt")


def test_duplicate_names_require_zipinfo_to_address_each_member():
    """名称可以重复且 write 会 warning；ZipInfo 身份能精确读取旧、新两个成员。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("same.txt", b"first")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("same.txt", b"second")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        first, second = archive.infolist()
        assert first.filename == second.filename == "same.txt"
        assert archive.read(first) == b"first"
        assert archive.read(second) == b"second"
        # 字符串查找使用内部名称索引，重复项会遮蔽旧成员。
        assert archive.read("same.txt") == b"second"


def test_writable_member_stream_accepts_incremental_bytes():
    """open(..., 'w') 无需先把完整 payload 放进内存，close 时补齐成员 header/CRC。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        with archive.open("streamed.bin", "w") as member:
            assert member.write(b"first-") == 6
            assert member.write(memoryview(b"second")) == 6

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.read("streamed.bin") == b"first-second"


def test_active_writer_excludes_other_archive_operations():
    """本地 header 尚未收尾时，归档拒绝并行读或第二个 writer，避免目录状态不一致。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("ready.txt", b"ready")
        writer = archive.open("active.txt", "w")
        try:
            writer.write(b"active")
            with pytest.raises(ValueError, match=r"writ(?:e|ing) handle"):
                archive.read("ready.txt")
            with pytest.raises(ValueError, match=r"writ(?:e|ing) handle"):
                archive.open("another.txt", "w")
        finally:
            writer.close()
        archive.writestr("after.txt", b"after")


def test_readable_member_stream_supports_buffered_navigation():
    """ZipExtFile 可 read/readline/iterate/seek/tell；seek 按解压后位置计算。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("lines.txt", b"first\nsecond\nthird\n")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with archive.open("lines.txt") as member:
            assert member.readable() is True
            assert member.seekable() is True
            assert member.readline() == b"first\n"
            assert member.tell() == 6
            assert member.seek(0) == 0
            assert list(member) == [b"first\n", b"second\n", b"third\n"]


def test_member_reader_can_outlive_the_zipfile_for_an_independent_source(tmp_path):
    """ZipExtFile 持有自己的底层引用；ZipFile.close 后，已打开 reader 仍可继续读取。"""

    path = tmp_path / "reader.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("payload.txt", b"payload")

    archive = zipfile.ZipFile(path)
    member = archive.open("payload.txt")
    archive.close()
    try:
        assert member.read() == b"payload"
    finally:
        member.close()


def test_archive_comment_round_trips_and_oversized_value_is_truncated():
    """EOCD comment 最多 65535 bytes；超长赋值会 warning 并截断，而不是扩展格式。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.comment = b"release-2020"
        archive.writestr("member", b"content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.comment == b"release-2020"
        with pytest.warns(UserWarning, match="65535"):
            archive.comment = b"x" * 70_000
        assert archive.comment == b"x" * 65_535


def test_testzip_returns_the_first_member_with_a_bad_crc():
    """testzip 逐个读取并校验 CRC；stored payload 损坏时返回成员名而非内容。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("healthy.txt", b"healthy")
        archive.writestr("damaged.txt", b"original")

    raw = bytearray(buffer.getvalue())
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        info = archive.getinfo("damaged.txt")
        name_length, extra_length = struct.unpack_from("<HH", raw, info.header_offset + 26)
        payload_offset = info.header_offset + 30 + name_length + extra_length
    raw[payload_offset] ^= 1

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert archive.testzip() == "damaged.txt"


def test_testzip_returns_none_when_every_member_passes_crc():
    """成功以 None 表示；空归档也没有坏成员。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("member.txt", b"content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.testzip() is None


def test_printdir_writes_a_human_readable_member_table(capsys):
    """printdir 面向终端浏览，不是结构化接口；程序逻辑应使用 infolist。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("report.txt", b"content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        archive.printdir()

    output = capsys.readouterr().out
    assert "File Name" in output
    assert "Modified" in output
    assert "report.txt" in output


def test_null_byte_truncates_an_archive_member_name():
    """NUL 后的名称会被静默截断；外部输入不应直接拼成 arcname。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("visible.txt\x00hidden.txt", b"content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.namelist() == ["visible.txt"]


def test_non_ascii_member_name_uses_the_utf8_flag():
    """无法用 CP437 表示的名称会以 UTF-8 存储并设置 general-purpose bit 11。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("报告.txt", b"content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        info = archive.getinfo("报告.txt")
        assert info.flag_bits & 0x800
        assert archive.read(info) == b"content"


def test_encrypted_member_requires_a_bytes_password():
    """无密码和错误密码都是 RuntimeError；密码参数必须是 bytes，不能传 str。"""

    with zipfile.ZipFile(io.BytesIO(_ENCRYPTED_ZIP)) as archive:
        with pytest.raises(RuntimeError, match="password required"):
            archive.read("test.txt")
        with pytest.raises(RuntimeError, match="Bad password"):
            archive.read("test.txt", pwd=b"wrong")
        with pytest.raises(TypeError, match="expected bytes"):
            archive.read("test.txt", pwd="python")


def test_password_can_be_per_call_or_an_archive_default():
    """read/open 的 pwd 覆盖默认值；setpassword 适合同一密码保护多个成员的读取流程。"""

    with zipfile.ZipFile(io.BytesIO(_ENCRYPTED_ZIP)) as archive:
        assert archive.read("test.txt", pwd=b"python") == b"zipfile.py encryption test"
        archive.setpassword(b"python")
        with archive.open("test.txt") as member:
            assert member.read() == b"zipfile.py encryption test"


def test_stdlib_zipfile_cannot_create_an_encrypted_member():
    """3.10 只实现传统 ZipCrypto 解密；writer 的 pwd 参数被明确拒绝，也不支持 AES。"""

    with zipfile.ZipFile(io.BytesIO(), "w") as archive:
        with pytest.raises(ValueError, match="only supported for reading"):
            archive.open("secret.txt", "w", pwd=b"password")


# ZIP 解压、目标路径清理与不可信归档的预检策略。
#
# ``extract``/``extractall`` 会创建父目录并清理绝对路径、``.``、``..`` 等组件，但官方
# 仍要求在解压不可信归档前检查成员。路径穿越只是风险之一：超大展开体积、极端压缩比、
# 重复覆盖和类 Unix symlink 元数据都需要应用按自身信任边界制定策略。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.zipfile.extract python.zipfile.extract-return-path
# polyglot-covers: python.zipfile.extractall python.zipfile.extract-subset
# polyglot-covers: python.zipfile.extract-create-directories
# polyglot-covers: python.zipfile.extract-path-normalization
# polyglot-covers: python.zipfile.extract-overwrite python.zipfile.untrusted-archive
# polyglot-covers: python.zipfile.preflight python.zipfile.uncompressed-size-budget
# polyglot-covers: python.zipfile.compression-ratio-budget python.zipfile.path-traversal
# polyglot-covers: python.zipfile.symlink-metadata python.zipfile.resource-limits




def _inspect_members(
    archive,
    *,
    max_total_size=1_000_000,
    max_member_size=500_000,
    max_ratio=100,
):
    """返回通过示例安全策略的 ZipInfo；真实限额应由业务场景决定。"""

    accepted = []
    total_size = 0
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe member path: {info.filename}")
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"symbolic link is not accepted: {info.filename}")

        total_size += info.file_size
        ratio = info.file_size / max(info.compress_size, 1)
        if info.file_size > max_member_size:
            raise ValueError(f"member is too large: {info.filename}")
        if total_size > max_total_size:
            raise ValueError("archive expands beyond the total size budget")
        if ratio > max_ratio:
            raise ValueError(f"compression ratio is too high: {info.filename}")
        accepted.append(info)
    return accepted


def test_extract_returns_created_path_and_makes_parent_directories(tmp_path):
    """返回值是规范化后的 filesystem path 字符串，可直接交给后续处理。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("nested/report.txt", b"report")

    destination = tmp_path / "output"
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        extracted = archive.extract("nested/report.txt", destination)

    assert extracted == str(destination / "nested" / "report.txt")
    assert (destination / "nested" / "report.txt").read_bytes() == b"report"


def test_extractall_can_select_a_member_subset(tmp_path):
    """members 参数限制本次展开范围；它不是安全过滤器，名称仍应在此前检查。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("keep.txt", b"keep")
        archive.writestr("skip.txt", b"skip")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        archive.extractall(tmp_path, members=["keep.txt"])

    assert (tmp_path / "keep.txt").read_bytes() == b"keep"
    assert not (tmp_path / "skip.txt").exists()


def test_extract_removes_absolute_and_parent_path_components(tmp_path):
    """内建提取器清除危险组件；不要把这项兼容性清理当成完整信任策略。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../../outside.txt", b"parent")
        archive.writestr("/absolute.txt", b"absolute")
        archive.writestr("safe/../flattened.txt", b"flattened")

    destination = tmp_path / "destination"
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        archive.extractall(destination)

    assert (destination / "outside.txt").read_bytes() == b"parent"
    assert (destination / "absolute.txt").read_bytes() == b"absolute"
    assert (destination / "safe" / "flattened.txt").read_bytes() == b"flattened"
    assert not (tmp_path / "outside.txt").exists()


def test_extract_overwrites_an_existing_regular_file(tmp_path):
    """同路径普通文件会被替换内容；若不能接受覆盖，应在 extract 前自行判定冲突。"""

    target = tmp_path / "same.txt"
    target.write_bytes(b"local content")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("same.txt", b"archive content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        archive.extract("same.txt", tmp_path)

    assert target.read_bytes() == b"archive content"


def test_preflight_accepts_members_within_path_and_size_budgets():
    """先检查 infolist，再把返回的 ZipInfo 列表交给 extractall，避免 TOCTOU 式重查名称。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("docs/readme.txt", b"ordinary content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        accepted = _inspect_members(archive)

    assert [info.filename for info in accepted] == ["docs/readme.txt"]


@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "a/../../escape.txt"])
def test_preflight_rejects_absolute_or_parent_paths(name):
    """PurePosixPath 按 ZIP 固定的 slash 语法检查；不能用宿主 OS 路径规则代替。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, b"content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="unsafe member path"):
            _inspect_members(archive)


def test_preflight_rejects_total_expansion_beyond_budget():
    """累计 file_size 比只看单个成员更重要，大量小成员同样能耗尽磁盘。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("first.bin", b"a" * 60)
        archive.writestr("second.bin", b"b" * 60)

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="total size budget"):
            _inspect_members(
                archive,
                max_total_size=100,
                max_member_size=100,
            )


def test_preflight_can_reject_an_extreme_compression_ratio():
    """小 archive 可能展开为大 payload；ratio 限额只是资源策略，不代表内容可信。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("repeated.bin", b"0" * 100_000)

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="compression ratio"):
            _inspect_members(
                archive,
                max_total_size=200_000,
                max_member_size=200_000,
                max_ratio=10,
            )


def test_preflight_recognizes_unix_symlink_metadata():
    """ZIP 没有统一的 symlink 类型；Unix creator 通常把 mode 编入 external_attr。"""

    link = zipfile.ZipInfo("link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(link, b"target.txt")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="symbolic link"):
            _inspect_members(archive)


# ``zipfile.Path`` 的 Traversable 视图、文本 I/O 与安全边界。
#
# ``Path`` 把中央目录呈现成接近 ``pathlib.Path`` 的只读/可写视图，支持 ``/``、
# ``joinpath``、目录枚举和 text/binary open。它还能推导未显式存储的父目录，但不会清理
# 成员名称；将归档路径映射到真实文件系统前，caller 必须自行阻止绝对路径和 ``..``。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.zipfile.Path python.zipfile.Path.root
# polyglot-covers: python.zipfile.Path.truediv python.zipfile.Path.joinpath
# polyglot-covers: python.zipfile.Path.name python.zipfile.Path.iterdir
# polyglot-covers: python.zipfile.Path.exists python.zipfile.Path.is_dir
# polyglot-covers: python.zipfile.Path.is_file python.zipfile.Path.implicit-directory
# polyglot-covers: python.zipfile.Path.open-text python.zipfile.Path.open-binary
# polyglot-covers: python.zipfile.Path.read_text python.zipfile.Path.read_bytes
# polyglot-covers: python.zipfile.Path.write-text python.zipfile.Path.write-binary
# polyglot-covers: python.zipfile.Path.unsanitized python.zipfile.Path.security
# polyglot-covers: python.zipfile.Path.encoding-keyword python.zipfile.Traversable



def _sample_archive():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("docs/guide.txt", "第一行\n第二行\n")
        archive.writestr("docs/raw.bin", b"\x00\xff")
        archive.writestr("top.txt", b"top")
    return buffer.getvalue()


def test_root_iterdir_infers_directories_not_stored_as_members():
    """只有 docs/guide.txt 也足以推导 docs/；调用方不必要求显式 directory entry。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        root = zipfile.Path(archive)
        children = {child.name: child for child in root.iterdir()}

        assert set(children) == {"docs", "top.txt"}
        assert children["docs"].is_dir() is True
        assert children["top.txt"].is_file() is True


def test_slash_and_multi_part_joinpath_traverse_the_same_member():
    """3.10 的 joinpath 可一次接收多个组件；``/`` 逐层组合得到等价位置。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        root = zipfile.Path(archive)
        via_slash = root / "docs" / "guide.txt"
        via_joinpath = root.joinpath("docs", "guide.txt")

        assert via_slash.at == via_joinpath.at == "docs/guide.txt"
        assert via_slash.exists() is True
        assert via_slash.is_file() is True
        assert (root / "missing.txt").exists() is False


def test_read_text_requires_an_explicit_encoding_for_portable_310_code():
    """encoding 用 keyword 兼容未打补丁的 3.10；默认 text open 还会做 newline 处理。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        guide = zipfile.Path(archive) / "docs" / "guide.txt"

        assert guide.read_text(encoding="utf-8") == "第一行\n第二行\n"
        with guide.open("r", encoding="utf-8") as stream:
            assert stream.readlines() == ["第一行\n", "第二行\n"]


def test_read_bytes_and_binary_open_return_member_bytes():
    """binary 模式忽略 TextIOWrapper 参数并直接交付 ZipExtFile 的 bytes。"""

    with zipfile.ZipFile(io.BytesIO(_sample_archive())) as archive:
        raw = zipfile.Path(archive) / "docs" / "raw.bin"

        assert raw.read_bytes() == b"\x00\xff"
        with raw.open("rb") as stream:
            assert stream.read(1) == b"\x00"
            assert stream.read() == b"\xff"


def test_path_open_writes_text_and_binary_members():
    """Path 不是纯只读 facade；root ZipFile 处于写模式时可用 w/wb 新建成员。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        root = zipfile.Path(archive)
        with (root / "text.txt").open("w", encoding="utf-8") as stream:
            assert stream.write("你好") == 2
        with (root / "raw.bin").open("wb") as stream:
            assert stream.write(b"\x00\xff") == 2

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert archive.read("text.txt") == "你好".encode()
        assert archive.read("raw.bin") == b"\x00\xff"


def test_path_can_be_constructed_directly_from_a_path_like_object(tmp_path):
    """root 可是现有 ZipFile，也可是 ZipFile 构造器接受的 path；后者由 Path 内部打开。"""

    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("member.txt", b"content")

    member = zipfile.Path(archive_path) / "member.txt"
    try:
        assert member.read_bytes() == b"content"
    finally:
        member.root.close()


def test_path_exposes_parent_components_without_sanitizing_them():
    """与 extract 不同，Path 忠实访问 ``..`` 名称；复制到磁盘前必须单独验证 at。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../outside.txt", b"untrusted")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        root = zipfile.Path(archive)
        unsafe = root / ".." / "outside.txt"

        assert unsafe.exists() is True
        assert unsafe.read_bytes() == b"untrusted"
        assert unsafe.at == "../outside.txt"


# ``PyZipFile.writepy`` 编译 Python 模块、包、过滤与 zipimport 工作流。
#
# ``PyZipFile`` 在普通 ZIP API 上增加 ``writepy``：它把 ``.py`` 编译为适合从归档导入的
# ``.pyc``，区分单文件、普通目录和 package 目录，并可用 ``filterfunc`` 跳过整棵子树。
# 编译优化级别属于归档构建配置；生成物仍是当前解释器版本绑定的 bytecode。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.zipfile.PyZipFile python.zipfile.PyZipFile.optimize
# polyglot-covers: python.zipfile.writepy python.zipfile.writepy-file
# polyglot-covers: python.zipfile.writepy-directory python.zipfile.writepy-package
# polyglot-covers: python.zipfile.writepy-recursion python.zipfile.writepy-sorted
# polyglot-covers: python.zipfile.writepy-filterfunc python.zipfile.filter-subtree
# polyglot-covers: python.zipfile.writepy-path-like python.zipfile.pyc-layout
# polyglot-covers: python.zipfile.bytecode-magic python.zipfile.zipimport-workflow
# polyglot-covers: python.zipfile.writepy-invalid-file python.zipfile.optimized-bytecode




def _write_source(path, source):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _forget_modules(prefix):
    """避免 zipimport 案例把临时模块留给同一 pytest process 的后续测试。"""

    for name in list(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            sys.modules.pop(name, None)


def test_writepy_compiles_a_single_source_at_the_archive_root(tmp_path):
    """单个 .py 去掉原路径并以 legacy ``module.pyc`` 名称存入根目录。"""

    source = _write_source(tmp_path / "standalone.py", "VALUE = 42\n")
    archive_path = tmp_path / "library.zip"
    with zipfile.PyZipFile(archive_path, "w", optimize=0) as archive:
        archive.writepy(source)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["standalone.pyc"]
        assert archive.read("standalone.pyc").startswith(importlib.util.MAGIC_NUMBER)


def test_writepy_maps_a_non_package_directory_to_top_level_modules(tmp_path):
    """没有 __init__.py 的目录不是 package namespace；其中模块平铺到归档根。"""

    source_dir = tmp_path / "loose_modules"
    _write_source(source_dir / "beta.py", "NAME = 'beta'\n")
    _write_source(source_dir / "alpha.py", "NAME = 'alpha'\n")
    _write_source(source_dir / "ignored.txt", "not Python\n")
    archive_path = tmp_path / "loose.zip"

    with zipfile.PyZipFile(archive_path, "w") as archive:
        archive.writepy(source_dir)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["alpha.pyc", "beta.pyc"]


def test_writepy_preserves_package_layout_and_recurses_in_sorted_order(tmp_path):
    """package/subpackage 依赖 __init__.py 识别；3.7+ 递归目录项按名称排序。"""

    package = tmp_path / "demo_package"
    _write_source(package / "__init__.py", "PACKAGE = True\n")
    _write_source(package / "zeta.py", "VALUE = 'z'\n")
    _write_source(package / "alpha.py", "VALUE = 'a'\n")
    _write_source(package / "nested" / "__init__.py", "NESTED = True\n")
    _write_source(package / "nested" / "module.py", "VALUE = 'nested'\n")
    archive_path = tmp_path / "package.zip"

    with zipfile.PyZipFile(archive_path, "w") as archive:
        archive.writepy(package)

    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()

    assert names == [
        "demo_package/__init__.pyc",
        "demo_package/alpha.pyc",
        "demo_package/nested/__init__.pyc",
        "demo_package/nested/module.pyc",
        "demo_package/zeta.pyc",
    ]
    # 递归遍历把排序后的目录与文件放在同一层比较，nested 因此先于 zeta。


def test_filterfunc_skips_a_file_or_an_entire_directory_subtree(tmp_path):
    """callback 对每个候选 path 调用；目录返回 False 时，不再遍历它的 descendants。"""

    package = tmp_path / "filtered_package"
    _write_source(package / "__init__.py", "PACKAGE = True\n")
    _write_source(package / "core.py", "VALUE = 'core'\n")
    _write_source(package / "test_core.py", "VALUE = 'test'\n")
    _write_source(package / "tests" / "__init__.py", "TESTS = True\n")
    _write_source(package / "tests" / "hidden.py", "HIDDEN = True\n")
    seen = []

    def exclude_tests(path):
        seen.append(path)
        # 官方接口传入 string；显式转 Path 后再按 basename 制定跨平台规则。
        name = Path(path).name
        return name != "tests" and not name.startswith("test_")

    archive_path = tmp_path / "filtered.zip"
    with zipfile.PyZipFile(archive_path, "w") as archive:
        archive.writepy(package, filterfunc=exclude_tests)

    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == [
            "filtered_package/__init__.pyc",
            "filtered_package/core.pyc",
        ]
    assert str(package / "tests") in seen
    assert str(package / "tests" / "hidden.py") not in seen


def test_compiled_package_can_be_imported_directly_from_the_zip(tmp_path, monkeypatch):
    """PyZipFile 的核心用途是配合 zipimport；归档根加入 sys.path 后可正常导入 package。"""

    package_name = "polyglot_zip_import_demo"
    package = tmp_path / package_name
    _write_source(package / "__init__.py", "from .answer import ANSWER\n")
    _write_source(package / "answer.py", "ANSWER = 6 * 7\n")
    archive_path = tmp_path / "importable.zip"
    with zipfile.PyZipFile(archive_path, "w", optimize=0) as archive:
        archive.writepy(package)

    monkeypatch.syspath_prepend(str(archive_path))
    importlib.invalidate_caches()
    _forget_modules(package_name)
    try:
        imported = importlib.import_module(package_name)
        assert imported.ANSWER == 42
        assert str(archive_path) in imported.__file__
    finally:
        _forget_modules(package_name)


def test_optimize_level_is_applied_when_compiling_bytecode(tmp_path, monkeypatch):
    """optimize=1 会让被编译模块中的 __debug__ 为 False；这是 build-time 语义。"""

    module_name = "polyglot_optimized_zip_module"
    source = _write_source(tmp_path / f"{module_name}.py", "DEBUG = __debug__\n")
    archive_path = tmp_path / "optimized.zip"
    with zipfile.PyZipFile(archive_path, "w", optimize=1) as archive:
        archive.writepy(source)

    monkeypatch.syspath_prepend(str(archive_path))
    importlib.invalidate_caches()
    _forget_modules(module_name)
    try:
        imported = importlib.import_module(module_name)
        assert imported.DEBUG is False
    finally:
        _forget_modules(module_name)


def test_writepy_rejects_a_non_python_file(tmp_path):
    """单文件入口必须以 .py 结尾；目录入口则会自然忽略其他扩展名。"""

    source = _write_source(tmp_path / "notes.txt", "not a module\n")
    with zipfile.PyZipFile(tmp_path / "invalid.zip", "w") as archive:
        with pytest.raises(RuntimeError, match="must end with"):
            archive.writepy(source)


# ``python -m zipfile`` 的创建、列出、校验与提取工作流。
#
# 标准库提供轻量命令行入口，适合脚本和人工检查：``--create`` 递归加入文件/目录，
# ``--list`` 打印目录，``--test`` 读取并校验成员，``--extract`` 展开归档。它没有应用级
# 资源限制或交互式冲突策略；不可信输入仍应由调用方先执行与 Python API 相同的预检。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.zipfile.cli python.zipfile.python-m-zipfile
# polyglot-covers: python.zipfile.cli-create python.zipfile.cli-recursive-directory
# polyglot-covers: python.zipfile.cli-list python.zipfile.cli-test
# polyglot-covers: python.zipfile.cli-extract python.zipfile.cli-invalid-usage
# polyglot-covers: python.zipfile.cli-short-options python.zipfile.cli-long-options
# polyglot-covers: python.zipfile.cli-exit-status python.zipfile.cli-security-boundary



def _run_zipfile_cli(*arguments):
    """统一捕获输出；实际测试只会由仓库 Docker 入口调用容器内解释器。"""

    return subprocess.run(
        [sys.executable, "-m", "zipfile", *map(str, arguments)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_create_command_adds_a_file_and_a_directory_tree(tmp_path):
    """输入的 basename 成为归档根名称；目录本身及 descendants 都会加入。"""

    source_file = tmp_path / "standalone.txt"
    source_file.write_text("standalone", encoding="utf-8")
    source_dir = tmp_path / "assets"
    source_dir.mkdir()
    (source_dir / "nested.txt").write_text("nested", encoding="utf-8")
    archive_path = tmp_path / "created.zip"

    result = _run_zipfile_cli(
        "--create",
        archive_path,
        source_file,
        source_dir,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == [
            "standalone.txt",
            "assets/",
            "assets/nested.txt",
        ]
        assert archive.read("standalone.txt") == b"standalone"
        assert archive.read("assets/nested.txt") == b"nested"


def test_list_and_test_commands_report_archive_state(tmp_path):
    """-l 是人读表格；-t 成功固定输出 Done testing，process status 才适合自动化判定。"""

    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("member.txt", b"content")

    listed = _run_zipfile_cli("-l", archive_path)
    tested = _run_zipfile_cli("--test", archive_path)

    assert listed.returncode == 0
    assert "File Name" in listed.stdout
    assert "member.txt" in listed.stdout
    assert tested.returncode == 0
    assert tested.stdout.strip() == "Done testing"


def test_extract_command_expands_members_to_the_target_directory(tmp_path):
    """-e 接收 archive 和 output_dir 两个位置参数；父目录按成员名自动创建。"""

    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nested/member.txt", b"content")
    output_dir = tmp_path / "output"

    result = _run_zipfile_cli("--extract", archive_path, output_dir)

    assert result.returncode == 0
    assert result.stdout == ""
    assert (output_dir / "nested" / "member.txt").read_bytes() == b"content"


def test_missing_operation_returns_a_nonzero_status_and_usage():
    """四个 operation 互斥且必须选一个；argparse 把错误写到 stderr。"""

    result = _run_zipfile_cli()

    assert result.returncode != 0
    assert result.stdout == ""
    assert "usage:" in result.stderr.lower()
