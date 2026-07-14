"""069｜``math`` 离散计数、取整协议与浮点表示工具。

这一组覆盖不需要超越函数的 ``math`` 工作流：组合计数、整数根、积、精确求和、
容差比较，以及 IEEE-754 浮点的拆分、相邻值、ULP、余数和特殊值。重点区分
``fmod``/``remainder``/``%`` 三套余数规则，并展示 signed zero 不能只靠 ``==`` 观察。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

from fractions import Fraction
import math
import sys

import pytest


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


def test_python_310_factorial_still_accepts_integral_float_but_warns():
    """3.10 尚兼容 5.0，但该行为自 3.9 已弃用；新代码应始终传 int。"""

    with pytest.warns(DeprecationWarning, match="factorial.*floats"):
        result = math.factorial(5.0)

    assert result == 120


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
