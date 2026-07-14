"""121｜``lzma.open``/``LZMAFile`` 的文件、文本与多 stream 行为。

LZMAFile 的 surface 与 BZ2File 类似：支持 XZ/legacy/raw、binary/text wrapper、seek/peek，
读取时透明连接多个 streams。已有 fileobj 的 ownership 留给 caller，``w`` 也不会 truncate；
单个 LZMAFile 实例不是 thread-safe，并发使用要由应用加锁。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.lzma.open python.lzma.LZMAFile python.lzma.path-like
# polyglot-covers: python.lzma.binary-mode python.lzma.text-mode python.lzma.encoding
# polyglot-covers: python.lzma.file-format python.lzma.file-check python.lzma.file-preset
# polyglot-covers: python.lzma.exclusive-create python.lzma.append
# polyglot-covers: python.lzma.file-multistream python.lzma.fileobj-not-closed
# polyglot-covers: python.lzma.fileobj-write-does-not-truncate
# polyglot-covers: python.lzma.peek python.lzma.seek python.lzma.readinto
# polyglot-covers: python.lzma.iteration python.lzma.unsupported-detach
# polyglot-covers: python.lzma.unsupported-truncate python.lzma.thread-unsafe

import io
import lzma

import pytest


def test_binary_open_round_trips_xz_at_a_path_like_object(tmp_path):
    """默认写 FORMAT_XZ；PathLike 直接传入，不依赖 filename extension 选择格式。"""

    path = tmp_path / "payload.xz"
    original = b"binary\x00payload" * 50
    with lzma.open(path, "wb", preset=1) as stream:
        assert stream.write(original) == len(original)

    assert path.read_bytes().startswith(b"\xfd7zXZ\x00")
    with lzma.open(path, "rb") as stream:
        assert stream.read() == original


def test_file_format_can_be_legacy_alone_independent_of_suffix(tmp_path):
    """format 参数而非 .lzma suffix 决定 writer；reader FORMAT_AUTO 可识别。"""

    path = tmp_path / "legacy.data"
    with lzma.open(path, "wb", format=lzma.FORMAT_ALONE) as stream:
        stream.write(b"legacy")

    with lzma.open(path, "rb", format=lzma.FORMAT_AUTO) as stream:
        assert stream.read() == b"legacy"


def test_text_mode_applies_encoding_and_newline_translation(tmp_path):
    """wt/rt 返回 TextIOWrapper；LZMAFile 本体只处理 binary bytes。"""

    path = tmp_path / "text.xz"
    with lzma.open(path, "wt", encoding="utf-8", newline="\n") as stream:
        stream.write("甲\n乙\n")

    with lzma.open(path, "rt", encoding="utf-8", newline=None) as stream:
        assert stream.readlines() == ["甲\n", "乙\n"]


def test_encoding_argument_is_rejected_in_binary_mode(tmp_path):
    """encoding/errors/newline 不能和 binary mode 混用。"""

    with pytest.raises(ValueError, match="encoding"):
        lzma.open(tmp_path / "binary.xz", "wb", encoding="utf-8")


def test_exclusive_create_refuses_an_existing_path(tmp_path):
    """x/xb/xt 与 ordinary open 一样执行 fail-if-exists。"""

    path = tmp_path / "existing.xz"
    path.write_bytes(b"exists")

    with pytest.raises(FileExistsError):
        lzma.open(path, "xb")


def test_append_adds_a_new_stream_and_reader_combines_content(tmp_path):
    """append 不重写旧 XZ container，而是增加独立 stream。"""

    path = tmp_path / "members.xz"
    with lzma.open(path, "wb") as stream:
        stream.write(b"first")
    first_stream_size = path.stat().st_size
    with lzma.open(path, "ab") as stream:
        stream.write(b"second")

    assert path.read_bytes()[first_stream_size : first_stream_size + 6] == b"\xfd7zXZ\x00"
    with lzma.open(path, "rb") as stream:
        assert stream.read() == b"firstsecond"


def test_file_object_w_mode_preserves_prefix_and_does_not_close_owner():
    """fileobj ``w`` 不 truncate；LZMAFile.close 也不关闭 caller-owned stream。"""

    prefix = b"outer-prefix"
    buffer = io.BytesIO(prefix)
    buffer.seek(0, io.SEEK_END)
    with lzma.LZMAFile(buffer, "w", preset=0) as stream:
        stream.write(b"compressed")

    assert buffer.closed is False
    assert buffer.getvalue().startswith(prefix + b"\xfd7zXZ\x00")
    assert lzma.decompress(buffer.getvalue()[len(prefix) :]) == b"compressed"


def test_peek_ignores_size_and_keeps_uncompressed_position(tmp_path):
    """size 只是兼容参数且被忽略；返回量未指定，tell 不前进。"""

    path = tmp_path / "peek.xz"
    path.write_bytes(lzma.compress(b"abcdef"))
    with lzma.LZMAFile(path, "rb") as stream:
        assert stream.tell() == 0
        assert stream.peek(1).startswith(b"a")
        assert stream.tell() == 0
        assert stream.read(2) == b"ab"


def test_buffered_methods_support_seek_readinto_and_iteration(tmp_path):
    """LZMAFile 提供常用 BufferedIOBase 操作，但同一实例并发调用需外部 lock。"""

    path = tmp_path / "buffered.xz"
    path.write_bytes(lzma.compress(b"first\nsecond\n"))
    with lzma.LZMAFile(path, "rb") as stream:
        assert stream.seek(6) == 6
        target = bytearray(6)
        assert stream.readinto(target) == 6
        assert target == b"second"
        stream.seek(0)
        assert list(stream) == [b"first\n", b"second\n"]


def test_detach_and_truncate_are_not_supported(tmp_path):
    """compressed wrapper 不能 detach raw stream，也不能原地 truncate。"""

    path = tmp_path / "unsupported.xz"
    with lzma.LZMAFile(path, "wb") as stream:
        with pytest.raises(io.UnsupportedOperation):
            stream.detach()
        with pytest.raises(io.UnsupportedOperation):
            stream.truncate()
