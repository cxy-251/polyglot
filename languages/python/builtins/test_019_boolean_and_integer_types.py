"""019｜``bool`` / ``int`` 构造、任意精度、位方法与字节转换示例。

``bool`` 只有 True/False 两个实例，并且是 ``int`` 的子类；这提供历史兼容的
数值行为，也会让 0/False、1/True 在 dict/set 中成为同一键。``int`` 是任意
精度不可变整数，支持多进制解析、位宽/置位计数以及显式的 bytes 编解码。

通用真假协议、二元运算分派和 ``__index__`` 已分别在 001、003、004 展示；
本文件聚焦内置类型自身。内容基于 Python 3.10 Built-in Types、int() 和整数
字面量；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.type.bool python.type.int
# polyglot-covers: python.literal.integer python.literal.integer-underscore
# polyglot-covers: python.builtin.int python.builtin.bool
# polyglot-covers: python.int.bit_length python.int.bit_count
# polyglot-covers: python.int.as_integer_ratio python.int.to_bytes
# polyglot-covers: python.int.from_bytes python.int.numeric-attributes

import math
import sys

import pytest


def test_bool_has_two_singletons_and_is_an_int_subclass():
    """真假对象有独立语义类型，但继承了整数的数值兼容行为。"""

    assert bool(0) is False
    assert bool(1) is True
    assert bool([]) is False
    assert bool([0]) is True

    assert type(True) is bool
    assert isinstance(True, int)
    assert issubclass(bool, int)
    assert int(True) == 1
    assert int(False) == 0
    assert True + True == 2

    # 算术成立不代表业务上应把布尔值当计数。清晰代码会显式区分“是否发生”
    # 和“发生次数”，避免 True + True 这类隐式转换扩散。


def test_bool_cannot_be_subclassed():
    """bool 是 final 风格的内置类型，不能再创建派生类。"""

    with pytest.raises(TypeError, match="not an acceptable base type"):
        type("CustomBool", (bool,), {})


def test_bool_and_zero_one_collide_as_mapping_and_set_keys():
    """相等且 hash 相同的 bool/int 在哈希容器中代表同一键。"""

    mapping = {
        True: "inserted as True",
        1: "overwritten through 1",
        False: "inserted as False",
        0: "overwritten through 0",
    }

    assert len(mapping) == 2
    assert mapping[True] == "overwritten through 1"
    assert mapping[1] == "overwritten through 1"
    assert mapping[False] == "overwritten through 0"
    assert mapping[0] == "overwritten through 0"
    assert len({True, 1, 1.0}) == 1

    # 常见坑：JSON/表格数据把 bool 和 int 混作 ID 时，放入 dict/set 会静默合并。
    # 应在容器边界先做明确类型校验或使用带类型标签的复合键。


def test_integer_literals_support_multiple_bases_and_visual_separators():
    """前缀决定字面量进制，下划线只提高可读性、不改变数值。"""

    decimal = 1_000_000
    binary = 0b1111_0000
    octal = 0o755
    hexadecimal = 0xFF_FF

    assert decimal == 1000000
    assert binary == 240
    assert octal == 493
    assert hexadecimal == 65535


def test_decimal_literal_with_leading_zero_is_rejected_at_compile_time():
    """除单独的 0 外，十进制整数字面量不能沿用旧式前导零写法。"""

    with pytest.raises(SyntaxError, match="leading zeros"):
        compile("value = 010", "<leading-zero>", "exec")

    # 八进制必须显式写 0o10；这样不会让读者猜测 010 是十还是八。


def test_int_has_arbitrary_precision_and_sys_maxsize_is_not_its_limit():
    """``sys.maxsize`` 描述平台索引大小，不是 Python int 的最大值。"""

    huge = 10**1000

    assert huge > sys.maxsize
    assert huge + 1 > huge
    assert (1 << 10000).bit_length() == 10001

    # 内存仍是现实边界，但不会像固定 64 位整数那样在 sys.maxsize 处溢出回绕。


def test_int_constructs_from_numbers_text_and_binary_text():
    """单参数 ``int`` 接受数值或十进制文本，包括 bytes/bytearray。"""

    assert int() == 0
    assert int(42) == 42
    assert int(3.9) == 3
    assert int(-3.9) == -3
    assert int("  -1_024  ") == -1024
    assert int(b"123") == 123
    assert int(bytearray(b"456")) == 456


def test_int_float_conversion_truncates_toward_zero_not_toward_floor():
    """负数最能显示显式 int 转换与 floor division 的方向差异。"""

    value = -3.9

    assert int(value) == -3
    assert math.trunc(value) == -3
    assert math.floor(value) == -4
    assert value // 1 == -4.0

    # int(float) 与 trunc 都朝零；// 和 floor 朝负无穷。不能用 int(a / b)
    # 机械替换 a // b。


def test_int_rejects_nan_and_infinity_with_distinct_errors():
    """非有限 float 没有可返回的有限整数。"""

    with pytest.raises(ValueError, match="NaN"):
        int(float("nan"))

    with pytest.raises(OverflowError, match="infinity"):
        int(float("inf"))


def test_int_string_base_parsing_supports_explicit_and_prefix_inferred_bases():
    """显式 base 解释纯数字；base 0 按合法前缀推断。"""

    assert int("1010", 2) == 10
    assert int("755", 8) == 493
    assert int("ff", 16) == 255
    assert int("z", 36) == 35

    assert int("0b1010", 0) == 10
    assert int("0o755", 0) == 493
    assert int("0xff", 0) == 255
    assert int("+0x_FF", 0) == 255

    # 前缀后的单个下划线合法，可把前缀与分组后的数字视觉分开。


def test_base_zero_rejects_ambiguous_leading_zero_decimal_text():
    """``base=0`` 模拟代码字面量规则，不把 ``"010"`` 猜成十进制或八进制。"""

    with pytest.raises(ValueError):
        int("010", 0)

    assert int("010", 10) == 10
    assert int("0o10", 0) == 8


def test_int_base_argument_has_strict_range_and_input_contract():
    """base 必须为 0 或 2--36，且两参数形式的 x 必须是文本/bytes。"""

    with pytest.raises(ValueError):
        int("10", 1)

    with pytest.raises(ValueError):
        int("10", 37)

    with pytest.raises(TypeError):
        int(10, 2)


def test_integer_bit_length_and_bit_count_use_absolute_magnitude():
    """位宽忽略符号，置位计数统计绝对值二进制中的 1。"""

    assert (0).bit_length() == 0
    assert (13).bit_length() == 4
    assert (-13).bit_length() == 4

    assert (0b1101).bit_count() == 3
    assert (-0b1101).bit_count() == 3

    byte_length = max(1, ((65535).bit_length() + 7) // 8)
    assert byte_length == 2

    # 位转字节常用 `(bit_length + 7) // 8`：先向上取整到完整字节，再除以 8。
    # 不要按十进制字符串长度猜需要几个字节。


def test_integer_ratio_and_numeric_attributes_are_exact():
    """整数作为实数/有理数的属性不会引入 float。"""

    value = 10

    assert value.as_integer_ratio() == (10, 1)
    assert value.numerator == 10
    assert value.denominator == 1
    assert value.real == 10
    assert value.imag == 0
    assert value.conjugate() == 10


def test_int_to_bytes_and_from_bytes_respect_byte_order():
    """相同整数的大端/小端排列不同，但用同一顺序解码会还原。"""

    value = 0x1234
    big_endian = value.to_bytes(2, byteorder="big")
    little_endian = value.to_bytes(2, byteorder="little")

    assert big_endian == b"\x12\x34"
    assert little_endian == b"\x34\x12"
    assert int.from_bytes(big_endian, byteorder="big") == value
    assert int.from_bytes(little_endian, byteorder="little") == value

    # byteorder 必须与外部格式约定一致；两边都“成功”不代表解释的是同一数值。


def test_signed_byte_conversion_controls_twos_complement_interpretation():
    """``signed=True`` 允许负数编码，并决定最高位是否作为符号位。"""

    encoded = (-2).to_bytes(2, byteorder="big", signed=True)

    assert encoded == b"\xff\xfe"
    assert int.from_bytes(encoded, byteorder="big", signed=True) == -2
    assert int.from_bytes(encoded, byteorder="big", signed=False) == 65534

    with pytest.raises(OverflowError):
        (-2).to_bytes(2, byteorder="big")


def test_to_bytes_length_must_be_large_enough_for_value_and_sign():
    """length 是固定输出宽度；装不下时不会自动扩容。"""

    assert (255).to_bytes(1, byteorder="big") == b"\xff"

    with pytest.raises(OverflowError):
        (256).to_bytes(1, byteorder="big")

    with pytest.raises(OverflowError):
        (128).to_bytes(1, byteorder="big", signed=True)

    assert (128).to_bytes(2, byteorder="big", signed=True) == b"\x00\x80"

    # signed 正数最高位为 1 时还需要一个前导 0 字节，不能只按无符号 bit_length
    # 估算固定协议宽度。


def test_invalid_shift_and_division_boundaries_raise_clear_errors():
    """负移位次数和零除法没有整数结果。"""

    with pytest.raises(ValueError, match="negative shift count"):
        1 << -1

    with pytest.raises(ZeroDivisionError):
        1 // 0

    with pytest.raises(ZeroDivisionError):
        1 % 0


def test_int_of_subclass_returns_plain_int_value_not_subclass_metadata():
    """显式 ``int`` 可去掉 int 子类身份；不可依赖缓存决定对象 identity。"""

    class Quantity(int):
        def __new__(cls, value, unit):
            instance = super().__new__(cls, value)
            instance.unit = unit
            return instance

    quantity = Quantity(7, "items")
    converted = int(quantity)

    assert converted == 7
    assert type(converted) is int
    assert converted is not quantity
    assert not hasattr(converted, "unit")

    exact = 10**100
    assert int(exact) == exact

    # CPython 可能直接复用已有精确 int，也会缓存一部分小整数；`is` 结果不是
    # 数值 API 契约，数值相等应使用 ==。
