"""070｜``math`` 指数对数、三角/双曲、几何与特殊函数。

这些函数面向实数并通常返回 ``float``。案例既覆盖常用公式，也强调数值稳定接口：
小量用 ``expm1``/``log1p``，向量长度用 ``hypot``，正态分布尾部用 ``erfc``。
非法实数域会尽早抛异常；确实需要复数结果时应明确切换到 ``cmath``。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import math

import pytest


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
