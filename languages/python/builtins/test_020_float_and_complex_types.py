"""020｜``float`` / ``complex`` 的近似表示、特殊值与复数运算示例。

Python float 通常实现为 IEEE 754 binary64：它能精确表示许多二进制分数，却不能
精确表示大多数有限十进制小数。complex 由两个 float 分量组成，支持相等和算术，
但复数没有自然的大小顺序，也不能隐式丢弃虚部转换成实数。

通用比较、二元运算分派和数值转换协议已在 002--004 展示；本文件聚焦内置数值
类型自身以及实际判断工作流。内容基于 Python 3.10 Built-in Types、float()、
complex() 和 math。
"""

# polyglot-covers: python.type.float python.type.complex
# polyglot-covers: python.literal.float python.literal.imaginary
# polyglot-covers: python.builtin.float python.builtin.complex
# polyglot-covers: python.float.as_integer_ratio python.float.hex
# polyglot-covers: python.float.fromhex python.float.is_integer
# polyglot-covers: python.float.infinity python.float.nan python.float.signed-zero
# polyglot-covers: python.math.isclose python.complex.conjugate

import math

import pytest


def test_float_literals_and_constructor_accept_readable_numeric_forms():
    """浮点字面量和文本都支持科学计数法与数字间下划线。"""

    decimal = 1_234.5_6
    scientific = 1.25e3

    assert decimal == 1234.56
    assert scientific == 1250.0
    assert float() == 0.0
    assert float(7) == 7.0
    assert float("  -1_000.25  ") == -1000.25
    assert float(b"6.25") == 6.25

    # 下划线只能出现在数字之间；它是可读性分隔符，不是任意可忽略字符。
    with pytest.raises(ValueError):
        float("1__000.0")


def test_true_division_and_mixed_arithmetic_produce_float_results():
    """``/`` 对整数也是真除法；int 与 float 混合时通常提升为 float。"""

    assert 5 / 2 == 2.5
    assert type(5 / 2) is float
    assert 5 // 2 == 2
    assert 5 + 0.5 == 5.5
    assert type(5 + 0.5) is float

    # 常见坑：需要离散数量时不能只看操作数都是 int；`/` 的结果仍是 float。


def test_decimal_fractions_are_not_usually_exact_binary_fractions():
    """显示值经过最短表示格式化，不代表底层值就是精确十进制数。"""

    assert 0.1 + 0.2 != 0.3
    assert math.isclose(0.1 + 0.2, 0.3)
    assert format(0.1, ".17g") == "0.10000000000000001"
    assert 0.1.as_integer_ratio() == (
        3602879701896397,
        36028797018963968,
    )

    # 财务等必须遵守十进制规则的领域应使用 decimal.Decimal，而不是靠 round
    # 掩盖每一步的 binary float 误差。


def test_float_exact_representation_tools_support_round_trips():
    """ratio 和十六进制形式可无损描述有限 float 的实际二进制值。"""

    value = 1.5
    numerator, denominator = value.as_integer_ratio()
    hexadecimal = value.hex()

    assert (numerator, denominator) == (3, 2)
    assert hexadecimal == "0x1.8000000000000p+0"
    assert float.fromhex(hexadecimal) == value
    assert float.fromhex("0x1.8p+1") == 3.0

    # float.hex() 适合精确存档、诊断和跨系统往返，不是面向普通用户的十六进制
    # 整数显示；其中 `p` 引入的是 2 的指数。


def test_float_is_integer_checks_value_not_source_or_storage_type():
    """``is_integer`` 判断当前有限值有无小数部分。"""

    assert (3.0).is_integer() is True
    assert (-0.0).is_integer() is True
    assert (3.5).is_integer() is False
    assert float("inf").is_integer() is False
    assert float("nan").is_integer() is False

    # 结果为 True 不说明数据最初来自 int，也不保证它能放入某个固定宽度整数。


def test_large_int_conversion_and_large_float_text_have_different_boundaries():
    """过大 int 转 float 报错，而合法但过大的浮点文本产生 infinity。"""

    with pytest.raises(OverflowError):
        float(10**400)

    assert float("1e400") == float("inf")

    # 两条路径语义不同：前者拒绝悄悄丢失一个已有整数，后者按浮点文本解析规则
    # 得到超出有限范围的特殊值。业务输入通常应再用 math.isfinite() 校验。


def test_infinity_is_ordered_but_arithmetic_can_create_nan():
    """无穷值参与普通排序；未定义的无穷运算会产生 NaN。"""

    positive = float("inf")
    negative = float("-Infinity")

    assert positive > 10**300
    assert negative < -(10**300)
    assert positive + 1 == positive
    assert math.isnan(positive - positive)
    assert bool(positive) is True


def test_nan_is_not_equal_to_itself_and_requires_an_explicit_predicate():
    """NaN 的不相等语义会破坏把 ``==`` 当检测手段的直觉。"""

    value = float("nan")

    assert value != value
    assert not (value < 0)
    assert not (value > 0)
    assert not (value == 0)
    assert math.isnan(value)
    assert bool(value) is True

    # `value == float("nan")` 永远不是可靠检测方式；NaN 也不是假值。


def test_math_classification_distinguishes_finite_infinite_and_nan_values():
    """先分类特殊值，再进入需要有限实数的计算。"""

    finite = 12.5
    infinity = float("inf")
    nan = float("nan")

    assert math.isfinite(finite)
    assert not math.isfinite(infinity)
    assert not math.isfinite(nan)
    assert math.isinf(infinity)
    assert not math.isinf(nan)
    assert math.isnan(nan)
    assert not math.isnan(infinity)


def test_math_isclose_needs_domain_appropriate_relative_and_absolute_tolerances():
    """相对容差适合非零尺度，靠近零时通常还要绝对容差。"""

    assert math.isclose(1_000_000.0, 1_000_001.0, rel_tol=1.1e-6)
    assert not math.isclose(0.0, 1e-12)
    assert math.isclose(0.0, 1e-12, abs_tol=1e-12)
    assert math.isclose(float("inf"), float("inf"))
    assert not math.isclose(float("nan"), float("nan"))

    # isclose 回答的是“在给定误差模型下是否足够接近”，不是精确相等，也不能
    # 替代 Decimal、货币最小单位或领域规定的舍入流程。


def test_positive_and_negative_zero_compare_equal_but_keep_a_sign_bit():
    """有符号零相等且 hash 相同，某些数值/序列化操作仍能观察其符号。"""

    positive = 0.0
    negative = -0.0

    assert positive == negative
    assert hash(positive) == hash(negative)
    assert negative.hex() == "-0x0.0p+0"
    assert math.copysign(1.0, negative) == -1.0

    with pytest.raises(ZeroDivisionError):
        1.0 / negative

    # Python 的 float 除零会抛异常，不会因为底层格式支持 infinity 就自动返回
    # `-inf`；若协议需要保留零的方向，应显式使用 copysign 等工具。


def test_complex_literals_constructor_and_text_forms_create_two_float_parts():
    """虚数字面量使用 j；complex 文本可包含实部和虚部但内部不能随意加空格。"""

    literal = 3 + 4j

    assert literal == complex(3, 4)
    assert complex("3+4j") == literal
    assert complex("  -2.5j  ") == -2.5j
    assert type(2j) is complex

    with pytest.raises(ValueError):
        complex("3 + 4j")

    # 构造器收到一个完整字符串时不能再传第二个 imag 参数。
    with pytest.raises(TypeError):
        complex("3", 4)


def test_complex_components_magnitude_and_conjugate_are_explicit():
    """real/imag 是 float 分量，共轭翻转虚部符号，abs 返回复平面距离。"""

    value = 3 + 4j

    assert value.real == 3.0
    assert value.imag == 4.0
    assert value.conjugate() == 3 - 4j
    assert abs(value) == 5.0


def test_real_and_complex_values_participate_in_mixed_arithmetic():
    """实数可无损提升为虚部为零的 complex。"""

    assert (1 + 2j) + 3 == 4 + 2j
    assert (1 + 2j) * (3 - 1j) == 5 + 5j
    assert (2 + 0j) / 2 == 1 + 0j

    root = (-1) ** 0.5
    assert type(root) is complex
    assert root == pytest.approx(1j)

    # 负实数的分数次幂进入复数域；若代码只接受实数，不能只检查输入类型而忽略
    # 运算可能产生的结果类型。


def test_complex_has_equality_and_hash_but_no_ordering_relation():
    """虚部为零的 complex 与相等实数共享 hash，但复数不能比较大小。"""

    value = 3 + 0j

    assert value == 3.0 == 3
    assert hash(value) == hash(3.0) == hash(3)
    assert len({value, 3.0, 3}) == 1

    with pytest.raises(TypeError):
        (1 + 2j) < (2 + 1j)

    # 哈希容器按 equality/hash 契约合并这些键；需要保留来源类型时应使用类型标签。


def test_complex_cannot_silently_discard_its_imaginary_component():
    """即使虚部是零，float/int 也不会替调用者决定是否丢弃复数类型。"""

    value = 3 + 0j

    with pytest.raises(TypeError):
        float(value)

    with pytest.raises(TypeError):
        int(value)

    assert float(value.real) == 3.0

    # 明确读取 `.real` 表达调用者已经检查或接受虚部；对任意数据还应先验证 imag。


def test_float_and_complex_instances_are_immutable_values():
    """数值分量只读；“修改”运算会绑定新对象。"""

    real_value = 1.5
    complex_value = 1 + 2j

    with pytest.raises(AttributeError):
        real_value.real = 2.0

    with pytest.raises(AttributeError):
        complex_value.imag = 3.0

    updated = complex_value + 1j
    assert complex_value == 1 + 2j
    assert updated == 1 + 3j
