"""124｜ZIP 成员流、``ZipInfo`` 元数据、重复名称与完整性检查。

中央目录允许按名称快速定位，但名称不保证唯一；需要区分同名成员时，应把 ``ZipInfo``
对象传给 ``open``/``read``。写成员流适合未知长度的数据，读成员流支持常用 buffered
操作；归档关闭前必须先关闭活动 writer。CRC 检查可发现内容损坏，但不是恶意输入防线。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import io
import struct
import zipfile

import pytest


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
            with pytest.raises(ValueError, match="writing handle"):
                archive.read("ready.txt")
            with pytest.raises(ValueError, match="writing handle"):
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
