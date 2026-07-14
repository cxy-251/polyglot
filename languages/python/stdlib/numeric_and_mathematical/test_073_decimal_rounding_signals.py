"""073｜``decimal`` 舍入模式、sticky flags、signal 与 trap。

Context 同时决定 precision、rounding、exponent 范围，并为每种异常条件维护 flag/trap。
flag 用于事后审计且会持续保留；trap 则把同一 signal 提升为异常。案例使用小型局部
context 主动制造 rounded、inexact、overflow、subnormal、underflow 和 clamped 状态。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.decimal.quantize python.decimal.fixed-exponent
# polyglot-covers: python.decimal.ROUND_CEILING python.decimal.ROUND_FLOOR
# polyglot-covers: python.decimal.ROUND_DOWN python.decimal.ROUND_UP python.decimal.ROUND_05UP
# polyglot-covers: python.decimal.ROUND_HALF_DOWN python.decimal.ROUND_HALF_EVEN python.decimal.ROUND_HALF_UP
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

import pytest


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
