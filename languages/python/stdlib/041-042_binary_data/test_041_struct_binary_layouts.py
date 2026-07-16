"""041｜``struct`` 固定二进制布局、buffer 读写与记录解析示例。

``struct`` 解决的是“已约定字段布局的 Python 值与 bytes 互转”，主要用于外部
文件/网络协议，或与同一平台上的 C 内存布局交互。前一种场景应显式固定字节序、
字段大小和 padding；后一种场景才适合原生 ``@`` 格式。

本文件用带字段含义的小记录说明格式字符串，而不是穷举所有数值边界。``struct``
不负责文本编码、消息分帧、校验或版本兼容，这些协议责任会在最后的长度前缀案例中
明确展示。
"""

# polyglot-covers: python.stdlib.struct python.struct.pack python.struct.unpack
# polyglot-covers: python.struct.calcsize python.struct.byte-order
# polyglot-covers: python.struct.native-layout python.struct.standard-layout
# polyglot-covers: python.struct.alignment python.struct.padding
# polyglot-covers: python.struct.integer-formats python.struct.__index__
# polyglot-covers: python.struct.bool-format python.struct.float-formats
# polyglot-covers: python.struct.char-bytes-pascal-formats
# polyglot-covers: python.struct.native-only-formats
# polyglot-covers: python.struct.pack_into python.struct.unpack_from
# polyglot-covers: python.struct.iter_unpack python.struct.Struct
# polyglot-covers: python.struct.buffer-protocol python.struct.error-boundaries
# polyglot-covers: python.struct.manual-framing

import math
import struct
import sys

import pytest


def test_network_record_has_an_explicit_stable_layout():
    """外部格式显式用 ``!``；字段顺序和大小不会跟随当前机器的 C ABI。"""

    # 设备编号 uint32、温度 int16、两字节状态码，共 8 字节。
    record_format = "!Ih2s"
    record = struct.pack(record_format, 0x01020304, -25, b"OK")

    assert isinstance(record, bytes)
    assert struct.calcsize(record_format) == 8
    assert record == b"\x01\x02\x03\x04\xff\xe7OK"
    assert struct.unpack(record_format, record) == (0x01020304, -25, b"OK")

    # 即使只有一个字段，unpack 的返回值仍是 tuple，而不是裸值。
    assert struct.unpack("!H", b"\x01\xbb") == (443,)


def test_byte_order_prefixes_make_integer_representation_explicit():
    """``<`` 固定小端，``>`` / ``!`` 固定大端，``=`` 只跟随原生字节序。"""

    value = 0x01020304

    assert struct.pack("<I", value) == b"\x04\x03\x02\x01"
    assert struct.pack(">I", value) == b"\x01\x02\x03\x04"
    assert struct.pack("!I", value) == struct.pack(">I", value)

    native_order_standard_size = "<I" if sys.byteorder == "little" else ">I"
    assert struct.pack("=I", value) == struct.pack(
        native_order_standard_size,
        value,
    )
    assert struct.calcsize("=I") == 4


def test_missing_prefix_means_native_layout_including_native_alignment():
    """无前缀等同 ``@``；大小和内部 padding 由解释器构建所用的 C ABI 决定。"""

    assert struct.pack("bI", 1, 2) == struct.pack("@bI", 1, 2)
    assert struct.calcsize("bI") == struct.calcsize("@bI")

    # 标准格式不自动对齐，所以一字节整数加四字节整数必定是 5 字节。
    assert struct.calcsize("=bI") == 5
    assert struct.calcsize("@bI") >= 1 + struct.calcsize("@I")

    # 原生格式只自动填充成员之间，不会自动把结构末尾补齐到最大成员对齐。
    native_without_tail_alignment = struct.calcsize("@Ib")
    native_with_explicit_tail_alignment = struct.calcsize("@Ib0I")
    assert native_with_explicit_tail_alignment >= native_without_tail_alignment

    encoded = struct.pack("@Ib0I", 0x1234, 7)
    assert len(encoded) == native_with_explicit_tail_alignment
    assert struct.unpack("@Ib0I", encoded) == (0x1234, 7)


def test_standard_formats_need_explicit_padding_bytes():
    """非原生格式不自动 padding；``x`` 明确写出协议保留位且不消费参数。"""

    record_format = ">BxH"
    encoded = struct.pack(record_format, 7, 0x1234)

    assert struct.calcsize(record_format) == 4
    assert encoded == b"\x07\x00\x12\x34"
    assert struct.unpack(record_format, encoded) == (7, 0x1234)

    # 标准格式中的 zero-repeat 不负责尾部对齐；需要几个字节就显式写几个 x。
    assert struct.calcsize(">H0I") == 2
    assert struct.calcsize(">H2x") == 4


def test_repeat_counts_and_whitespace_keep_the_value_arity_visible():
    """数字代码前的计数表示重复字段；格式之间的空白可读性友好。"""

    compact = struct.pack(">2HB", 8000, 8001, 3)
    spaced = struct.pack("> 2H B", 8000, 8001, 3)

    assert compact == spaced
    assert compact == struct.pack(">HHB", 8000, 8001, 3)
    assert struct.unpack("> 2H B", spaced) == (8000, 8001, 3)

    # 重复计数与格式代码之间不能插入空白，否则计数失去归属。
    with pytest.raises(struct.error):
        struct.calcsize(">2 H")


def test_integer_fields_check_ranges_and_use_the_index_protocol():
    """整数格式接受 ``__index__`` 的精确整数语义，不接受仅能转成 int 的对象。"""

    class Port:
        def __init__(self, number):
            self.number = number

        def __index__(self):
            return self.number

    class IntOnly:
        def __int__(self):
            return 7

    assert struct.pack("!H", Port(443)) == b"\x01\xbb"

    with pytest.raises(struct.error):
        struct.pack("!B", 256)
    with pytest.raises(struct.error):
        struct.pack("!B", -1)
    with pytest.raises(struct.error):
        struct.pack("!H", 1.5)
    with pytest.raises(struct.error):
        struct.pack("!H", IntOnly())


def test_signed_and_unsigned_codes_describe_distinct_value_domains():
    """相同位宽的大小写代码共享字节数，但有符号范围和编码不同。"""

    assert struct.calcsize("!bBhHiIqQ") == 30
    assert struct.unpack("!bB", struct.pack("!bB", -1, 255)) == (-1, 255)

    # 0xff 对 signed char 是 -1，对 unsigned char 是 255。
    assert struct.unpack("!b", b"\xff") == (-1,)
    assert struct.unpack("!B", b"\xff") == (255,)


def test_question_mark_packs_truth_values_not_only_bool_instances():
    """``?`` 打包前调用真假值协议，解包结果则规范化成真正的 bool。"""

    calls = []

    class FeatureFlag:
        def __bool__(self):
            calls.append("checked")
            return True

    encoded = struct.pack("!???", False, [], FeatureFlag())

    assert encoded == b"\x00\x00\x01"
    assert struct.unpack("!???", encoded) == (False, False, True)
    assert calls == ["checked"]


def test_fixed_bytes_and_repeated_chars_have_different_argument_shapes():
    """``4s`` 是一个四字节字段；``4c`` 是四个各长一字节的独立字段。"""

    one_field = struct.pack("!4s", b"PY3!")
    four_fields = struct.pack("!4c", b"P", b"Y", b"3", b"!")

    assert one_field == four_fields == b"PY3!"
    assert struct.unpack("!4s", one_field) == (b"PY3!",)
    assert struct.unpack("!4c", four_fields) == (b"P", b"Y", b"3", b"!")

    # s 字段会截断或以 NUL 补足；解包不会替调用方删除协议 padding。
    assert struct.pack("!4s", b"python") == b"pyth"
    assert struct.pack("!4s", b"go") == b"go\x00\x00"
    assert struct.unpack("!4s", b"go\x00\x00") == (b"go\x00\x00",)


def test_character_and_bytes_fields_require_bytes_like_values_not_text():
    """``struct`` 不猜测字符编码；调用方必须先把 str 明确编码成 bytes。"""

    encoded_text = "猫".encode("utf-8")
    assert struct.pack("!3s", encoded_text) == b"\xe7\x8c\xab"
    assert struct.unpack("!3s", encoded_text)[0].decode("utf-8") == "猫"

    with pytest.raises(struct.error):
        struct.pack("!c", "A")
    with pytest.raises(struct.error):
        struct.pack("!2s", "AB")
    with pytest.raises(struct.error):
        struct.pack("!2c", b"AB")


def test_pascal_string_has_a_length_byte_inside_a_fixed_width_field():
    """``p`` 把长度和内容放进固定总宽度；它不是通用的无限长字符串格式。"""

    encoded = struct.pack("!8p", b"cat")

    assert len(encoded) == 8
    assert encoded == b"\x03cat\x00\x00\x00\x00"
    assert struct.unpack("!8p", encoded) == (b"cat",)

    # 8p 最多保存 count - 1，即 7 个内容字节。
    truncated = struct.pack("!8p", b"abcdefghij")
    assert truncated == b"\x07abcdefg"
    assert struct.unpack("!8p", truncated) == (b"abcdefg",)


@pytest.mark.parametrize(
    ("code", "relative_tolerance"),
    [("e", 1e-3), ("f", 1e-6), ("d", 1e-15)],
)
def test_float_formats_have_fixed_ieee_widths_and_need_approximation(
    code,
    relative_tolerance,
):
    """binary16/32/64 宽度固定，但十进制 0.1 通常不能被二进制浮点精确表示。"""

    expected_sizes = {"e": 2, "f": 4, "d": 8}
    encoded = struct.pack(">" + code, 0.1)
    decoded, = struct.unpack(">" + code, encoded)

    assert len(encoded) == expected_sizes[code]
    assert decoded == pytest.approx(0.1, rel=relative_tolerance)


def test_float_formats_preserve_infinity_and_nan_categories():
    """NaN 不能用相等判断；解包后应通过数值分类函数检查其语义。"""

    positive_infinity, = struct.unpack(">f", struct.pack(">f", math.inf))
    not_a_number, = struct.unpack(">d", struct.pack(">d", math.nan))

    assert positive_infinity == math.inf
    assert math.isnan(not_a_number)
    assert not_a_number != not_a_number


def test_pointer_and_size_t_codes_are_native_layout_only():
    """``n``、``N``、``P`` 服务本机 C 互操作，不能进入可移植文件/网络格式。"""

    native_values = {"n": -1, "N": 1, "P": 0}
    for code, value in native_values.items():
        encoded = struct.pack("@" + code, value)
        assert len(encoded) == struct.calcsize("@" + code)
        assert struct.unpack("@" + code, encoded) == (value,)

        for standard_prefix in "=<>!":
            with pytest.raises(struct.error):
                struct.calcsize(standard_prefix + code)


def test_pack_into_writes_only_the_selected_writable_buffer_region():
    """pack_into 避免先造中间 bytes；目标必须可写且从 offset 起有足够空间。"""

    buffer = bytearray(b"\xaa" * 12)

    assert struct.pack_into("!Hh", buffer, 4, 500, -20) is None
    assert buffer[:4] == b"\xaa" * 4
    assert buffer[4:8] == struct.pack("!Hh", 500, -20)
    assert buffer[8:] == b"\xaa" * 4

    # bytearray 和 memoryview 都实现 buffer protocol，无需复制成 bytes 才能读取。
    view = memoryview(buffer)[4:8]
    assert struct.unpack("!Hh", view) == (500, -20)

    with pytest.raises(TypeError):
        struct.pack_into("!I", b"\x00" * 4, 0, 1)
    with pytest.raises(struct.error):
        struct.pack_into("!I", bytearray(3), 0, 1)


def test_unpack_from_reads_a_record_inside_a_larger_packet():
    """unpack 要求长度恰好相等；unpack_from 才适合 header、记录、trailer 共存。"""

    header = b"HEAD"
    reading = struct.pack("!Ih", 1001, -12)
    packet = header + reading + b"CRC!"

    assert struct.unpack_from("!Ih", packet, len(header)) == (1001, -12)

    with pytest.raises(struct.error):
        struct.unpack("!Ih", packet)


def test_iter_unpack_parses_only_whole_fixed_size_records():
    """iter_unpack 适合无间隙定长记录流；尾部半条记录不是可忽略的 remainder。"""

    record_format = "!HB"
    stream = b"".join(
        struct.pack(record_format, identifier, state)
        for identifier, state in [(101, 1), (102, 0), (103, 1)]
    )

    assert list(struct.iter_unpack(record_format, stream)) == [
        (101, 1),
        (102, 0),
        (103, 1),
    ]

    with pytest.raises(struct.error):
        list(struct.iter_unpack(record_format, stream + b"\xff"))


def test_struct_object_reuses_one_compiled_format_across_all_operations():
    """频繁处理同一布局时，Struct 把 format 和 size 与操作方法收在一个对象上。"""

    message_header = struct.Struct("!4sBH")
    first = message_header.pack(b"PGLT", 1, 12)
    second = message_header.pack(b"PGLT", 2, 30)

    assert message_header.format == "!4sBH"
    assert message_header.size == 7
    assert len(first) == message_header.size
    assert message_header.unpack(first) == (b"PGLT", 1, 12)
    assert list(message_header.iter_unpack(first + second)) == [
        (b"PGLT", 1, 12),
        (b"PGLT", 2, 30),
    ]

    buffer = bytearray(b"--" + b"\x00" * message_header.size + b"--")
    assert message_header.pack_into(buffer, 2, b"PGLT", 3, 99) is None
    assert message_header.unpack_from(buffer, 2) == (b"PGLT", 3, 99)


def test_argument_count_buffer_size_and_format_errors_fail_loudly():
    """布局不匹配必须尽早失败，不能把缺字段、多余字节或坏格式静默吞掉。"""

    with pytest.raises(struct.error):
        struct.pack("!HB", 7)
    with pytest.raises(struct.error):
        struct.pack("!HB", 7, 1, 99)
    with pytest.raises(struct.error):
        struct.unpack("!H", b"\x00")
    with pytest.raises(struct.error):
        struct.unpack("!H", b"\x00\x01\x02")
    with pytest.raises(struct.error):
        struct.calcsize("!Z")


def test_length_prefixed_text_requires_manual_encoding_and_framing():
    """struct 只编码长度整数；UTF-8、边界检查和下一帧 offset 都由协议代码负责。"""

    def encode_frame(text):
        payload = text.encode("utf-8")
        if len(payload) > 0xFFFF:
            raise ValueError("payload 超过 uint16 长度字段")
        return struct.pack("!H", len(payload)) + payload

    def decode_frame(buffer, offset=0):
        payload_size, = struct.unpack_from("!H", buffer, offset)
        payload_start = offset + struct.calcsize("!H")
        payload_end = payload_start + payload_size
        if payload_end > len(buffer):
            raise ValueError("帧声明的 payload 尚未完整到达")
        text = bytes(buffer[payload_start:payload_end]).decode("utf-8")
        return text, payload_end

    stream = encode_frame("你好") + encode_frame("Python")
    first, next_offset = decode_frame(stream)
    second, final_offset = decode_frame(stream, next_offset)

    assert first == "你好"
    assert second == "Python"
    assert final_offset == len(stream)

    with pytest.raises(ValueError, match="尚未完整到达"):
        decode_frame(encode_frame("完整")[:-1])
