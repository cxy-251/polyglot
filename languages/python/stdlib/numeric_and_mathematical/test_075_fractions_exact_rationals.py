"""075｜``fractions.Fraction`` 精确有理数、构造归一化与分母限制近似。

Fraction 永远保存最简整数分子和正分母，适合比例、概率和需要绝对精确除法的离散领域。
从 float 构造会忠实保留 binary64 的真实值；从十进制字符串或 Decimal 构造才表达
人看到的十进制值。``limit_denominator`` 用于明确地把近似值恢复为小分母比例。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.fractions.Fraction python.fraction.normalization
# polyglot-covers: python.fraction.integer-pair python.fraction.positive-denominator
# polyglot-covers: python.fraction.string-construction python.fraction.python310-slash-whitespace
# polyglot-covers: python.fraction.float-construction python.fraction.decimal-construction
# polyglot-covers: python.fraction.from_float python.fraction.from_decimal
# polyglot-covers: python.fraction.numerator python.fraction.denominator python.fraction.as_integer_ratio
# polyglot-covers: python.fraction.immutable python.fraction.hashable python.fraction.Rational
# polyglot-covers: python.fraction.exact-arithmetic python.fraction.mixed-arithmetic
# polyglot-covers: python.fraction.limit_denominator python.fraction.rational-recovery
# polyglot-covers: python.fraction.floor python.fraction.ceil python.fraction.trunc
# polyglot-covers: python.fraction.round python.fraction.half-even

from decimal import Decimal
from fractions import Fraction
import math
import numbers

import pytest


def test_default_and_integer_constructors_use_denominator_one():
    """无参数是 0/1，单个整数 n 是 n/1；Fraction 是 Rational 的具体不可变实现。"""

    assert Fraction() == Fraction(0, 1)
    assert Fraction(7) == Fraction(7, 1)
    assert Fraction(-7) == Fraction(-7, 1)
    assert isinstance(Fraction(1, 2), numbers.Rational)


def test_integer_pair_is_reduced_and_denominator_sign_moves_to_numerator():
    """构造时用 gcd 约分，并规范为正 denominator，后续 equality/hash 无需再化简。"""

    value = Fraction(16, -10)

    assert value == Fraction(-8, 5)
    assert value.numerator == -8
    assert value.denominator == 5
    assert math.gcd(value.numerator, value.denominator) == 1


def test_zero_numerator_is_canonical_and_zero_denominator_is_an_error():
    """任意非零分母的 0 都归一为 0/1；分母 0 不产生 infinity，而是立即失败。"""

    assert Fraction(0, 999).as_integer_ratio() == (0, 1)
    assert Fraction(0, -3).as_integer_ratio() == (0, 1)

    with pytest.raises(ZeroDivisionError, match=r"Fraction\(1, 0\)"):
        Fraction(1, 0)


def test_fraction_constructor_copies_any_rational_value_exactly():
    """单参数 Rational 构造读取其 numerator/denominator，不经 float 中转。"""

    original = Fraction(355, 113)
    copied = Fraction(original)

    assert copied == original
    assert copied.as_integer_ratio() == (355, 113)
    assert Fraction(True) == Fraction(1, 1)


def test_string_constructor_accepts_ratio_decimal_and_scientific_forms():
    """ratio 字符串直接给整数比；有限 float 风格字符串按十进制文本精确解析。"""

    assert Fraction("  -3/7  ") == Fraction(-3, 7)
    assert Fraction("1.414213") == Fraction(1_414_213, 1_000_000)
    assert Fraction("-.125") == Fraction(-1, 8)
    assert Fraction("7e-6") == Fraction(7, 1_000_000)


def test_python_310_ratio_string_does_not_allow_spaces_around_slash():
    """3.10 只允许整个字符串首尾空白；分子与斜杠之间的空白支持来自后续版本。"""

    with pytest.raises(ValueError, match="Invalid literal"):
        Fraction("2 / 3")


def test_string_constructor_rejects_nonfinite_and_malformed_values():
    """Fraction 必须是有限整数比，因此 NaN/Infinity 和不完整 ratio 都无合法表示。"""

    for text in ("nan", "inf", "1/", "one-half"):
        with pytest.raises(ValueError):
            Fraction(text)


def test_float_constructor_preserves_exact_binary_value_not_displayed_decimal():
    """Fraction(1.1) 读取 float 的真实整数比，所以不等于文本语义 11/10。"""

    exact_binary = Fraction(1.1)

    assert exact_binary == Fraction(2_476_979_795_053_773, 2_251_799_813_685_248)
    assert exact_binary != Fraction(11, 10)
    assert exact_binary == Fraction.from_float(1.1)


def test_decimal_constructor_preserves_exact_base_ten_value():
    """Decimal('1.1') 本身就是 11/10，转换不会经过 float；尾随零不影响比例。"""

    assert Fraction(Decimal("1.1")) == Fraction(11, 10)
    assert Fraction(Decimal("1.100")) == Fraction(11, 10)
    assert Fraction.from_decimal(Decimal("0.125")) == Fraction(1, 8)


def test_alternative_constructors_restrict_input_types_to_make_intent_clear():
    """from_float/from_decimal 不接受数字字符串；显式入口能防止调用方误选解析语义。"""

    assert Fraction.from_float(2) == Fraction(2, 1)
    assert Fraction.from_decimal(2) == Fraction(2, 1)

    with pytest.raises(TypeError):
        Fraction.from_float(Decimal("0.5"))
    with pytest.raises(TypeError):
        Fraction.from_decimal(0.5)


def test_numerator_denominator_and_integer_ratio_are_already_in_lowest_terms():
    """三个公共入口给出同一 canonical pair，denominator 保证正数。"""

    value = Fraction(-42, 56)

    assert value.numerator == -3
    assert value.denominator == 4
    assert value.as_integer_ratio() == (-3, 4)
    assert type(value.numerator) is type(value.denominator) is int


def test_fraction_is_immutable_hashable_and_hash_compatible_with_equal_numbers():
    """不可变最简表示可作 key；与 int/float 精确相等时必须共享 hash。"""

    half = Fraction(1, 2)
    mapping = {half: "half"}

    assert mapping[Fraction(2, 4)] == "half"
    assert mapping[0.5] == "half"
    assert hash(half) == hash(0.5)

    with pytest.raises(AttributeError):
        half.numerator = 2


def test_fraction_arithmetic_stays_exact_for_rational_operands():
    """加减乘除都通过整数交叉运算再约分，不会累积 binary rounding。"""

    left = Fraction(1, 3)
    right = Fraction(1, 6)

    assert left + right == Fraction(1, 2)
    assert left - right == Fraction(1, 6)
    assert left * right == Fraction(1, 18)
    assert left / right == Fraction(2, 1)
    assert type(left + right) is Fraction


def test_integer_powers_are_exact_and_negative_power_inverts_the_fraction():
    """整数 exponent 保持 Fraction；负 exponent 交换分子分母，零的负次幂报错。"""

    value = Fraction(2, 3)

    assert value**3 == Fraction(8, 27)
    assert value**-2 == Fraction(9, 4)
    assert Fraction(4, 9) ** Fraction(1, 2) == (4 / 9) ** 0.5

    with pytest.raises(ZeroDivisionError):
        Fraction(0) ** -1


def test_mixed_arithmetic_selects_fraction_float_or_complex_common_type():
    """int/Fraction 保持 exact；遇 float 或 complex 后按数值塔 fallback 到相应内置类型。"""

    value = Fraction(1, 3)

    assert type(value + 1) is Fraction
    assert value + 1 == Fraction(4, 3)

    float_result = value + 0.5
    complex_result = value + 1j
    assert type(float_result) is float
    assert type(complex_result) is complex
    assert float_result == float(value) + 0.5
    assert complex_result == complex(value) + 1j


def test_decimal_and_fraction_compare_but_require_explicit_arithmetic_conversion():
    """跨类型 equality/order 能精确比较；两套精度模型没有默认共同算术类型。"""

    fraction = Fraction(1, 10)
    decimal = Decimal("0.1")

    assert fraction == decimal
    assert Fraction(1, 3) > decimal

    with pytest.raises(TypeError, match="unsupported operand"):
        fraction + decimal


def test_limit_denominator_finds_best_small_denominator_approximation():
    """限制 denominator 后返回距离最近的 Fraction，常用于显示比例或协议近似。"""

    pi_approximation = Fraction("3.1415926535897932").limit_denominator(1000)

    assert pi_approximation == Fraction(355, 113)
    assert pi_approximation.denominator <= 1000

    with pytest.raises(ValueError, match="max_denominator should be at least 1"):
        Fraction(1, 2).limit_denominator(0)


def test_limit_denominator_can_recover_simple_ratio_from_float_noise():
    """binary trig/decimal 输入的长比例可在明确误差预算下恢复为 1/2、11/10 等。"""

    noisy_half = Fraction(math.cos(math.pi / 3))

    assert noisy_half != Fraction(1, 2)
    assert noisy_half.limit_denominator() == Fraction(1, 2)
    assert Fraction(1.1).limit_denominator() == Fraction(11, 10)


def test_floor_ceil_trunc_and_int_have_distinct_negative_rounding_rules():
    """floor 向负无穷，ceil 向正无穷，trunc/int 向零；协议结果都是 int。"""

    value = Fraction(-7, 3)

    assert math.floor(value) == -3
    assert math.ceil(value) == -2
    assert math.trunc(value) == -2
    assert int(value) == -2


def test_round_uses_half_even_and_ndigits_returns_an_exact_fraction():
    """无 ndigits 返回 int；指定 ndigits 则返回最接近相应十进制 quantum 的 Fraction。"""

    assert round(Fraction(5, 2)) == 2
    assert round(Fraction(7, 2)) == 4
    assert round(Fraction(-5, 2)) == -2

    rounded = round(Fraction(1, 3), 2)
    assert rounded == Fraction(33, 100)
    assert type(rounded) is Fraction

    assert round(Fraction(149, 1), -2) == Fraction(100, 1)
