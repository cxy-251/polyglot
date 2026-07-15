"""056｜``numbers`` 数值抽象基类、跨类型相等与算术双分派。

``Number -> Complex -> Real -> Rational -> Integral`` 是逐层增强的能力分类，
适合判断调用者真正需要哪组数值协议。它不是要求所有“看起来像数字”的类型强行继承
同一个具体实现。本文件也用 ``Fraction`` 和最小自定义类型展示混合算术的
``__op__`` / ``__rop__`` fallback 规则。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.numbers.Number python.numbers.numeric-tower
# polyglot-covers: python.numbers.Complex python.numbers.Real
# polyglot-covers: python.numbers.Rational python.numbers.Integral
# polyglot-covers: python.numbers.builtin-classification python.numbers.bool-is-integral
# polyglot-covers: python.numbers.abstract-operations python.numbers.virtual-subclass
# polyglot-covers: python.numbers.extensible-tower python.numbers.abc-register
# polyglot-covers: python.numbers.rational-invariants python.numbers.cross-type-hash
# polyglot-covers: python.numbers.mixed-mode-arithmetic python.numbers.builtin-fallback
# polyglot-covers: python.numeric-dispatch.NotImplemented python.numeric-dispatch.reflected-operation
# polyglot-covers: python.numeric-dispatch.subclass-priority python.numeric-dispatch.type-error




from abc import abstractmethod
from fractions import Fraction
import numbers
import pytest
import math
import sys
import cmath
from decimal import Decimal

def test_numeric_tower_abc_subclass_relationships_run_from_specific_to_general():
    """越靠下的 ABC 承诺越多；Integral 同时满足上方所有数值类别。"""

    assert issubclass(numbers.Integral, numbers.Rational)
    assert issubclass(numbers.Rational, numbers.Real)
    assert issubclass(numbers.Real, numbers.Complex)
    assert issubclass(numbers.Complex, numbers.Number)

    assert not issubclass(numbers.Real, numbers.Rational)
    assert not issubclass(numbers.Complex, numbers.Real)


def test_builtin_numeric_types_enter_the_tower_at_different_levels():
    """int、float、complex 分别停在 Integral、Real、Complex；不要只检查 Number 后猜能力。"""

    assert isinstance(3, numbers.Integral)
    assert isinstance(3, numbers.Rational)
    assert isinstance(3, numbers.Real)
    assert isinstance(3, numbers.Complex)
    assert isinstance(3, numbers.Number)

    assert isinstance(3.5, numbers.Real)
    assert not isinstance(3.5, numbers.Rational)

    assert isinstance(3 + 4j, numbers.Complex)
    assert not isinstance(3 + 4j, numbers.Real)


def test_bool_is_integral_because_bool_is_a_subclass_of_int():
    """``True``/``False`` 会通过 Integral 检查；若布尔值在业务上无效，必须额外排除。"""

    assert issubclass(bool, int)
    assert isinstance(True, numbers.Integral)
    assert isinstance(False, numbers.Number)

    def require_non_boolean_integer(value):
        if isinstance(value, bool) or not isinstance(value, numbers.Integral):
            raise TypeError("a non-boolean integer is required")
        return int(value)

    assert require_non_boolean_integer(7) == 7
    with pytest.raises(TypeError, match="non-boolean integer"):
        require_non_boolean_integer(True)


def test_fraction_is_rational_and_exposes_normalized_integral_components():
    """Rational 要求分子分母为 Integral、约至最简且分母为正；Fraction 落实这些不变量。"""

    value = Fraction(-6, -8)

    assert isinstance(value, numbers.Rational)
    assert isinstance(value, numbers.Real)
    assert not isinstance(value, numbers.Integral)
    assert value == Fraction(3, 4)
    assert value.numerator == 3
    assert value.denominator == 4
    assert isinstance(value.numerator, numbers.Integral)


def test_each_tower_level_corresponds_to_additional_protocols():
    """实例展示各层新增能力：complex components、real rounding、rational parts、integer bits。"""

    complex_value = 3 + 4j
    real_value = 3.75
    rational_value = Fraction(7, 3)
    integral_value = 6

    assert complex_value.real == 3
    assert complex_value.imag == 4
    assert complex_value.conjugate() == 3 - 4j
    assert abs(complex_value) == 5

    assert round(real_value) == 4
    assert real_value // 2 == 1.0
    assert divmod(real_value, 2) == (1.0, 1.75)

    assert (rational_value.numerator, rational_value.denominator) == (7, 3)
    assert integral_value << 1 == 12
    assert integral_value & 3 == 2


@pytest.mark.parametrize(
    "abstract_type",
    [numbers.Complex, numbers.Real, numbers.Rational, numbers.Integral],
)
def test_specific_numeric_abcs_cannot_be_instantiated_without_abstract_operations(abstract_type):
    """这些类描述协议而非现成数值；缺少抽象运算的直接实例化会被 ABCMeta 拒绝。"""

    assert abstract_type.__abstractmethods__
    with pytest.raises(TypeError, match="abstract class"):
        abstract_type()


def test_number_is_a_broad_classification_not_a_specific_arithmetic_contract():
    """只需要 abs 的函数可接收 Number；需要 floor/bit 操作时应选择更具体 ABC。"""

    def magnitude(value):
        if not isinstance(value, numbers.Number):
            raise TypeError("number required")
        return abs(value)

    assert magnitude(-4) == 4
    assert magnitude(3 + 4j) == 5
    with pytest.raises(TypeError, match="number required"):
        magnitude("4")


def test_virtual_registration_changes_classification_but_does_not_mix_in_methods():
    """ABC.register 只声明外部类型符合协议；它不会复制 Real 的默认属性或实现。"""

    class ExternalMeasurement:
        pass

    numbers.Real.register(ExternalMeasurement)
    value = ExternalMeasurement()

    assert isinstance(value, numbers.Real)
    assert isinstance(value, numbers.Number)
    assert not hasattr(value, "real")
    with pytest.raises(TypeError):
        float(value)


def test_a_domain_abc_can_be_inserted_between_complex_and_real():
    """自定义层继承 Complex，再把 Real 注册为虚拟子类，就能扩展而不修改标准数值塔。"""

    class Measurable(numbers.Complex):
        @abstractmethod
        def uncertainty(self):
            """返回该数值的测量误差。"""

    Measurable.register(numbers.Real)

    assert issubclass(numbers.Real, Measurable)
    assert isinstance(1.5, Measurable)
    assert isinstance(2, Measurable)
    assert not isinstance(1 + 2j, Measurable)


def test_equal_values_from_different_numeric_types_must_share_the_same_hash():
    """跨类型相等必须满足 hash 不变量，否则 dict/set 会保存逻辑重复的 key。"""

    integer = 2
    rational = Fraction(2, 1)
    real = 2.0
    complex_value = 2 + 0j

    assert integer == rational == real == complex_value
    assert hash(integer) == hash(rational) == hash(real) == hash(complex_value)
    assert len({integer, rational, real, complex_value}) == 1


def test_fraction_hashes_like_an_exactly_equal_float_when_equality_is_exact():
    """二分数可被 float 精确表示时也要共享 hash；不可精确表示时通常并不相等。"""

    exact = Fraction(1, 2)
    inexact = Fraction(1, 10)

    assert exact == 0.5
    assert hash(exact) == hash(0.5)

    assert inexact != 0.1
    assert float(inexact) == 0.1


def test_fraction_mixed_arithmetic_preserves_exactness_until_a_wider_fallback_is_needed():
    """已知 int/Fraction 时返回 Fraction；遇到 float/complex 则转换到最近共同内置类型。"""

    value = Fraction(1, 3)

    with_integer = value + 1
    with_fraction = value + Fraction(1, 6)
    with_float = value + 0.5
    with_complex = value + 1j

    assert with_integer == Fraction(4, 3)
    assert type(with_integer) is Fraction
    assert with_fraction == Fraction(1, 2)
    assert type(with_fraction) is Fraction
    assert type(with_float) is float
    assert with_float == float(value) + 0.5
    assert type(with_complex) is complex
    assert with_complex == complex(value) + 1j


def test_reverse_fraction_operation_handles_a_left_hand_integral():
    """``int + Fraction`` 先给 int.__add__，其 NotImplemented 让 Fraction.__radd__ 保留精度。"""

    result = 2 + Fraction(1, 3)

    assert result == Fraction(7, 3)
    assert type(result) is Fraction


def test_notimplemented_from_forward_operation_gives_reflected_operation_a_chance():
    """运算方法应返回 NotImplemented（不是抛异常），让右操作数处理它认识的组合。"""

    calls = []

    class LeftNumber:
        def __add__(self, other):
            calls.append("left.__add__")
            return NotImplemented

    class RightNumber:
        def __radd__(self, other):
            calls.append("right.__radd__")
            return "handled by right"

    assert LeftNumber() + RightNumber() == "handled by right"
    assert calls == ["left.__add__", "right.__radd__"]


def test_right_subclass_reflected_method_gets_priority_over_left_base_method():
    """右侧类型是左侧类型子类时，Python 先试更具体的子类 __radd__。"""

    calls = []

    class BaseNumber:
        def __add__(self, other):
            calls.append("base.__add__")
            return "base result"

    class SpecializedNumber(BaseNumber):
        def __radd__(self, other):
            calls.append("specialized.__radd__")
            return "specialized result"

    result = BaseNumber() + SpecializedNumber()

    assert result == "specialized result"
    assert calls == ["specialized.__radd__"]


def test_type_error_is_raised_only_after_both_arithmetic_sides_decline():
    """双方都返回 NotImplemented 后，解释器才产生最终的 unsupported operand TypeError。"""

    calls = []

    class LeftNumber:
        def __add__(self, other):
            calls.append("left")
            return NotImplemented

    class RightNumber:
        def __radd__(self, other):
            calls.append("right")
            return NotImplemented

    with pytest.raises(TypeError, match="unsupported operand"):
        LeftNumber() + RightNumber()

    assert calls == ["left", "right"]


# ``math`` 离散计数、取整协议与浮点表示工具。
#
# 这一组覆盖不需要超越函数的 ``math`` 工作流：组合计数、整数根、积、精确求和、
# 容差比较，以及 IEEE-754 浮点的拆分、相邻值、ULP、余数和特殊值。重点区分
# ``fmod``/``remainder``/``%`` 三套余数规则，并展示 signed zero 不能只靠 ``==`` 观察。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.math.ceil python.math.floor python.math.trunc
# polyglot-covers: python.protocol.__ceil__ python.protocol.__floor__ python.protocol.__trunc__
# polyglot-covers: python.math.comb python.math.perm python.math.factorial
# polyglot-covers: python.math.gcd python.math.lcm python.math.isqrt
# polyglot-covers: python.math.prod python.math.prod-start
# polyglot-covers: python.math.copysign python.math.signed-zero python.math.fabs
# polyglot-covers: python.math.fmod python.math.remainder python.float.modulo-semantics
# polyglot-covers: python.math.frexp python.math.ldexp python.math.modf
# polyglot-covers: python.math.fsum python.float.cancellation
# polyglot-covers: python.math.isclose python.math.relative-tolerance python.math.absolute-tolerance
# polyglot-covers: python.math.isfinite python.math.isinf python.math.isnan
# polyglot-covers: python.math.nextafter python.math.ulp python.float.adjacent-values




def test_ceil_floor_and_trunc_round_negative_values_in_three_directions():
    """ceil 向正无穷、floor 向负无穷、trunc 向零；负数最能暴露三者差异。"""

    value = -1.75

    assert math.ceil(value) == -1
    assert math.floor(value) == -2
    assert math.trunc(value) == -1
    assert all(type(result) is int for result in (math.ceil(value), math.floor(value), math.trunc(value)))


def test_rounding_functions_delegate_to_non_float_special_methods():
    """非 float 对象分别走 __ceil__/__floor__/__trunc__，协议结果应是 Integral。"""

    calls = []

    class BoundedValue:
        def __ceil__(self):
            calls.append("ceil")
            return 8

        def __floor__(self):
            calls.append("floor")
            return 7

        def __trunc__(self):
            calls.append("trunc")
            return 7

    value = BoundedValue()

    assert math.ceil(value) == 8
    assert math.floor(value) == 7
    assert math.trunc(value) == 7
    assert calls == ["ceil", "floor", "trunc"]


def test_comb_counts_unordered_choices_and_returns_zero_when_k_exceeds_n():
    """comb 不考虑排列顺序；选 0 个只有一种方案，k > n 则没有方案。"""

    assert math.comb(5, 2) == 10
    assert math.comb(5, 3) == 10
    assert math.comb(5, 0) == 1
    assert math.comb(2, 5) == 0


def test_perm_counts_ordered_choices_and_defaults_to_factorial():
    """perm 考虑顺序；省略 k 等价于排列全部 n 个元素。"""

    assert math.perm(5, 2) == 20
    assert math.perm(5, 0) == 1
    assert math.perm(5) == math.factorial(5) == 120
    assert math.perm(2, 5) == 0


@pytest.mark.parametrize("operation", [math.comb, math.perm])
def test_comb_and_perm_require_nonnegative_integer_arguments(operation):
    """离散计数不默默截断 float；非整数报 TypeError，负数报 ValueError。"""

    with pytest.raises(TypeError):
        operation(5.0, 2)
    with pytest.raises(ValueError):
        operation(-1, 0)
    with pytest.raises(ValueError):
        operation(5, -1)


def test_factorial_handles_zero_and_rejects_negative_values():
    """0! 定义为 1；负整数没有该组合意义，因此不是返回 NaN 而是抛 ValueError。"""

    assert math.factorial(0) == 1
    assert math.factorial(6) == 720

    with pytest.raises(ValueError):
        math.factorial(-1)


def test_python_310_factorial_rejects_integral_float():
    """3.10 已移除 integral float 兼容路径；即使是 5.0 也必须显式转成 int。"""

    with pytest.raises(TypeError, match="integer"):
        math.factorial(5.0)


def test_gcd_is_variadic_nonnegative_and_has_a_zero_argument_identity():
    """3.9+ gcd 接受任意个整数；结果非负，空参数返回 0。"""

    assert math.gcd(54, 24) == 6
    assert math.gcd(54, -24, 18) == 6
    assert math.gcd(0, 0) == 0
    assert math.gcd() == 0


def test_lcm_is_variadic_and_zero_absorbs_the_product():
    """lcm 也在 3.9+ 支持多参数；空参数单位元是 1，任一参数为 0 时结果为 0。"""

    assert math.lcm(4, 6, 10) == 60
    assert math.lcm(-4, 6) == 12
    assert math.lcm(7) == 7
    assert math.lcm(3, 0, 5) == 0
    assert math.lcm() == 1


def test_isqrt_returns_exact_floor_without_converting_large_int_to_float():
    """isqrt 在整数域计算 floor(sqrt(n))，大整数不会先丢到有限精度 float。"""

    root = 10**40 + 12345
    square = root * root

    assert math.isqrt(square) == root
    assert math.isqrt(square + root) == root
    assert math.isqrt(square - 1) == root - 1

    with pytest.raises(ValueError):
        math.isqrt(-1)
    with pytest.raises(TypeError):
        math.isqrt(4.0)


def test_isqrt_recipe_computes_the_ceiling_square_root_for_positive_n():
    """正整数的 ceil(sqrt(n)) 可用 ``1 + isqrt(n - 1)``，全程保持整数精度。"""

    def ceil_sqrt(value):
        if value == 0:
            return 0
        return 1 + math.isqrt(value - 1)

    assert [ceil_sqrt(value) for value in (0, 1, 2, 4, 5, 9, 10)] == [0, 1, 2, 2, 3, 3, 4]


def test_prod_multiplies_iterables_and_start_participates_in_the_result():
    """start 不是空输入专用默认值，而是总会作为第一个乘数参与。"""

    assert math.prod([2, 3, 4]) == 24
    assert math.prod((value for value in range(1, 5))) == 24
    assert math.prod([2, 3], start=10) == 60
    assert math.prod([], start=7) == 7
    assert math.prod([]) == 1


def test_prod_can_preserve_an_exact_numeric_type_through_start():
    """以 Fraction 为 start 时运算走其乘法协议，可避免不必要的 float 转换。"""

    result = math.prod([2, Fraction(3, 5)], start=Fraction(1, 2))

    assert result == Fraction(3, 5)
    assert type(result) is Fraction


def test_copysign_exposes_negative_zero_that_numeric_equality_hides():
    """0.0 == -0.0，但 sign bit 影响部分数值算法；用 copysign 观察或复制符号。"""

    negative_zero = math.copysign(0.0, -1.0)

    assert negative_zero == 0.0
    assert math.copysign(1.0, negative_zero) == -1.0
    assert math.copysign(3.5, -0.0) == -3.5
    assert math.copysign(-3.5, 0.0) == 3.5


def test_fabs_converts_to_float_instead_of_using_the_objects_abs_protocol():
    """内置 abs 走 __abs__；math.fabs 先按浮点协议转换并固定返回 float。"""

    class Measurement:
        def __abs__(self):
            return "domain magnitude"

        def __float__(self):
            return -3.5

    value = Measurement()

    assert abs(value) == "domain magnitude"
    assert math.fabs(value) == 3.5
    assert type(math.fabs(4)) is float


def test_fmod_and_percent_choose_the_sign_from_different_operands():
    """fmod 的余数跟 x 同号，Python % 的余数跟除数 y 同号；浮点计算应按需求选择。"""

    assert math.fmod(-5.5, 2.0) == -1.5
    assert -5.5 % 2.0 == 0.5

    assert math.fmod(5.5, -2.0) == 1.5
    assert 5.5 % -2.0 == -0.5


def test_frexp_and_ldexp_portably_split_and_rebuild_binary_float():
    """frexp 返回 x == mantissa * 2**exponent 的精确拆分，ldexp 是其逆操作。"""

    value = -123.75
    mantissa, exponent = math.frexp(value)

    assert 0.5 <= abs(mantissa) < 1.0
    assert type(exponent) is int
    assert math.ldexp(mantissa, exponent) == value
    assert math.frexp(0.0) == (0.0, 0)


def test_modf_returns_signed_fractional_then_integral_parts_as_floats():
    """返回顺序是 (fractional, integral)，两部分都保留 x 的符号且类型为 float。"""

    fractional, integral = math.modf(-3.75)

    assert fractional == -0.75
    assert integral == -3.0
    assert type(fractional) is type(integral) is float

    zero_fraction, integer = math.modf(-4.0)
    assert integer == -4.0
    assert math.copysign(1.0, zero_fraction) == -1.0


def test_fsum_tracks_partial_sums_to_recover_values_lost_by_naive_sum():
    """大数加小数再抵消时，逐步 sum 会吞掉小数；fsum 保存多个 partial。"""

    values = [1e16, 1.0, -1e16]

    assert sum(values) == 0.0
    assert math.fsum(values) == 1.0
    assert math.fsum([0.1] * 10) == 1.0


def test_isclose_combines_relative_and_absolute_tolerance():
    """允许误差是 relative scale 与 absolute floor 的较大者，而不是固定小数位数。"""

    assert math.isclose(1_000_000.0, 1_000_000.5, rel_tol=1e-6)
    assert not math.isclose(1_000_000.0, 1_000_002.0, rel_tol=1e-6)

    assert not math.isclose(0.0, 1e-12)
    assert math.isclose(0.0, 1e-12, abs_tol=1e-11)


def test_isclose_rejects_negative_tolerances_and_handles_ieee_special_values():
    """容差不得为负；NaN 永不接近，正负 infinity 只接近同号自身。"""

    with pytest.raises(ValueError, match="tolerances must be non-negative"):
        math.isclose(1.0, 1.0, rel_tol=-1e-9)
    with pytest.raises(ValueError, match="tolerances must be non-negative"):
        math.isclose(1.0, 1.0, abs_tol=-1e-9)

    assert not math.isclose(math.nan, math.nan)
    assert math.isclose(math.inf, math.inf)
    assert math.isclose(-math.inf, -math.inf)
    assert not math.isclose(math.inf, -math.inf)


def test_classification_functions_are_the_correct_way_to_detect_special_floats():
    """NaN 不等于自身，因此应用 isnan；isfinite 同时排除两种 infinity 与 NaN。"""

    assert math.isfinite(0.0)
    assert math.isfinite(-1e300)
    assert not math.isfinite(math.inf)
    assert not math.isfinite(-math.inf)
    assert not math.isfinite(math.nan)

    assert math.isinf(math.inf)
    assert math.isinf(-math.inf)
    assert not math.isinf(math.nan)

    assert math.isnan(math.nan)
    assert math.nan != math.nan


def test_nextafter_moves_exactly_one_representable_float_toward_the_target():
    """连续实数之间有无数值，float 却离散；nextafter 给出指定方向的紧邻表示。"""

    upward = math.nextafter(1.0, math.inf)
    downward = math.nextafter(1.0, 0.0)

    assert upward > 1.0
    assert downward < 1.0
    assert math.nextafter(upward, 0.0) == 1.0
    assert math.nextafter(downward, math.inf) == 1.0
    assert math.nextafter(2.0, 2.0) == 2.0


def test_ulp_measures_local_spacing_and_connects_to_nextafter():
    """1.0 处的 ULP 是机器 epsilon；0.0 处则是最小正 subnormal。"""

    assert math.ulp(1.0) == sys.float_info.epsilon
    assert math.nextafter(1.0, math.inf) == 1.0 + math.ulp(1.0)
    assert math.nextafter(0.0, math.inf) == math.ulp(0.0)
    assert math.ulp(-1.0) == math.ulp(1.0)
    assert math.ulp(math.inf) == math.inf
    assert math.isnan(math.ulp(math.nan))


def test_ieee_remainder_uses_nearest_even_quotient_not_floor_or_truncation():
    """商正好在两个整数中间时选偶数：7/2 选 4 得 -1，5/2 选 2 得 +1。"""

    assert math.remainder(7.0, 2.0) == -1.0
    assert math.remainder(5.0, 2.0) == 1.0
    assert math.remainder(-7.0, 2.0) == 1.0
    assert abs(math.remainder(100.0, 9.0)) <= 4.5


def test_ieee_remainder_preserves_zero_sign_and_rejects_undefined_inputs():
    """零结果跟 x 同号；零除数或 infinite x 没有有限 IEEE remainder。"""

    negative_zero = math.remainder(-4.0, 2.0)
    assert negative_zero == 0.0
    assert math.copysign(1.0, negative_zero) == -1.0
    assert math.remainder(3.0, math.inf) == 3.0

    with pytest.raises(ValueError):
        math.remainder(1.0, 0.0)
    with pytest.raises(ValueError):
        math.remainder(math.inf, 2.0)


# ``math`` 指数对数、三角/双曲、几何与特殊函数。
#
# 这些函数面向实数并通常返回 ``float``。案例既覆盖常用公式，也强调数值稳定接口：
# 小量用 ``expm1``/``log1p``，向量长度用 ``hypot``，正态分布尾部用 ``erfc``。
# 非法实数域会尽早抛异常；确实需要复数结果时应明确切换到 ``cmath``。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.math.exp python.math.expm1 python.math.e
# polyglot-covers: python.math.log python.math.log1p python.math.log2 python.math.log10
# polyglot-covers: python.math.pow python.math.sqrt python.math.real-domain
# polyglot-covers: python.math.sin python.math.cos python.math.tan
# polyglot-covers: python.math.asin python.math.acos python.math.atan python.math.atan2
# polyglot-covers: python.math.degrees python.math.radians python.math.pi python.math.tau
# polyglot-covers: python.math.hypot python.math.dist python.math.python310-hypot-accuracy
# polyglot-covers: python.math.sinh python.math.cosh python.math.tanh
# polyglot-covers: python.math.asinh python.math.acosh python.math.atanh
# polyglot-covers: python.math.erf python.math.erfc python.math.normal-cdf
# polyglot-covers: python.math.gamma python.math.lgamma
# polyglot-covers: python.math.domain-error python.math.overflow-error python.math.complex-rejection




def test_exp_and_log_are_inverse_on_positive_real_values():
    """自然指数与自然对数在正实数域互逆；浮点结果用 isclose 比较。"""

    for value in (0.125, 1.0, 10.0):
        assert math.isclose(math.log(math.exp(value)), value, rel_tol=1e-14)

    assert math.isclose(math.exp(1.0), math.e, rel_tol=0.0, abs_tol=1e-15)


def test_expm1_preserves_small_increment_lost_by_exp_then_subtract():
    """x 很小时 exp(x) 与 1 接近，先舍入再相减会丢有效位；expm1 一步计算更准确。"""

    value = 1e-10
    stable = math.expm1(value)
    naive = math.exp(value) - 1.0

    # exp(x)-1 = x + x²/2 + ...；与 x 的差应约为 5e-21。
    assert abs(stable - value) < abs(naive - value)
    assert math.isclose(stable, value + value * value / 2, rel_tol=1e-15)


def test_log1p_retains_an_increment_that_rounds_away_in_one_plus_x():
    """1 + 1e-16 在 binary64 中舍入为 1，普通 log 得 0；log1p 仍看得到原始 x。"""

    value = 1e-16

    assert 1.0 + value == 1.0
    assert math.log(1.0 + value) == 0.0
    assert math.log1p(value) != 0.0
    assert math.isclose(math.log1p(value), value, rel_tol=1e-15)


def test_log_supports_custom_base_while_specialized_bases_are_clearer():
    """两参数 log 计算 log(x)/log(base)；常见 2、10 底优先用专门函数。"""

    assert math.isclose(math.log(81, 3), 4.0)
    assert math.log2(1024) == 10.0
    assert math.log10(1_000_000) == 6.0
    assert math.isclose(math.log(math.e), 1.0)


def test_math_pow_converts_to_float_while_builtin_power_can_keep_big_int_exact():
    """math.pow 固定走 C double；整数精确幂应使用 ``**`` 或内置 pow。"""

    floating = math.pow(10, 6)
    exact = 10**100

    assert floating == 1_000_000.0
    assert type(floating) is float
    assert type(exact) is int
    assert len(str(exact)) == 101

    with pytest.raises(OverflowError):
        math.pow(10, 1000)
    assert 10**1000 > 0


def test_negative_fractional_power_marks_the_boundary_between_math_and_cmath():
    """负底数的非整数实数幂不在 math 实数域；``**`` 可产生 complex，但应明确选择。"""

    with pytest.raises(ValueError, match="math domain error"):
        math.pow(-1.0, 0.5)
    with pytest.raises(ValueError, match="math domain error"):
        math.sqrt(-1.0)

    complex_result = (-1.0) ** 0.5
    assert math.isclose(complex_result.real, 0.0, abs_tol=1e-15)
    assert math.isclose(complex_result.imag, 1.0)


def test_sqrt_returns_float_and_isqrt_should_be_used_for_exact_integer_roots():
    """sqrt 即使输入完美平方也返回 float；大整数精确根由上一套的 isqrt 负责。"""

    assert math.sqrt(81) == 9.0
    assert type(math.sqrt(81)) is float
    assert math.isclose(math.sqrt(2) ** 2, 2.0)


def test_trigonometric_functions_use_radians_and_satisfy_the_unit_circle_identity():
    """math 三角函数的角度单位是弧度；sin²+cos² 只应近似比较。"""

    angle = math.pi / 6

    assert math.isclose(math.sin(angle), 0.5)
    assert math.isclose(math.cos(angle), math.sqrt(3) / 2)
    assert math.isclose(math.tan(angle), 1 / math.sqrt(3))
    assert math.isclose(math.sin(angle) ** 2 + math.cos(angle) ** 2, 1.0)


def test_inverse_trigonometric_functions_return_documented_principal_ranges():
    """反函数只返回 principal value：asin/atan 在 ±π/2，acos 在 0..π。"""

    asin_value = math.asin(0.5)
    acos_value = math.acos(0.5)
    atan_value = math.atan(1.0)

    assert math.isclose(asin_value, math.pi / 6)
    assert math.isclose(acos_value, math.pi / 3)
    assert math.isclose(atan_value, math.pi / 4)
    assert -math.pi / 2 <= asin_value <= math.pi / 2
    assert 0.0 <= acos_value <= math.pi


def test_atan2_uses_both_signs_to_choose_the_correct_quadrant():
    """atan(y/x) 丢失象限且 x=0 会失败；atan2(y, x) 保留两坐标符号。"""

    assert math.isclose(math.atan2(1.0, 1.0), math.pi / 4)
    assert math.isclose(math.atan2(1.0, -1.0), 3 * math.pi / 4)
    assert math.isclose(math.atan2(-1.0, -1.0), -3 * math.pi / 4)
    assert math.isclose(math.atan2(1.0, 0.0), math.pi / 2)


def test_atan2_distinguishes_signed_zero_on_the_negative_real_axis():
    """分支切线上 +0 与 -0 选择 +π/-π；普通数值相等无法表达这一区别。"""

    positive_side = math.atan2(0.0, -1.0)
    negative_side = math.atan2(-0.0, -1.0)

    assert positive_side == math.pi
    assert negative_side == -math.pi


def test_degree_radian_conversions_make_units_explicit():
    """外部接口常用 degree，三角函数用 radian；边界处显式转换避免静默量纲错误。"""

    assert math.isclose(math.radians(180.0), math.pi)
    assert math.isclose(math.degrees(math.pi / 2), 90.0)

    angle = 123.456
    assert math.isclose(math.degrees(math.radians(angle)), angle)
    assert math.tau == 2 * math.pi


def test_hypot_computes_n_dimensional_norm_without_intermediate_overflow():
    """3.8+ hypot 接受任意维；缩放算法避免先算 x*x 造成的 overflow/underflow。"""

    assert math.hypot(3.0, 4.0) == 5.0
    assert math.hypot(1.0, 2.0, 2.0) == 3.0
    assert math.hypot() == 0.0

    stable = math.hypot(1e200, 1e200)
    naive = math.sqrt(1e200 * 1e200 + 1e200 * 1e200)

    assert math.isfinite(stable)
    assert naive == math.inf
    assert math.isclose(stable / 1e200, math.sqrt(2))


def test_python_310_hypot_is_accurate_to_within_one_ulp_for_typical_inputs():
    """3.10 改进了 hypot 算法；经典 3-4-5 及缩放变体得到正确舍入结果。"""

    result = math.hypot(3e100, 4e100)
    expected = 5e100

    assert abs(result - expected) <= math.ulp(expected)


def test_dist_computes_point_distance_and_requires_matching_dimensions():
    """dist 对两个同维坐标做欧氏距离；维度不一致不会静默 zip 截断。"""

    assert math.dist((0, 0), (3, 4)) == 5.0
    assert math.dist((0, 0, 0), (1, 2, 2)) == 3.0
    assert math.dist((value for value in (1, 1)), (4, 5)) == 5.0

    with pytest.raises(ValueError, match="same number of dimensions"):
        math.dist((0, 0), (1, 2, 3))


def test_hyperbolic_functions_and_inverses_round_trip_in_their_real_domains():
    """双曲函数基于 hyperbola；inverse 的实数域分别受 acosh>=1、|atanh|<1 限制。"""

    value = 0.5

    assert math.isclose(math.cosh(value) ** 2 - math.sinh(value) ** 2, 1.0)
    assert math.isclose(math.asinh(math.sinh(value)), value)
    assert math.isclose(math.acosh(math.cosh(value)), value)
    assert math.isclose(math.atanh(math.tanh(value)), value)

    with pytest.raises(ValueError):
        math.acosh(0.5)
    with pytest.raises(ValueError):
        math.atanh(1.0)


def test_erf_builds_standard_normal_cdf_and_erfc_preserves_small_tail_values():
    """erf 可构造标准正态 CDF；大 x 时用 erfc 避免 ``1 - erf(x)`` catastrophic cancellation。"""

    def normal_cdf(value):
        return (1.0 + math.erf(value / math.sqrt(2.0))) / 2.0

    assert normal_cdf(0.0) == 0.5
    assert math.isclose(normal_cdf(1.0), 0.8413447460685429)
    assert math.erf(-1.0) == -math.erf(1.0)
    assert math.isclose(math.erf(1.0) + math.erfc(1.0), 1.0)

    assert 1.0 - math.erf(10.0) == 0.0
    assert math.erfc(10.0) > 0.0


def test_gamma_extends_factorial_and_lgamma_avoids_huge_intermediate_results():
    """正整数 n 的 gamma(n)=(n-1)!；lgamma 直接给绝对值对数，可跨过 gamma overflow。"""

    assert math.gamma(6) == math.factorial(5) == 120
    assert math.isclose(math.gamma(0.5), math.sqrt(math.pi))
    assert math.isclose(math.lgamma(6), math.log(math.gamma(6)))

    with pytest.raises(OverflowError):
        math.gamma(200)
    assert math.isfinite(math.lgamma(200))


def test_special_constant_and_nan_exceptions_follow_c99_rules():
    """少数 Annex F 特例会覆盖普通 NaN 传播：任意数的 0 次幂和 1 的任意幂为 1。"""

    assert math.pow(math.nan, 0.0) == 1.0
    assert math.pow(1.0, math.nan) == 1.0
    assert math.hypot(math.nan, math.inf) == math.inf


def test_math_reports_domain_overflow_and_complex_inputs_instead_of_hiding_them():
    """无效实数域、不可表示的大结果和意外 complex 分别尽早暴露。"""

    with pytest.raises(ValueError, match="math domain error"):
        math.log(0.0)
    with pytest.raises(ValueError, match="math domain error"):
        math.asin(2.0)
    with pytest.raises(OverflowError, match="math range error"):
        math.exp(1000.0)
    with pytest.raises(TypeError, match="must be real number"):
        math.sqrt(1 + 0j)


# ``cmath`` 复数函数、极坐标、分支切线与特殊值。
#
# ``cmath`` 接受实数和复数并始终返回 complex（分类/phase/polar 等明确例外）。复对数、
# 平方根和反函数必须选择 principal branch；落在 branch cut 上时，虚部或实部的
# signed zero 用来区分从哪一侧逼近。本文件把这个不容易从表面调用看出的规则显式化。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.cmath.complex-input python.cmath.always-complex
# polyglot-covers: python.protocol.__complex__ python.cmath.float-fallback
# polyglot-covers: python.cmath.phase python.cmath.polar python.cmath.rect
# polyglot-covers: python.cmath.signed-zero python.cmath.branch-cut
# polyglot-covers: python.cmath.sqrt python.cmath.exp python.cmath.log python.cmath.log10
# polyglot-covers: python.cmath.sin python.cmath.cos python.cmath.tan
# polyglot-covers: python.cmath.asin python.cmath.acos python.cmath.atan
# polyglot-covers: python.cmath.sinh python.cmath.cosh python.cmath.tanh
# polyglot-covers: python.cmath.asinh python.cmath.acosh python.cmath.atanh
# polyglot-covers: python.cmath.isclose python.cmath.isfinite python.cmath.isinf python.cmath.isnan
# polyglot-covers: python.cmath.pi python.cmath.e python.cmath.tau
# polyglot-covers: python.cmath.inf python.cmath.infj python.cmath.nan python.cmath.nanj




def test_elementary_cmath_functions_accept_real_inputs_but_return_complex():
    """即使答案完全为实数，cmath 仍保留 complex 类型，避免根据数据值改变返回类型。"""

    results = [
        cmath.sqrt(4),
        cmath.exp(0.0),
        cmath.log(math.e),
        cmath.sin(0),
        cmath.cosh(0),
    ]

    expected = [2 + 0j, 1 + 0j, 1 + 0j, 0 + 0j, 1 + 0j]
    assert all(cmath.isclose(result, target) for result, target in zip(results, expected))
    assert all(type(result) is complex for result in results)


def test_cmath_prefers_complex_conversion_protocol_when_available():
    """自定义数值可实现 __complex__；同时存在 __float__ 时，复数协议表达的信息更完整。"""

    calls = []

    class Phasor:
        def __complex__(self):
            calls.append("complex")
            return 3 + 4j

        def __float__(self):
            calls.append("float")
            return 999.0

    result = cmath.sqrt(Phasor())

    assert cmath.isclose(result * result, 3 + 4j)
    assert calls == ["complex"]


def test_cmath_falls_back_to_float_protocol_when_complex_is_absent():
    """只有 __float__ 的对象也可输入；它先变成实数，再嵌入虚部为零的复平面。"""

    class RealMeasurement:
        def __float__(self):
            return 9.0

    result = cmath.sqrt(RealMeasurement())

    assert result == 3 + 0j
    assert type(result) is complex


def test_complex_protocol_must_return_an_actual_complex_instance():
    """__complex__ 不能只返回“可再次转换”的任意对象，协议返回类型错误会立即暴露。"""

    class Broken:
        def __complex__(self):
            return "3+4j"

    with pytest.raises(TypeError, match="__complex__ returned non-complex"):
        cmath.sqrt(Broken())


def test_phase_matches_atan2_and_abs_supplies_the_modulus():
    """cmath 没有 abs 函数；复数模用内置 abs，phase 等价于 atan2(imag, real)。"""

    value = -3 + 4j

    assert abs(value) == 5.0
    assert cmath.phase(value) == math.atan2(value.imag, value.real)
    assert -math.pi <= cmath.phase(value) <= math.pi
    assert not hasattr(cmath, "abs")


def test_polar_returns_modulus_and_phase_and_rect_round_trips():
    """polar 在直角坐标与 (r, phi) 之间转换；rect 是反向构造。"""

    value = -3 + 4j
    radius, phase = cmath.polar(value)
    restored = cmath.rect(radius, phase)

    assert radius == abs(value) == 5.0
    assert phase == cmath.phase(value)
    assert cmath.isclose(restored, value, rel_tol=1e-15, abs_tol=1e-15)


def test_phase_uses_imaginary_signed_zero_on_the_negative_real_axis():
    """同一个 -1 数值从 branch cut 上方/下方逼近，phase 分别选择 +π/-π。"""

    above = complex(-1.0, 0.0)
    below = complex(-1.0, -0.0)

    assert cmath.phase(above) == math.pi
    assert cmath.phase(below) == -math.pi


def test_sqrt_branch_cut_uses_signed_zero_to_choose_imaginary_sign():
    """负实轴是 sqrt 的 cut；虚部 +0 得正虚根，-0 得负虚根。"""

    above = cmath.sqrt(complex(-2.0, 0.0))
    below = cmath.sqrt(complex(-2.0, -0.0))

    assert above.real == below.real == 0.0
    assert math.isclose(above.imag, math.sqrt(2.0))
    assert math.isclose(below.imag, -math.sqrt(2.0))
    assert cmath.isclose(above * above, -2 + 0j)
    assert cmath.isclose(below * below, -2 + 0j)


def test_log_branch_cut_chooses_positive_or_negative_pi():
    """负实轴上的 principal log 实部为 log(|z|)，虚部由 signed zero 选择 ±π。"""

    above = cmath.log(complex(-2.0, 0.0))
    below = cmath.log(complex(-2.0, -0.0))

    assert math.isclose(above.real, math.log(2.0))
    assert math.isclose(below.real, math.log(2.0))
    assert above.imag == math.pi
    assert below.imag == -math.pi


def test_exp_and_log_round_trip_away_from_the_log_branch_cut():
    """principal log 丢弃相差 2πi 的分支；选在 principal strip 内即可稳定往返。"""

    value = 0.75 + 0.5j

    assert cmath.isclose(cmath.log(cmath.exp(value)), value)
    assert cmath.isclose(cmath.exp(cmath.log(value)), value)


def test_complex_log_supports_a_complex_base_and_log10():
    """两参数 log 按 ``log(x)/log(base)``；log10 是常用底的专门入口。"""

    assert cmath.isclose(cmath.log(8, 2), 3 + 0j)
    assert cmath.isclose(cmath.log(-8, 2), cmath.log(-8) / cmath.log(2))
    assert cmath.isclose(cmath.log10(1000), 3 + 0j)


def test_complex_exponential_encodes_eulers_identity():
    """``exp(iφ)=cosφ+i sinφ`` 把极坐标旋转与指数连接起来。"""

    value = cmath.exp(1j * math.pi)

    assert cmath.isclose(value, -1 + 0j, abs_tol=1e-15)
    assert cmath.isclose(cmath.exp(1j * math.pi / 2), 1j, abs_tol=1e-15)


def test_complex_trigonometric_identity_and_tangent_relation_hold():
    """复数域仍有 sin²+cos²=1，且 tan=sin/cos；使用 isclose 吸收舍入。"""

    value = 0.4 + 0.2j
    sine = cmath.sin(value)
    cosine = cmath.cos(value)

    assert cmath.isclose(sine * sine + cosine * cosine, 1 + 0j)
    assert cmath.isclose(cmath.tan(value), sine / cosine)


def test_inverse_complex_trigonometric_functions_use_principal_values():
    """在远离 branch cut 的小值上可往返；越过 cut 后不应假定恢复原分支。"""

    value = 0.25 + 0.1j

    assert cmath.isclose(cmath.asin(cmath.sin(value)), value)
    assert cmath.isclose(cmath.acos(cmath.cos(value)), value)
    assert cmath.isclose(cmath.atan(cmath.tan(value)), value)


def test_trigonometric_and_hyperbolic_functions_are_linked_by_imaginary_rotation():
    """sin(i x)=i sinh(x)、cos(i x)=cosh(x)，说明两族函数并非无关 API。"""

    value = 0.75

    assert cmath.isclose(cmath.sin(1j * value), 1j * cmath.sinh(value))
    assert cmath.isclose(cmath.cos(1j * value), cmath.cosh(value))
    assert cmath.isclose(cmath.tan(1j * value), 1j * cmath.tanh(value))


def test_complex_hyperbolic_identity_and_inverses_round_trip_near_origin():
    """在 principal branch 邻域，cosh²-sinh²=1 且三种 inverse 可恢复输入。"""

    value = 0.4 + 0.2j

    assert cmath.isclose(cmath.cosh(value) ** 2 - cmath.sinh(value) ** 2, 1 + 0j)
    assert cmath.isclose(cmath.asinh(cmath.sinh(value)), value)
    assert cmath.isclose(cmath.acosh(cmath.cosh(value)), value)
    assert cmath.isclose(cmath.atanh(cmath.tanh(value)), value)


def test_complex_isclose_uses_magnitude_of_the_difference_and_needs_abs_tol_near_zero():
    """误差度量是复平面距离 abs(a-b)；接近原点时相对容差仍需 absolute floor。"""

    base = 1000 + 1000j
    nearby = base + (1e-7 - 1e-7j)

    assert cmath.isclose(base, nearby, rel_tol=1e-9)
    assert not cmath.isclose(0j, 1e-12 + 1e-12j)
    assert cmath.isclose(0j, 1e-12 + 1e-12j, abs_tol=2e-12)


def test_complex_classification_checks_both_components_independently():
    """isfinite 要求两部分都有限；isinf/isnan 任一部分命中即为真，二者可能同时为真。"""

    assert cmath.isfinite(1 + 2j)
    assert not cmath.isfinite(complex(math.inf, 0.0))
    assert not cmath.isfinite(complex(0.0, math.nan))

    assert cmath.isinf(complex(0.0, math.inf))
    assert cmath.isnan(complex(math.nan, 0.0))

    mixed = complex(math.nan, math.inf)
    assert cmath.isinf(mixed)
    assert cmath.isnan(mixed)


def test_complex_isclose_follows_ieee_nan_and_infinity_rules():
    """含 NaN 的数永不 close；同一个 infinity 只接近自身，有限扰动不能吸收 infinity。"""

    infinity = complex(math.inf, 1.0)

    assert cmath.isclose(infinity, infinity)
    assert not cmath.isclose(infinity, complex(math.inf, 2.0))
    assert not cmath.isclose(complex(math.nan, 0.0), complex(math.nan, 0.0))


def test_cmath_constants_match_math_and_provide_imaginary_special_values():
    """pi/e/tau/inf/nan 是 float；infj/nanj 把特殊值放在虚部以便直接构造复数。"""

    assert cmath.pi == math.pi
    assert cmath.e == math.e
    assert cmath.tau == math.tau
    assert cmath.inf == math.inf
    assert math.isnan(cmath.nan)

    assert cmath.infj.real == 0.0
    assert math.isinf(cmath.infj.imag)
    assert cmath.nanj.real == 0.0
    assert math.isnan(cmath.nanj.imag)


# ``fractions.Fraction`` 精确有理数、构造归一化与分母限制近似。
#
# Fraction 永远保存最简整数分子和正分母，适合比例、概率和需要绝对精确除法的离散领域。
# 从 float 构造会忠实保留 binary64 的真实值；从十进制字符串或 Decimal 构造才表达
# 人看到的十进制值。``limit_denominator`` 用于明确地把近似值恢复为小分母比例。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

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
