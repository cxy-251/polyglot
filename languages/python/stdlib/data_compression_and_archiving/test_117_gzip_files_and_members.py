"""117｜``gzip`` one-shot、压缩文件、member 与可复现 header。

gzip 在 DEFLATE 外增加 filename/mtime/checksum 等 file wrapper。``gzip.open`` 支持 binary
和 text mode；append 会增加 gzip member，reader 自动拼接 member 的解压内容。``GzipFile``
关闭时故意不关闭传入的 fileobj，便于从 BytesIO 取结果或继续写外层数据。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.gzip.compress python.gzip.decompress python.gzip.one-shot
# polyglot-covers: python.gzip.mtime python.gzip.reproducible-output python.gzip.header
# polyglot-covers: python.gzip.multi-member python.gzip.concatenated-streams
# polyglot-covers: python.gzip.open python.gzip.binary-mode python.gzip.path-like
# polyglot-covers: python.gzip.text-mode python.gzip.encoding python.gzip.newline
# polyglot-covers: python.gzip.append python.gzip.exclusive-create
# polyglot-covers: python.gzip.GzipFile python.gzip.fileobj-not-closed python.gzip.name
# polyglot-covers: python.gzip.peek python.gzip.tell python.gzip.seek
# polyglot-covers: python.gzip.read1 python.gzip.readinto python.gzip.iteration
# polyglot-covers: python.gzip.bytes-like-write python.gzip.truncate-unsupported
# polyglot-covers: python.gzip.BadGzipFile python.gzip.EOFError python.gzip.invalid-file
# polyglot-covers: python.gzip.binary-encoding-error python.gzip.compression-level

import gzip
import io
import struct

import pytest


def test_one_shot_compress_and_decompress_round_trip_bytes():
    """完整 payload 已在内存时，convenience functions 避免手动管理 file object。"""

    original = b"gzip one-shot" * 100
    payload = gzip.compress(original)

    assert isinstance(payload, bytes)
    assert payload.startswith(b"\x1f\x8b")
    assert gzip.decompress(payload) == original


@pytest.mark.parametrize("level", [0, 1, 6, 9])
def test_documented_compression_levels_preserve_content(level):
    """0–9 只改变压缩取舍；gzip 默认 level 9，与 zlib one-shot 默认不同。"""

    original = b"level semantics" * 100

    assert gzip.decompress(gzip.compress(original, compresslevel=level)) == original


def test_fixed_mtime_makes_repeated_output_reproducible():
    """默认 mtime 取当前时间；构建 artifact 应显式固定为 0 或 source timestamp。"""

    original = b"reproducible artifact"
    first = gzip.compress(original, mtime=0)
    second = gzip.compress(original, mtime=0)

    assert first == second
    assert struct.unpack("<I", first[4:8]) == (0,)


def test_numeric_mtime_is_stored_as_unsigned_header_seconds():
    """gzip header 的 4-byte MTIME 可由 reader 暴露；它不是 filesystem mtime 自动同步。"""

    payload = gzip.compress(b"payload", mtime=1_234_567)

    assert struct.unpack("<I", payload[4:8]) == (1_234_567,)


def test_one_shot_decompress_combines_concatenated_members():
    """gzip 允许多个 members 直接拼接；解压结果是各 member 内容的连接。"""

    payload = gzip.compress(b"first", mtime=0) + gzip.compress(
        b"second", mtime=0
    )

    assert gzip.decompress(payload) == b"firstsecond"


def test_binary_open_round_trips_a_path_like_file(tmp_path):
    """gzip.open 接受 PathLike，读写视角像 ordinary binary file。"""

    path = tmp_path / "payload.gz"
    original = b"binary\x00payload" * 20
    with gzip.open(path, "wb", compresslevel=6) as stream:
        assert stream.write(original) == len(original)

    assert path.read_bytes().startswith(b"\x1f\x8b")
    with gzip.open(path, "rb") as stream:
        assert stream.read() == original


def test_text_mode_wraps_gzip_file_with_encoding_and_newline_handling(tmp_path):
    """wt/rt 使用 TextIOWrapper；encoding/newline 只属于 text mode。"""

    path = tmp_path / "text.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as stream:
        stream.write("第一行\n第二行\n")

    with gzip.open(path, "rt", encoding="utf-8", newline=None) as stream:
        assert stream.readlines() == ["第一行\n", "第二行\n"]


def test_encoding_argument_is_rejected_in_binary_mode(tmp_path):
    """binary stream 只接受 bytes；提供 encoding 通常意味着 mode 写错。"""

    path = tmp_path / "binary.gz"

    with pytest.raises(ValueError, match="encoding"):
        gzip.open(path, "wb", encoding="utf-8")


def test_exclusive_create_refuses_to_replace_an_existing_file(tmp_path):
    """x/xb/xt 是原子 fail-if-exists 语义，适合避免覆盖 artifact。"""

    path = tmp_path / "existing.gz"
    path.write_bytes(b"already exists")

    with pytest.raises(FileExistsError):
        gzip.open(path, "xb")


def test_append_mode_adds_a_member_and_reader_combines_them(tmp_path):
    """append 不重写既有 compressed data，而是在末尾创建新 gzip member。"""

    path = tmp_path / "members.gz"
    with gzip.open(path, "wb") as stream:
        stream.write(b"first\n")
    first_member_size = path.stat().st_size
    with gzip.open(path, "ab") as stream:
        stream.write(b"second\n")

    assert path.read_bytes()[first_member_size : first_member_size + 2] == b"\x1f\x8b"
    with gzip.open(path, "rb") as stream:
        assert stream.read() == b"first\nsecond\n"


def test_gzipfile_close_keeps_caller_owned_file_object_open():
    """ownership 不转移给 GzipFile；close 完成 trailer 后仍可读取/追加 underlying BytesIO。"""

    buffer = io.BytesIO()
    stream = gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0)
    stream.write(b"compressed content")
    stream.close()

    assert buffer.closed is False
    payload = buffer.getvalue()
    assert gzip.decompress(payload) == b"compressed content"
    buffer.write(b"outer trailer")
    assert buffer.getvalue().endswith(b"outer trailer")


def test_reading_header_populates_mtime_and_fileobj_stays_open():
    """reader.mtime 初始 None；读到 member header 后变为该 member 的 timestamp。"""

    buffer = io.BytesIO(gzip.compress(b"content", mtime=123))
    stream = gzip.GzipFile(fileobj=buffer, mode="rb")
    assert stream.mtime is None

    assert stream.read(1) == b"c"
    assert stream.mtime == 123
    stream.close()
    assert buffer.closed is False


def test_gzipfile_name_reflects_original_path_without_resolution(tmp_path):
    """name 来自 os.fspath(input)，不会 resolve、expanduser 或改成 member header filename。"""

    path = tmp_path / "named.gz"
    with gzip.GzipFile(filename=path, mode="wb", mtime=0) as stream:
        assert stream.name == str(path)
        stream.write(b"content")


def test_peek_does_not_advance_uncompressed_position():
    """peek 返回数量可多可少，唯一稳定保证是 GzipFile.tell() 不前进。"""

    stream = gzip.GzipFile(
        fileobj=io.BytesIO(gzip.compress(b"abcdef", mtime=0)),
        mode="rb",
    )
    try:
        assert stream.tell() == 0
        preview = stream.peek(2)
        assert preview.startswith(b"ab")
        assert stream.tell() == 0
        assert stream.read(2) == b"ab"
    finally:
        stream.close()


def test_buffered_interface_supports_seek_read1_readinto_and_iteration(tmp_path):
    """GzipFile 模拟 buffered binary file，可随机定位解压位置，但不支持 truncate。"""

    path = tmp_path / "buffered.gz"
    with gzip.open(path, "wb") as stream:
        stream.write(b"first\nsecond\nthird\n")

    with gzip.open(path, "rb") as stream:
        assert stream.readline() == b"first\n"
        assert stream.tell() == len(b"first\n")
        assert stream.seek(0) == 0
        assert stream.read1(5) == b"first"
        target = bytearray(2)
        assert stream.readinto(target) == 2
        assert target == b"\ns"
        stream.seek(0)
        assert list(stream) == [b"first\n", b"second\n", b"third\n"]


def test_gzipfile_accepts_arbitrary_bytes_like_writes():
    """3.5 起 write 接受 buffer protocol，不必先复制 memoryview/bytearray 为 bytes。"""

    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as stream:
        stream.write(bytearray(b"mutable"))
        stream.write(memoryview(b" view"))

    assert gzip.decompress(buffer.getvalue()) == b"mutable view"


def test_truncate_is_not_supported_by_gzipfile(tmp_path):
    """压缩 stream 无法像普通文件原地截短；需重新生成目标 gzip。"""

    path = tmp_path / "truncate.gz"
    with gzip.open(path, "wb") as stream:
        with pytest.raises(io.UnsupportedOperation):
            stream.truncate()


def test_invalid_magic_raises_bad_gzip_file():
    """BadGzipFile 是 OSError subclass；损坏类型不同也可能出现 EOFError/zlib.error。"""

    assert issubclass(gzip.BadGzipFile, OSError)
    with pytest.raises(gzip.BadGzipFile):
        gzip.decompress(b"not a gzip stream")


def test_truncated_member_can_raise_eof_error():
    """magic/header 合法但 trailer 不完整时，错误与完全错误的 magic 不同。"""

    payload = gzip.compress(b"content" * 100, mtime=0)

    with pytest.raises(EOFError):
        gzip.decompress(payload[:-4])
