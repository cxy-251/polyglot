"""071｜``cmath`` 复数函数、极坐标、分支切线与特殊值。

``cmath`` 接受实数和复数并始终返回 complex（分类/phase/polar 等明确例外）。复对数、
平方根和反函数必须选择 principal branch；落在 branch cut 上时，虚部或实部的
signed zero 用来区分从哪一侧逼近。本文件把这个不容易从表面调用看出的规则显式化。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import cmath
import math

import pytest


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
