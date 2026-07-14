"""072｜``decimal.Decimal`` 精确构造、有效位表示与 context 隔离。

Decimal 的值由 sign、coefficient digits 和 exponent 组成；尾随零会保留为有效位信息。
构造过程保存输入的全部位数，当前 context 的 precision 主要在算术时生效。
所有会修改 context 的案例都使用 ``localcontext``，避免测试之间泄漏舍入环境。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.decimal.Decimal python.decimal.exact-decimal-string
# polyglot-covers: python.decimal.integer-construction python.decimal.tuple-construction
# polyglot-covers: python.decimal.float-construction python.decimal.from_float
# polyglot-covers: python.decimal.string-grammar python.decimal.unicode-digits
# polyglot-covers: python.decimal.significance python.decimal.trailing-zero
# polyglot-covers: python.decimal.immutable python.decimal.hashable
# polyglot-covers: python.decimal.as_tuple python.decimal.adjusted python.decimal.as_integer_ratio
# polyglot-covers: python.decimal.special-values python.decimal.signed-zero
# polyglot-covers: python.decimal.Context python.decimal.getcontext python.decimal.localcontext
# polyglot-covers: python.decimal.context-precision python.decimal.context-rounding
# polyglot-covers: python.decimal.Context.create_decimal python.decimal.constructor-context
# polyglot-covers: python.decimal.malformed-input python.decimal.InvalidOperation

from decimal import (
    Context,
    Decimal,
    Inexact,
    InvalidOperation,
    ROUND_DOWN,
    ROUND_UP,
    Rounded,
    getcontext,
    localcontext,
)

import pytest


def test_decimal_strings_represent_base_ten_fractions_exactly():
    """从字符串构造不会先经过 binary float，适合金额等要求十进制恒等式的领域。"""

    decimal_result = Decimal("0.1") + Decimal("0.1") + Decimal("0.1") - Decimal("0.3")
    float_result = 0.1 + 0.1 + 0.1 - 0.3

    assert decimal_result == Decimal("0.0")
    assert decimal_result.is_zero()
    assert float_result != 0.0


def test_constructor_accepts_integer_string_and_default_zero():
    """无参数得到 0；int 精确转换，字符串的指数与尾随零按原表示保存。"""

    assert Decimal() == Decimal(0) == Decimal("0")
    assert Decimal(10) == Decimal("10")
    assert Decimal("1.2300e2") == Decimal("123.00")
    assert str(Decimal("1.2300e2")) == "123.00"


def test_decimal_string_grammar_allows_whitespace_underscores_and_unicode_digits():
    """构造器比 Python literal 更宽：首尾空白被忽略，下划线分组和 Unicode 十进制数字可用。"""

    assert Decimal("  1_234.50  ") == Decimal("1234.50")
    assert Decimal("١٢.٥") == Decimal("12.5")
    assert Decimal("+7_000e-3") == Decimal("7.000")


def test_tuple_constructor_exposes_sign_digits_and_exponent_model():
    """三元组是 ``(sign, digits, exponent)``；sign 只允许 0/1，digits 是逐位 coefficient。"""

    positive = Decimal((0, (3, 1, 4), -2))
    negative = Decimal((1, (3, 1, 4), -2))

    assert positive == Decimal("3.14")
    assert negative == Decimal("-3.14")
    assert positive.as_tuple().sign == 0
    assert negative.as_tuple().sign == 1


def test_float_constructor_preserves_the_exact_binary_float_value():
    """``Decimal(0.1)`` 不是“用户输入的 0.1”，而是 binary64 近似值的无损十进制展开。"""

    from_string = Decimal("0.1")
    from_float = Decimal(0.1)

    assert from_float != from_string
    assert str(from_float) == "0.1000000000000000055511151231257827021181583404541015625"
    assert from_float == Decimal.from_float(0.1)


def test_from_float_accepts_int_and_float_but_not_decimal_strings():
    """classmethod 明确表示“还原已有二进制数值”，因此不会接受可能有歧义的字符串。"""

    assert Decimal.from_float(10) == Decimal(10)
    assert Decimal.from_float(0.5) == Decimal("0.5")

    with pytest.raises(TypeError, match="argument must be int or float"):
        Decimal.from_float("0.5")


def test_context_precision_does_not_truncate_new_decimal_input():
    """precision 不限制构造时保存的 digits；第一次算术才按 context 舍入。"""

    with localcontext() as context:
        context.prec = 4
        value = Decimal("3.1415926535")

        assert str(value) == "3.1415926535"
        assert len(value.as_tuple().digits) == 11
        assert value + Decimal(0) == Decimal("3.142")


def test_significant_trailing_zeros_survive_schoolbook_arithmetic():
    """尾随零记录测量/金额精度：加法保留 2 位小数，乘法组合乘数的有效位。"""

    assert Decimal("1.30") + Decimal("1.20") == Decimal("2.50")
    assert str(Decimal("1.30") + Decimal("1.20")) == "2.50"

    product = Decimal("1.30") * Decimal("1.20")
    assert product == Decimal("1.5600")
    assert str(product) == "1.5600"


def test_decimal_is_immutable_and_operations_return_new_values():
    """算术不修改原 coefficient；不可变性也让 Decimal 可安全作为 dict/set key。"""

    original = Decimal("12.30")
    result = original + Decimal("0.70")

    assert str(original) == "12.30"
    assert str(result) == "13.00"
    assert result is not original

    mapping = {original: "price"}
    assert mapping[Decimal("12.3")] == "price"


def test_as_tuple_preserves_representation_details_hidden_by_numeric_equality():
    """12、12.0、12.00 数值相等，但 digits/exponent 不同；负零的 sign 也不会被 == 显示。"""

    integer = Decimal("12")
    hundredths = Decimal("12.00")
    negative_zero = Decimal("-0.00")

    assert integer == hundredths
    assert integer.as_tuple() == (0, (1, 2), 0)
    assert hundredths.as_tuple() == (0, (1, 2, 0, 0), -2)
    assert negative_zero == Decimal("0.00")
    assert negative_zero.as_tuple() == (1, (0,), -2)


def test_adjusted_reports_the_most_significant_digits_decimal_position():
    """adjusted 等于 exponent + digits_count - 1，可用于决定科学计数或量级。"""

    assert Decimal("321e+5").adjusted() == 7
    assert Decimal("0.00123").adjusted() == -3
    assert Decimal("12.30").adjusted() == 1


def test_as_integer_ratio_returns_an_exact_reduced_fraction():
    """有限 Decimal 可无损转为最简整数比，分母始终为正。"""

    assert Decimal("-3.14").as_integer_ratio() == (-157, 50)
    assert Decimal("0.125").as_integer_ratio() == (1, 8)
    assert Decimal("2.00").as_integer_ratio() == (2, 1)

    with pytest.raises(OverflowError):
        Decimal("Infinity").as_integer_ratio()
    with pytest.raises(ValueError):
        Decimal("NaN").as_integer_ratio()


def test_special_values_and_signed_zero_are_part_of_the_decimal_model():
    """Infinity、qNaN、sNaN 和 ±0 都能直接构造；分类方法比字符串或普通等式可靠。"""

    assert Decimal("Infinity").is_infinite()
    assert Decimal("-Infinity").is_signed()
    assert Decimal("NaN").is_qnan()
    assert Decimal("sNaN42").is_snan()

    negative_zero = Decimal("-0")
    assert negative_zero.is_zero()
    assert negative_zero.is_signed()
    assert negative_zero == Decimal("0")


def test_malformed_string_uses_the_supplied_context_invalid_operation_policy():
    """context 参数只决定非法构造是 trap 还是返回 NaN；它不负责正常输入的 precision。"""

    trapping = Context()
    quiet = Context()
    quiet.traps[InvalidOperation] = False

    with pytest.raises(InvalidOperation):
        Decimal("not-a-number", context=trapping)

    result = Decimal("not-a-number", context=quiet)
    assert result.is_qnan()
    assert quiet.flags[InvalidOperation]


def test_getcontext_returns_the_active_mutable_arithmetic_environment():
    """同一执行上下文中 getcontext 返回当前对象；precision/rounding 会影响随后的算术。"""

    with localcontext() as active:
        assert getcontext() is active
        active.prec = 5
        active.rounding = ROUND_DOWN

        result = Decimal(1) / Decimal(7)

        assert result == Decimal("0.14285")
        assert getcontext().prec == 5


def test_localcontext_restores_outer_precision_and_rounding_after_exit():
    """库函数临时提高精度时必须恢复调用者环境；context manager 同时处理异常路径。"""

    outer = getcontext()
    original_precision = outer.prec
    original_rounding = outer.rounding

    with localcontext() as inner:
        inner.prec = 3
        inner.rounding = ROUND_UP
        assert getcontext() is inner
        assert Decimal(1) / Decimal(8) == Decimal("0.125")

    assert getcontext() is outer
    assert outer.prec == original_precision
    assert outer.rounding == original_rounding


def test_localcontext_copies_an_explicit_template_instead_of_mutating_it():
    """传入 Context 时安装的是副本；块内调整不会污染可复用的模板。"""

    template = Context(prec=6, rounding=ROUND_DOWN)

    with localcontext(template) as active:
        assert active is not template
        active.prec = 2
        active.rounding = ROUND_UP
        assert Decimal(1) / Decimal(6) == Decimal("0.17")

    assert template.prec == 6
    assert template.rounding == ROUND_DOWN


def test_context_create_decimal_applies_precision_during_conversion():
    """Decimal 构造器保留输入；Context.create_decimal 则立即按模板 precision/rounding 规范化。"""

    context = Context(prec=4, rounding=ROUND_DOWN)
    raw = Decimal("1.234567")
    created = context.create_decimal("1.234567")

    assert raw == Decimal("1.234567")
    assert created == Decimal("1.234")
    assert context.flags[Inexact]
    assert context.flags[Rounded]


def test_context_create_decimal_from_float_combines_exact_conversion_and_rounding():
    """先精确恢复 binary float，再按 Context 位数舍入；结果不同于从用户字符串构造。"""

    context = Context(prec=5)
    created = context.create_decimal_from_float(0.1)

    assert created == Decimal("0.10000")
    assert str(created) == "0.10000"
    assert created != Decimal.from_float(0.1)
