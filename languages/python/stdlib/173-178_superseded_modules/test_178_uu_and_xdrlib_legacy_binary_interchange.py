"""178｜uu 与 xdrlib：遗留文本封装和 XDR 二进制表示。

uu 把二进制分行编码为历史邮件/新闻系统可传输的 ASCII；xdrlib 按
RFC 1014 风格的大端、四字节对齐规则打包数据。案例覆盖流与路径工作流、
损坏输入、目录穿越防护，以及 XDR 标量、变长值、列表、数组和
游标协议。新协议通常应选用仍在维护且自带模式定义、大小限制和
安全审计的序列化方案。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.uu python.uu.encode python.uu.decode
# polyglot-covers: python.uu.file-like python.uu.path-like python.uu.header
# polyglot-covers: python.uu.mode python.uu.name python.uu.backtick
# polyglot-covers: python.uu.line-chunks python.uu.quiet python.uu.error
# polyglot-covers: python.uu.truncated-input python.uu.no-overwrite
# polyglot-covers: python.uu.directory-traversal
# polyglot-covers: python.stdlib.xdrlib python.xdrlib.packer python.xdrlib.unpacker
# polyglot-covers: python.xdrlib.uint-int-enum-bool
# polyglot-covers: python.xdrlib.hyper python.xdrlib.float-double
# polyglot-covers: python.xdrlib.fixed-string python.xdrlib.opaque
# polyglot-covers: python.xdrlib.four-byte-padding
# polyglot-covers: python.xdrlib.list python.xdrlib.array python.xdrlib.fixed-array
# polyglot-covers: python.xdrlib.position python.xdrlib.reset python.xdrlib.done
# polyglot-covers: python.xdrlib.eof python.xdrlib.conversion-error

import binascii
import io
import os
import struct
import uu
import xdrlib

import pytest


def test_uu_bytes_stream_round_trip_preserves_payload_header_name_and_mode():
    payload = bytes(range(128))
    encoded = io.BytesIO()

    assert uu.encode(
        io.BytesIO(payload),
        encoded,
        name="lesson.bin",
        mode=0o640,
    ) is None

    wire = encoded.getvalue()
    assert wire.startswith(b"begin 640 lesson.bin\n")
    assert wire.endswith(b" \nend\n")

    decoded = io.BytesIO()
    assert uu.decode(io.BytesIO(wire), decoded) is None
    assert decoded.getvalue() == payload
    # file-like 输出的权限无法修改；mode 只在 out_file 是路径时交给 chmod。


def test_uu_backtick_uses_an_alternate_zero_length_line():
    ordinary = io.BytesIO()
    backtick = io.BytesIO()

    uu.encode(io.BytesIO(b""), ordinary, name="empty", backtick=False)
    uu.encode(io.BytesIO(b""), backtick, name="empty", backtick=True)

    assert ordinary.getvalue().endswith(b" \nend\n")
    assert backtick.getvalue().endswith(b"`\nend\n")
    decoded = io.BytesIO()
    uu.decode(io.BytesIO(backtick.getvalue()), decoded)
    assert decoded.getvalue() == b""


def test_uu_path_inputs_derive_the_name_and_mode_and_close_internal_files(tmp_path):
    source = tmp_path / "payload.bin"
    encoded = tmp_path / "payload.uu"
    decoded = tmp_path / "decoded.bin"
    source.write_bytes(b"path workflow")
    source.chmod(0o640)

    uu.encode(str(source), str(encoded))
    header = encoded.read_bytes().splitlines()[0]
    uu.decode(str(encoded), str(decoded))

    assert header == b"begin 640 payload.bin"
    assert decoded.read_bytes() == b"path workflow"
    if os.name == "posix":
        assert decoded.stat().st_mode & 0o777 == 0o640
    # encode/decode 接受 str 路径并自行关闭；
    # Path 本身在 3.10 不是该接口的路径分支。


def test_uu_encoder_reads_at_most_45_payload_bytes_per_data_line():
    payload = b"x" * 91
    encoded = io.BytesIO()
    uu.encode(io.BytesIO(payload), encoded, name="chunks")

    data_lines = encoded.getvalue().splitlines()[1:-2]

    assert len(data_lines) == 3
    assert [len(binascii.a2b_uu(line)) for line in data_lines] == [45, 45, 1]
    # 行首编码了本行原始长度；45 字节会展开成 60 个可传输字符。


def test_uu_header_escapes_newlines_in_the_embedded_name():
    encoded = io.BytesIO()
    uu.encode(
        io.BytesIO(b"data"),
        encoded,
        name="line\none\rtwo.bin",
    )

    assert encoded.getvalue().splitlines()[0] == b"begin 666 line\\none\\rtwo.bin"


def recoverable_broken_uu_stream():
    line = binascii.b2a_uu(b"recoverable").rstrip(b"\n") + b"!\n"
    return b"begin 600 data.bin\n" + line + b" \nend\n"


def test_uu_decode_warns_for_recoverable_broken_lines_unless_quiet(capsys):
    noisy_output = io.BytesIO()
    uu.decode(io.BytesIO(recoverable_broken_uu_stream()), noisy_output)
    warning = capsys.readouterr().err

    quiet_output = io.BytesIO()
    uu.decode(
        io.BytesIO(recoverable_broken_uu_stream()),
        quiet_output,
        quiet=True,
    )

    assert noisy_output.getvalue() == b"recoverable"
    assert quiet_output.getvalue() == b"recoverable"
    assert "Warning:" in warning
    assert capsys.readouterr().err == ""
    # quiet 只压制兼容性警告，不会把无法恢复的结构错误变成成功。


@pytest.mark.parametrize(
    ("wire", "message"),
    [
        (b"not a uu stream\n", "No valid begin line"),
        (b"begin 644 file.bin\n#0V%T\n", "Truncated input file"),
    ],
)
def test_uu_decode_reports_missing_header_and_missing_end_marker(wire, message):
    with pytest.raises(uu.Error, match=message):
        uu.decode(io.BytesIO(wire), io.BytesIO())


def test_uu_decode_will_not_overwrite_an_implicit_output_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    existing = tmp_path / "existing.bin"
    existing.write_bytes(b"keep me")
    wire = b"begin 600 existing.bin\n \nend\n"

    with pytest.raises(uu.Error, match="Cannot overwrite existing file"):
        uu.decode(io.BytesIO(wire))

    assert existing.read_bytes() == b"keep me"


@pytest.mark.parametrize("embedded_name", ["../escape.bin", "/absolute.bin"])
def test_uu_decode_refuses_directory_traversal_for_implicit_outputs(embedded_name):
    wire = f"begin 600 {embedded_name}\n \nend\n".encode("ascii")

    with pytest.raises(uu.Error, match="directory traversal"):
        uu.decode(io.BytesIO(wire))
    # 显式 out_file 由调用者决定；
    # 防穿越检查针对不可信头部自动选出的文件名。


def test_xdr_integer_boolean_enum_and_hyper_values_round_trip_in_big_endian_order():
    packer = xdrlib.Packer()
    packer.pack_uint(0x01020304)
    packer.pack_int(-2)
    packer.pack_enum(7)
    packer.pack_bool("")
    packer.pack_bool("truthy")
    packer.pack_uhyper(0x0102030405060708)
    packer.pack_hyper(-1)

    wire = packer.get_buffer()
    assert wire[:4] == b"\x01\x02\x03\x04"

    unpacker = xdrlib.Unpacker(wire)
    assert unpacker.unpack_uint() == 0x01020304
    assert unpacker.unpack_int() == -2
    assert unpacker.unpack_enum() == 7
    assert unpacker.unpack_bool() is False
    assert unpacker.unpack_bool() is True
    assert unpacker.unpack_uhyper() == 0x0102030405060708
    assert unpacker.unpack_hyper() == -1
    assert unpacker.done() is None
    # bool 打包依据真值，但线上只写 0/1；
    # hyper 由两个无符号 32 位大端字组成。


def test_xdr_float_and_double_use_network_byte_order():
    packer = xdrlib.Packer()
    packer.pack_float(1.5)
    packer.pack_double(-2.25)

    assert packer.get_buffer() == struct.pack(">fd", 1.5, -2.25)

    unpacker = xdrlib.Unpacker(packer.get_buffer())
    assert unpacker.unpack_float() == pytest.approx(1.5)
    assert unpacker.unpack_double() == pytest.approx(-2.25)
    unpacker.done()


def test_xdr_fixed_strings_truncate_or_zero_pad_to_a_four_byte_boundary():
    packer = xdrlib.Packer()
    packer.pack_fstring(5, b"abcdefgh")
    packer.pack_fopaque(6, b"xy")

    assert packer.get_buffer() == b"abcde\0\0\0xy\0\0\0\0\0\0"

    unpacker = xdrlib.Unpacker(packer.get_buffer())
    assert unpacker.unpack_fstring(5) == b"abcde"
    assert unpacker.unpack_fopaque(6) == b"xy\0\0\0\0"
    unpacker.done()
    # fstring 的 n 是协议固定宽度：过长会截断，过短会补零，
    # 再整体补到 4 的倍数。


def test_xdr_variable_strings_prefix_the_unpadded_length_and_offer_aliases():
    packer = xdrlib.Packer()
    packer.pack_string(b"abc")
    packer.pack_opaque(b"four")
    packer.pack_bytes(b"12345")

    wire = packer.get_buffer()
    assert wire[:8] == b"\0\0\0\x03abc\0"

    unpacker = xdrlib.Unpacker(wire)
    assert unpacker.unpack_string() == b"abc"
    assert unpacker.unpack_opaque() == b"four"
    assert unpacker.unpack_bytes() == b"12345"
    unpacker.done()
    # 长度前缀不含 padding；调用者取得原字节，不会看到对齐零字节。


def test_xdr_list_uses_presence_markers_while_array_uses_a_count_prefix():
    packer = xdrlib.Packer()
    packer.pack_list([10, 20], packer.pack_int)
    packer.pack_array([30, 40], packer.pack_int)
    packer.pack_farray(2, [50, 60], packer.pack_int)

    expected_list_prefix = struct.pack(">LiLiL", 1, 10, 1, 20, 0)
    assert packer.get_buffer().startswith(expected_list_prefix)

    unpacker = xdrlib.Unpacker(packer.get_buffer())
    assert unpacker.unpack_list(unpacker.unpack_int) == [10, 20]
    assert unpacker.unpack_array(unpacker.unpack_int) == [30, 40]
    assert unpacker.unpack_farray(2, unpacker.unpack_int) == [50, 60]
    unpacker.done()


def test_xdr_fixed_array_requires_exactly_the_declared_item_count():
    packer = xdrlib.Packer()

    with pytest.raises(ValueError, match="wrong array size"):
        packer.pack_farray(2, [1], packer.pack_int)


def test_xdr_buffers_reset_and_position_allow_explicit_reuse_and_rewind():
    packer = xdrlib.Packer()
    packer.pack_uint(1)
    assert packer.get_buf() == packer.get_buffer() == b"\0\0\0\1"
    packer.reset()
    packer.pack_uint(2)
    assert packer.get_buffer() == b"\0\0\0\2"

    unpacker = xdrlib.Unpacker(packer.get_buffer() + b"tail")
    assert unpacker.get_buffer().endswith(b"tail")
    start = unpacker.get_position()
    assert unpacker.unpack_uint() == 2
    assert unpacker.get_position() == 4
    unpacker.set_position(start)
    assert unpacker.unpack_uint() == 2
    with pytest.raises(xdrlib.Error, match="unextracted data remains"):
        unpacker.done()

    unpacker.reset(b"\0\0\0\x03")
    assert unpacker.unpack_uint() == 3
    unpacker.done()


def test_xdr_short_input_raises_eof_and_bad_values_raise_conversion_error():
    with pytest.raises(EOFError):
        xdrlib.Unpacker(b"\0\0").unpack_uint()

    packer = xdrlib.Packer()
    with pytest.raises(xdrlib.ConversionError):
        packer.pack_uint(-1)
    with pytest.raises(xdrlib.ConversionError):
        packer.pack_int(2**40)

    invalid_list_marker = struct.pack(">L", 2)
    with pytest.raises(xdrlib.ConversionError, match="0 or 1 expected"):
        xdrlib.Unpacker(invalid_list_marker).unpack_list(lambda: None)


def test_xdr_error_keeps_a_public_message_and_readable_string_forms():
    error = xdrlib.Error("broken record")

    assert error.msg == "broken record"
    assert str(error) == "broken record"
    assert repr(error) == "'broken record'"
