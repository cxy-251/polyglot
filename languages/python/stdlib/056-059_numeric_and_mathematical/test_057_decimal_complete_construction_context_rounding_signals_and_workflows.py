"""057｜``decimal.Decimal`` 精确构造、有效位表示与 context 隔离。

Decimal 的值由 sign、coefficient digits 和 exponent 组成；尾随零会保留为有效位信息。
构造过程保存输入的全部位数，当前 context 的 precision 主要在算术时生效。
所有会修改 context 的案例都使用 ``localcontext``，避免测试之间泄漏舍入环境。

这些案例面向 Python 3.10。
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
from decimal import (
    BasicContext,
    Clamped,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    ExtendedContext,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    ROUND_05UP,
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Rounded,
    Subnormal,
    Underflow,
    localcontext,
)
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, localcontext
from fractions import Fraction

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


# ``decimal`` 舍入模式、sticky flags、signal 与 trap。
#
# Context 同时决定 precision、rounding、exponent 范围，并为每种异常条件维护 flag/trap。
# flag 用于事后审计且会持续保留；trap 则把同一 signal 提升为异常。案例使用小型局部
# context 主动制造 rounded、inexact、overflow、subnormal、underflow 和 clamped 状态。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.decimal.quantize python.decimal.fixed-exponent
# polyglot-covers: python.decimal.ROUND_CEILING python.decimal.ROUND_FLOOR
# polyglot-covers: python.decimal.ROUND_DOWN python.decimal.ROUND_UP python.decimal.ROUND_05UP
# polyglot-covers: python.decimal.ROUND_HALF_DOWN python.decimal.ROUND_HALF_EVEN
# polyglot-covers: python.decimal.ROUND_HALF_UP
# polyglot-covers: python.decimal.to_integral_value python.decimal.to_integral_exact
# polyglot-covers: python.decimal.unary-plus python.decimal.context-application
# polyglot-covers: python.decimal.flags-sticky python.decimal.clear_flags python.decimal.traps
# polyglot-covers: python.decimal.Rounded python.decimal.Inexact
# polyglot-covers: python.decimal.DivisionByZero python.decimal.InvalidOperation
# polyglot-covers: python.decimal.FloatOperation python.decimal.mixed-float
# polyglot-covers: python.decimal.Overflow python.decimal.Underflow
# polyglot-covers: python.decimal.Subnormal python.decimal.Clamped
# polyglot-covers: python.decimal.Etiny python.decimal.Etop
# polyglot-covers: python.decimal.BasicContext python.decimal.ExtendedContext
# polyglot-covers: python.decimal.signal-hierarchy python.decimal.exact-arithmetic-trap




@pytest.mark.parametrize(
    ("rounding", "positive", "negative"),
    [
        (ROUND_CEILING, "3", "-2"),
        (ROUND_FLOOR, "2", "-3"),
        (ROUND_DOWN, "2", "-2"),
        (ROUND_UP, "3", "-3"),
        (ROUND_HALF_DOWN, "2", "-2"),
        (ROUND_HALF_EVEN, "2", "-2"),
        (ROUND_HALF_UP, "3", "-3"),
    ],
)
def test_rounding_modes_make_direction_and_half_tie_policy_explicit(rounding, positive, negative):
    """同一 ±2.5 在不同规则下得到不同整数；业务代码不应依赖隐含默认值。"""

    quantum = Decimal("1")

    assert Decimal("2.5").quantize(quantum, rounding=rounding) == Decimal(positive)
    assert Decimal("-2.5").quantize(quantum, rounding=rounding) == Decimal(negative)


def test_half_even_chooses_the_even_neighbor_on_both_kinds_of_tie():
    """banker's rounding 不是总向下：2.5→2，但 3.5→4，使大量 ties 的偏差更小。"""

    quantum = Decimal("1")

    assert Decimal("2.5").quantize(quantum, rounding=ROUND_HALF_EVEN) == Decimal("2")
    assert Decimal("3.5").quantize(quantum, rounding=ROUND_HALF_EVEN) == Decimal("4")
    assert Decimal("-3.5").quantize(quantum, rounding=ROUND_HALF_EVEN) == Decimal("-4")


def test_round_05up_depends_on_the_last_retained_digit_after_truncation():
    """05UP 仅当向零截断后最后一位为 0/5 才远离零；它不是普通的“尾数 5 入”。"""

    quantum = Decimal("1")

    assert Decimal("10.1").quantize(quantum, rounding=ROUND_05UP) == Decimal("11")
    assert Decimal("11.9").quantize(quantum, rounding=ROUND_05UP) == Decimal("11")
    assert Decimal("-10.1").quantize(quantum, rounding=ROUND_05UP) == Decimal("-11")


def test_quantize_copies_target_exponent_for_money_and_explicit_rounding_wins():
    """quantize 的结果 exponent 与模板一致；rounding 参数优先于当前 context。"""

    cents = Decimal("0.01")

    with localcontext() as context:
        context.rounding = ROUND_DOWN

        default_result = Decimal("7.325").quantize(cents)
        override_result = Decimal("7.325").quantize(cents, rounding=ROUND_HALF_UP)

    assert str(default_result) == "7.32"
    assert str(override_result) == "7.33"
    assert default_result.as_tuple().exponent == cents.as_tuple().exponent == -2


def test_quantize_signals_invalid_when_coefficient_would_exceed_precision():
    """quantize 保证目标 exponent；若 precision 容不下结果，不会偷偷改变 exponent 而是报错。"""

    with localcontext() as context:
        context.prec = 3

        with pytest.raises(InvalidOperation):
            Decimal("99.99").quantize(Decimal("0.01"))


def test_quantize_with_inexact_trap_validates_fixed_decimal_places():
    """启用 Inexact trap 可把 quantize 变成“不得丢失非零小数位”的输入验证器。"""

    context = Context(traps=[Inexact])
    cents = Decimal("0.01")

    assert Decimal("3.21").quantize(cents, context=context) == Decimal("3.21")
    with pytest.raises(Inexact):
        Decimal("3.214").quantize(cents, context=context)


def test_quantize_never_signals_underflow_even_for_inexact_subnormal_result():
    """quantize 的特例保证不发 Underflow；仍会记录 Subnormal、Inexact 与 Rounded。"""

    context = Context(prec=3, Emin=-2, Emax=2, traps=[])
    result = Decimal("0.0001234").quantize(Decimal("0.0001"), context=context)

    assert result == Decimal("0.0001")
    assert context.flags[Subnormal]
    assert context.flags[Inexact]
    assert context.flags[Rounded]
    assert not context.flags[Underflow]


def test_to_integral_value_is_quiet_while_to_integral_exact_records_rounding():
    """只想得到整数值用 quiet 版本；要审计是否丢小数则用 exact 版本查看 flags/traps。"""

    with localcontext() as context:
        context.clear_flags()
        quiet = Decimal("2.7").to_integral_value(rounding=ROUND_DOWN)
        assert quiet == Decimal("2")
        assert not context.flags[Rounded]
        assert not context.flags[Inexact]

        exact = Decimal("2.7").to_integral_exact(rounding=ROUND_DOWN)
        assert exact == Decimal("2")
        assert context.flags[Rounded]
        assert context.flags[Inexact]


def test_unary_plus_applies_context_precision_and_is_not_an_identity_operation():
    """``+decimal`` 会按当前 context 重新舍入；复制 Decimal 不应借用一元加。"""

    value = Decimal("1.234567")

    with localcontext() as context:
        context.prec = 4
        rounded = +value

    assert rounded == Decimal("1.235")
    assert rounded is not value
    assert value == Decimal("1.234567")


def test_signal_flags_are_sticky_until_clear_flags_is_called():
    """一次 inexact 后 flag 不会被后续 exact 运算自动清除；每段审计前应主动 reset。"""

    with localcontext() as context:
        context.prec = 4
        context.clear_flags()

        assert Decimal(1) / Decimal(7) == Decimal("0.1429")
        assert context.flags[Inexact]
        assert context.flags[Rounded]

        assert Decimal(1) + Decimal(1) == Decimal(2)
        assert context.flags[Inexact]

        context.clear_flags()
        assert not any(context.flags.values())


def test_rounded_and_inexact_flags_describe_different_information_loss():
    """丢弃的全是零时只有 Rounded；丢弃任一非零 digit 才同时有 Inexact。"""

    context = Context(prec=10)
    context.clear_flags()

    assert Decimal("5.00").quantize(Decimal("1"), context=context) == Decimal("5")
    assert context.flags[Rounded]
    assert not context.flags[Inexact]

    context.clear_flags()
    assert Decimal("5.01").quantize(Decimal("1"), context=context) == Decimal("5")
    assert context.flags[Rounded]
    assert context.flags[Inexact]


def test_inexact_trap_can_enforce_exact_arithmetic_for_a_calculation():
    """同一 signal 在 trap 关闭时给结果和 flag，开启后则在首次非精确操作处中断。"""

    with localcontext() as context:
        context.prec = 3
        context.traps[Inexact] = True

        assert Decimal(1) / Decimal(8) == Decimal("0.125")
        with pytest.raises(Inexact):
            Decimal(1) / Decimal(7)

        assert context.flags[Inexact]


def test_division_by_zero_flag_and_trap_choose_infinity_or_exception():
    """signal 总会先置 flag；trap 关闭返回有符号 Infinity，开启则抛同名异常。"""

    with localcontext() as context:
        context.traps[DivisionByZero] = False
        context.clear_flags()

        assert Decimal(1) / Decimal(0) == Decimal("Infinity")
        assert Decimal(-1) / Decimal(0) == Decimal("-Infinity")
        assert context.flags[DivisionByZero]

        context.clear_flags()
        context.traps[DivisionByZero] = True
        with pytest.raises(DivisionByZero):
            Decimal(1) / Decimal(0)
        assert context.flags[DivisionByZero]


def test_invalid_operation_can_flow_as_qnan_or_interrupt():
    """0/0 没有定义：quiet policy 返回 NaN 继续传播，strict policy 在源头抛异常。"""

    with localcontext() as context:
        context.traps[InvalidOperation] = False
        context.clear_flags()

        result = Decimal(0) / Decimal(0)
        assert result.is_qnan()
        assert (result + Decimal(1)).is_qnan()
        assert context.flags[InvalidOperation]

        context.traps[InvalidOperation] = True
        with pytest.raises(InvalidOperation):
            Decimal(0) / Decimal(0)


def test_float_operation_trap_blocks_implicit_construction_and_ordering_but_not_equality():
    """FloatOperation 审计隐式混用；显式 from_float 及 equality 保持可用。"""

    with localcontext() as context:
        context.traps[FloatOperation] = True

        with pytest.raises(FloatOperation):
            Decimal(3.14)
        with pytest.raises(FloatOperation):
            Decimal("3.5") < 3.7

        assert Decimal("3.5") == 3.5
        assert Decimal.from_float(0.5) == Decimal("0.5")


def test_decimal_float_arithmetic_is_rejected_even_when_float_operation_trap_is_off():
    """FloatOperation 只控制构造/比较审计；Decimal 与 float 的加减乘除始终不隐式转换。"""

    with localcontext() as context:
        context.traps[FloatOperation] = False

        with pytest.raises(TypeError, match="unsupported operand"):
            Decimal("1.0") + 1.0


def test_overflow_returns_infinity_and_sets_its_parent_signals_when_untrapped():
    """超出 Emax 且采用默认向最近舍入时得到 Infinity；Overflow 也属于 Inexact/Rounded。"""

    context = Context(prec=3, Emin=-2, Emax=2, traps=[])
    result = context.multiply(Decimal("9.99E+2"), Decimal(10))

    assert result == Decimal("Infinity")
    assert context.flags[Overflow]
    assert context.flags[Inexact]
    assert context.flags[Rounded]


def test_exact_subnormal_sets_subnormal_without_underflow():
    """Underflow 不是“量级小”的同义词；结果 subnormal 但 exact 时只置 Subnormal。"""

    context = Context(prec=3, Emin=-2, Emax=2, traps=[])
    result = context.plus(Decimal("0.001"))

    assert result == Decimal("0.001")
    assert result.is_subnormal(context=context)
    assert context.flags[Subnormal]
    assert not context.flags[Underflow]
    assert not context.flags[Inexact]


def test_underflow_requires_a_subnormal_result_that_was_also_rounded_inexactly():
    """极小精确结果进一步越过 Etiny 后被舍入；Underflow 同时蕴含 Subnormal/Inexact/Rounded。"""

    context = Context(prec=3, Emin=-2, Emax=2, traps=[])
    result = context.multiply(Decimal("0.001"), Decimal("0.001"))

    assert result.is_zero()
    assert context.flags[Underflow]
    assert context.flags[Subnormal]
    assert context.flags[Inexact]
    assert context.flags[Rounded]


def test_clamp_reduces_exponent_by_appending_coefficient_zeros():
    """clamp=1 把指数压到 Etop 内，同时增加 coefficient 尾零以保持数值。"""

    context = Context(prec=3, Emin=-2, Emax=2, clamp=1, traps=[])
    result = context.create_decimal("1E+2")

    assert result == Decimal("100")
    assert result.as_tuple().digits == (1, 0, 0)
    assert result.as_tuple().exponent == 0
    assert context.flags[Clamped]


def test_etiny_and_etop_derive_representable_exponent_limits_from_context():
    """Etiny=Emin-prec+1 是 subnormal 最小 exponent；Etop=Emax-prec+1 是 clamp 上界。"""

    context = Context(prec=4, Emin=-10, Emax=20)

    assert context.Etiny() == -13
    assert context.Etop() == 17


def test_basic_and_extended_context_choose_debugging_vs_permissive_defaults():
    """BasicContext 开启多种 trap 便于调试；ExtendedContext 关闭 traps 并让信号流入结果。"""

    with localcontext(BasicContext):
        with pytest.raises(DivisionByZero):
            Decimal(1) / Decimal(0)

    with localcontext(ExtendedContext) as context:
        context.clear_flags()
        assert Decimal(1) / Decimal(0) == Decimal("Infinity")
        assert context.flags[DivisionByZero]


def test_decimal_signal_exception_hierarchy_supports_broad_or_specific_handling():
    """所有 signal 都是 DecimalException/ArithmeticError；部分还兼容内置异常类别。"""

    assert issubclass(DecimalException, ArithmeticError)
    assert issubclass(DivisionByZero, DecimalException)
    assert issubclass(DivisionByZero, ZeroDivisionError)
    assert issubclass(FloatOperation, TypeError)

    assert issubclass(Overflow, Inexact)
    assert issubclass(Overflow, Rounded)
    assert issubclass(Underflow, Inexact)
    assert issubclass(Underflow, Rounded)
    assert issubclass(Underflow, Subnormal)


# ``Decimal`` 表示比较、融合运算、相邻值与进阶工作流。
#
# 这一组覆盖 Decimal 专有而非普通算术表面的工具：representation total order、分类、
# ``fma``、十进制相邻值、digit-wise logical operations、scale/rotate/shift，以及工程记数。
# 最后用受限/提高 precision 的同一计算说明十进制精确表示仍不等于无限精度算术。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.decimal.remainder python.decimal.divide-integer
# polyglot-covers: python.decimal.compare python.decimal.compare_signal
# polyglot-covers: python.decimal.compare_total python.decimal.compare_total_mag
# polyglot-covers: python.decimal.copy_abs python.decimal.copy_negate python.decimal.copy_sign
# polyglot-covers: python.decimal.canonical python.decimal.conjugate
# polyglot-covers: python.decimal.fma python.decimal.exp python.decimal.ln python.decimal.log10
# polyglot-covers: python.decimal.sqrt python.decimal.logb
# polyglot-covers: python.decimal.number_class python.decimal.classification
# polyglot-covers: python.decimal.max python.decimal.min
# polyglot-covers: python.decimal.max_mag python.decimal.min_mag
# polyglot-covers: python.decimal.next_minus python.decimal.next_plus python.decimal.next_toward
# polyglot-covers: python.decimal.normalize python.decimal.remainder_near
# polyglot-covers: python.decimal.logical_and python.decimal.logical_or
# polyglot-covers: python.decimal.logical_xor python.decimal.logical_invert
# polyglot-covers: python.decimal.rotate python.decimal.shift python.decimal.scaleb
# polyglot-covers: python.decimal.same_quantum python.decimal.radix
# polyglot-covers: python.decimal.to_eng_string python.decimal.to_sci_string
# polyglot-covers: python.decimal.Context-arithmetic python.decimal.modular-power
# polyglot-covers: python.decimal.nan-comparison python.decimal.precision-loss-identities




def test_decimal_floor_division_and_remainder_truncate_toward_zero():
    """Decimal // 与 % 遵循 divide-integer/remainder，符号规则不同于 Python int 的 floor 模型。"""

    dividend = Decimal(-7)
    divisor = Decimal(4)

    quotient = dividend // divisor
    remainder = dividend % divisor

    assert quotient == Decimal(-1)
    assert remainder == Decimal(-3)
    assert dividend == quotient * divisor + remainder

    assert -7 // 4 == -2
    assert -7 % 4 == 1


def test_compare_returns_decimal_minus_one_zero_or_one_and_propagates_qnan():
    """compare 是十进制标准操作，返回 Decimal 状态值；qNaN 产生 qNaN 而非 bool。"""

    value = Decimal("12.0")

    assert value.compare(Decimal("11.9")) == Decimal(1)
    assert value.compare(Decimal("12")) == Decimal(0)
    assert value.compare(Decimal("12.1")) == Decimal(-1)
    assert value.compare(Decimal("NaN")).is_qnan()


def test_compare_signal_treats_quiet_nan_as_signaling():
    """compare 允许 qNaN 流动；compare_signal 连 quiet NaN 也触发 InvalidOperation。"""

    with localcontext() as context:
        context.traps[InvalidOperation] = True

        assert Decimal(1).compare(Decimal(2)) == Decimal(-1)
        with pytest.raises(InvalidOperation):
            Decimal(1).compare_signal(Decimal("NaN"))


def test_compare_total_orders_distinct_representations_that_are_numerically_equal():
    """普通 == 忽略有效位；compare_total 把 exponent/digits/NaN 等表示细节纳入全序。"""

    compact = Decimal("12")
    measured = Decimal("12.0")

    assert compact == measured
    assert measured.compare_total(compact) == Decimal(-1)
    assert compact.compare_total(measured) == Decimal(1)
    assert compact.compare_total(Decimal("12")) == Decimal(0)


def test_compare_total_mag_ignores_sign_but_keeps_other_representation_details():
    """total_mag 先取绝对值再做 representation order，适合按 magnitude 的稳定排序。"""

    negative = Decimal("-12.0")
    positive = Decimal("12.0")
    compact = Decimal("12")

    assert negative.compare_total_mag(positive) == Decimal(0)
    assert negative.compare_total_mag(compact) == Decimal(-1)


def test_copy_sign_operations_are_quiet_and_preserve_coefficient_and_exponent():
    """copy_abs/copy_negate/copy_sign 只改 sign bit，不按 context precision 重舍入。"""

    value = Decimal("-12.300")

    assert value.copy_abs() == Decimal("12.300")
    assert value.copy_negate() == Decimal("12.300")
    assert value.copy_sign(Decimal("0")) == Decimal("12.300")
    assert value.copy_sign(Decimal("-0")) == Decimal("-12.300")
    assert value.copy_abs().as_tuple().exponent == -3


def test_canonical_and_conjugate_return_the_same_decimal_object():
    """当前 Decimal 编码始终 canonical，且实数的 conjugate 不变；两方法直接返回 self。"""

    value = Decimal("1.2300")

    assert value.is_canonical()
    assert value.canonical() is value
    assert value.conjugate() is value


def test_fma_avoids_rounding_the_intermediate_product():
    """有限 precision 下 ``a*b+c`` 可能先丢抵消位；fma 只对最终结果舍入一次。"""

    with localcontext() as context:
        context.prec = 3
        left = Decimal("9.99")
        right = Decimal("9.99")
        correction = Decimal("-99.8")

        separate = left * right + correction
        fused = left.fma(right, correction)

    assert separate == Decimal("0.0")
    assert fused == Decimal("0.0001")


def test_decimal_transcendental_methods_obey_context_precision():
    """sqrt/exp/ln/log10 直接在十进制域计算，避免先经 binary float。"""

    with localcontext() as context:
        context.prec = 10

        square_root = Decimal(2).sqrt()
        exponential = Decimal(1).exp()
        logarithm = Decimal(10).ln()
        common_log = Decimal(1000).log10()

    assert square_root == Decimal("1.414213562")
    assert exponential == Decimal("2.718281828")
    assert logarithm == Decimal("2.302585093")
    assert common_log == Decimal(3)


def test_logb_returns_adjusted_exponent_and_signals_on_zero():
    """logb 是 Decimal 形式的 adjusted exponent；0 没有量级，返回 -Infinity 并置 DivByZero。"""

    assert Decimal("123.45").logb() == Decimal(2)
    assert Decimal("0.00123").logb() == Decimal(-3)
    assert Decimal("Infinity").logb() == Decimal("Infinity")

    with localcontext() as context:
        context.traps[DivisionByZero] = False
        context.clear_flags()

        assert Decimal(0).logb() == Decimal("-Infinity")
        assert context.flags[DivisionByZero]


def test_number_class_distinguishes_all_special_sign_and_magnitude_categories():
    """number_class 把 sign、normal/subnormal、zero、infinity 与两种 NaN 合成稳定标签。"""

    context = Context(prec=3, Emin=-2, Emax=2)
    # sNaN 会在 hash 时主动 signal，不能拿它当 dict key；分类表因此使用 pair 列表。
    examples = [
        (Decimal("-Infinity"), "-Infinity"),
        (Decimal("-1"), "-Normal"),
        (Decimal("-0.001"), "-Subnormal"),
        (Decimal("-0"), "-Zero"),
        (Decimal("0"), "+Zero"),
        (Decimal("0.001"), "+Subnormal"),
        (Decimal("1"), "+Normal"),
        (Decimal("Infinity"), "+Infinity"),
        (Decimal("NaN"), "NaN"),
        (Decimal("sNaN"), "sNaN"),
    ]

    for value, expected in examples:
        assert value.number_class(context=context) == expected


def test_decimal_classification_methods_are_orthogonal_predicates():
    """分类方法可组合使用，避免靠字符串猜 special value；signed 对 NaN/zero 也有意义。"""

    assert Decimal("1").is_finite()
    assert Decimal("1").is_normal()
    assert not Decimal("0").is_normal()

    assert Decimal("-Infinity").is_infinite()
    assert Decimal("-Infinity").is_signed()

    assert Decimal("-NaN").is_nan()
    assert Decimal("-NaN").is_qnan()
    assert Decimal("-NaN").is_signed()
    assert Decimal("sNaN").is_snan()


def test_decimal_max_min_can_ignore_nan_and_magnitude_variants_ignore_sign():
    """Decimal methods 应用 context 的 NaN 规则；*_mag 按绝对值选择而不是普通数值顺序。"""

    negative_large = Decimal("-10")
    positive_small = Decimal("3")

    assert negative_large.max(positive_small) == positive_small
    assert negative_large.min(positive_small) == negative_large
    assert negative_large.max_mag(positive_small) == negative_large
    assert negative_large.min_mag(positive_small) == positive_small

    assert positive_small.max(Decimal("NaN")) == positive_small


def test_next_plus_minus_and_toward_follow_context_representable_spacing():
    """十进制相邻间距随 decade 改变：1.00 上方是 1.01，下方是 0.999（prec=3）。"""

    context = Context(prec=3, Emin=-9, Emax=9)
    value = Decimal("1.00")

    assert value.next_plus(context=context) == Decimal("1.01")
    assert value.next_minus(context=context) == Decimal("0.999")
    assert value.next_toward(Decimal(2), context=context) == Decimal("1.01")
    assert value.next_toward(Decimal(0), context=context) == Decimal("0.999")

    signed_zero = Decimal("0").next_toward(Decimal("-0"), context=context)
    assert signed_zero.is_zero()
    assert signed_zero.is_signed()


def test_normalize_removes_trailing_zeros_but_numeric_equality_already_ignores_them():
    """normalize 为 equivalence class 生成简洁表示；它不是改变数值或强制固定小数位。"""

    variants = [Decimal("32.100"), Decimal("0.321000E+2")]

    assert variants[0] == variants[1]
    assert [value.normalize() for value in variants] == [Decimal("32.1"), Decimal("32.1")]
    assert Decimal("-0.00").normalize() == Decimal("-0")


def test_remainder_near_uses_nearest_even_quotient_unlike_percent():
    """nearest quotient 使余数绝对值最小；半整数 tie 选择偶数 quotient。"""

    assert Decimal(18).remainder_near(Decimal(10)) == Decimal(-2)
    assert Decimal(25).remainder_near(Decimal(10)) == Decimal(5)
    assert Decimal(35).remainder_near(Decimal(10)) == Decimal(-5)

    assert Decimal(18) % Decimal(10) == Decimal(8)


def test_logical_operations_apply_boolean_algebra_digit_by_digit():
    """logical operand 必须 sign/exponent 为 0 且 digits 仅 0/1；这里操作的是十进制 digits。"""

    left = Decimal("1100")
    right = Decimal("1010")
    context = Context(prec=4)

    assert left.logical_and(right, context=context) == Decimal("1000")
    assert left.logical_or(right, context=context) == Decimal("1110")
    assert left.logical_xor(right, context=context) == Decimal("110")
    assert left.logical_invert(context=context) == Decimal("11")

    with pytest.raises(InvalidOperation):
        Decimal("1200").logical_and(right, context=Context())


def test_rotate_and_shift_use_context_precision_as_the_coefficient_width():
    """rotate 把移出的 digits 绕回另一端；shift 丢弃移出 digits 并补零，sign/exponent 不变。"""

    value = Decimal("123456")
    context = Context(prec=6)

    assert value.rotate(Decimal(2), context=context) == Decimal("345612")
    assert value.rotate(Decimal(-2), context=context) == Decimal("561234")
    assert value.shift(Decimal(2), context=context) == Decimal("345600")
    assert value.shift(Decimal(-2), context=context) == Decimal("1234")


def test_scaleb_changes_exponent_without_binary_power_conversion():
    """scaleb(n) 等价乘 10**n，但直接调整十进制 exponent 并保留 coefficient。"""

    value = Decimal("1.23")
    scaled = value.scaleb(Decimal(3))

    assert scaled == Decimal("1230")
    assert scaled.as_tuple().digits == value.as_tuple().digits
    assert scaled.as_tuple().exponent == value.as_tuple().exponent + 3


def test_same_quantum_checks_exponent_not_numeric_scale_and_radix_is_ten():
    """quantum 相同意味着 exponent 相同；它比 == 更适合检查固定小数位 schema。"""

    assert Decimal("1.00").same_quantum(Decimal("2.00"))
    assert not Decimal("1.00").same_quantum(Decimal("1.0"))
    assert Decimal("NaN").same_quantum(Decimal("sNaN"))
    assert Decimal(1).radix() == Decimal(10)


def test_engineering_notation_uses_exponents_divisible_by_three():
    """engineering notation 便于 SI 前缀；scientific notation 则固定一位 lead digit。"""

    value = Decimal("1E+4")
    context = Context()

    assert value.to_eng_string() == "10E+3"
    assert context.to_sci_string(value) == "1E+4"
    assert Decimal("123E+1").to_eng_string() == "1.23E+3"


def test_context_methods_run_under_an_explicit_environment_without_installing_it():
    """Context.add/divide 等适合并列使用多套精度；无需修改当前 context。"""

    three_digits = Context(prec=3)
    six_digits = Context(prec=6)

    assert three_digits.divide(Decimal(1), Decimal(7)) == Decimal("0.143")
    assert six_digits.divide(Decimal(1), Decimal(7)) == Decimal("0.142857")
    assert three_digits.add(Decimal("1.234"), Decimal("2.345")) == Decimal("3.58")


def test_context_three_argument_power_computes_exact_modular_power():
    """三参数 power 在整数域高效计算 (x**y)%m；结果 exact 且 exponent 固定为 0。"""

    context = Context(prec=3)
    result = context.power(Decimal(7), Decimal(5), Decimal(13))

    assert result == Decimal(pow(7, 5, 13))
    assert result.as_tuple().exponent == 0


def test_decimal_compares_exactly_with_fraction_but_does_not_mix_arithmetic():
    """跨数值类型 comparison 支持精确语义；算术仍要求调用者主动选择 Decimal 或 Fraction。"""

    half = Decimal("0.5")

    assert half == Fraction(1, 2)
    assert Decimal("0.1") < Fraction(1, 3)

    with pytest.raises(TypeError, match="unsupported operand"):
        half + Fraction(1, 2)


def test_nan_equality_and_ordering_follow_different_signal_rules():
    """qNaN == 自身为 False 且 != 为 True；有序比较会发 InvalidOperation。"""

    nan = Decimal("NaN")

    assert not (nan == nan)
    assert nan != nan

    with localcontext() as context:
        context.clear_flags()
        context.traps[InvalidOperation] = False
        assert not (nan < Decimal(1))
        assert context.flags[InvalidOperation]

        context.traps[InvalidOperation] = True
        with pytest.raises(InvalidOperation):
            nan < Decimal(1)


def test_increasing_precision_can_restore_associative_identity_after_cancellation():
    """Decimal 消除 0.1 表示误差，却仍受 precision 舍入；提高中间精度可恢复代数恒等式。"""

    left = Decimal(11111113)
    middle = Decimal(-11111111)
    right = Decimal("7.51111111")

    with localcontext() as context:
        context.prec = 8
        low_left_grouping = (left + middle) + right
        low_right_grouping = left + (middle + right)

        context.prec = 20
        high_left_grouping = (left + middle) + right
        high_right_grouping = left + (middle + right)

    assert low_left_grouping == Decimal("9.5111111")
    assert low_right_grouping == Decimal("10")
    assert high_left_grouping == high_right_grouping == Decimal("9.51111111")
