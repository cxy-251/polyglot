"""123｜``zipfile`` 创建归档、压缩选择与文件模式。

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
