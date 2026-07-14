"""074｜``Decimal`` 表示比较、融合运算、相邻值与进阶工作流。

这一组覆盖 Decimal 专有而非普通算术表面的工具：representation total order、分类、
``fma``、十进制相邻值、digit-wise logical operations、scale/rotate/shift，以及工程记数。
最后用受限/提高 precision 的同一计算说明十进制精确表示仍不等于无限精度算术。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.decimal.remainder python.decimal.divide-integer
# polyglot-covers: python.decimal.compare python.decimal.compare_signal
# polyglot-covers: python.decimal.compare_total python.decimal.compare_total_mag
# polyglot-covers: python.decimal.copy_abs python.decimal.copy_negate python.decimal.copy_sign
# polyglot-covers: python.decimal.canonical python.decimal.conjugate
# polyglot-covers: python.decimal.fma python.decimal.exp python.decimal.ln python.decimal.log10
# polyglot-covers: python.decimal.sqrt python.decimal.logb
# polyglot-covers: python.decimal.number_class python.decimal.classification
# polyglot-covers: python.decimal.max python.decimal.min python.decimal.max_mag python.decimal.min_mag
# polyglot-covers: python.decimal.next_minus python.decimal.next_plus python.decimal.next_toward
# polyglot-covers: python.decimal.normalize python.decimal.remainder_near
# polyglot-covers: python.decimal.logical_and python.decimal.logical_or
# polyglot-covers: python.decimal.logical_xor python.decimal.logical_invert
# polyglot-covers: python.decimal.rotate python.decimal.shift python.decimal.scaleb
# polyglot-covers: python.decimal.same_quantum python.decimal.radix
# polyglot-covers: python.decimal.to_eng_string python.decimal.to_sci_string
# polyglot-covers: python.decimal.Context-arithmetic python.decimal.modular-power
# polyglot-covers: python.decimal.nan-comparison python.decimal.precision-loss-identities

from decimal import Context, Decimal, DivisionByZero, InvalidOperation, localcontext
from fractions import Fraction

import pytest


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
