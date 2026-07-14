"""079｜``statistics`` 离散程度、协方差、相关与线性回归。

总体方差使用 N 作分母，样本方差用 N-1 作 Bessel 校正；选择 API 前必须先判断
数据代表完整总体还是总体的样本。双变量函数按位置配对输入，长度、常量序列和样本量
都有明确约束，不能让 zip 式静默截断掩盖脏数据。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.statistics.pvariance python.statistics.population-denominator
# polyglot-covers: python.statistics.variance python.statistics.sample-bessel-correction
# polyglot-covers: python.statistics.pstdev python.statistics.stdev
# polyglot-covers: python.statistics.precomputed-mu python.statistics.precomputed-xbar
# polyglot-covers: python.statistics.unchecked-center python.statistics.spread-exact-types
# polyglot-covers: python.statistics.covariance python.statistics.sample-covariance
# polyglot-covers: python.statistics.correlation python.statistics.pearson-correlation
# polyglot-covers: python.statistics.linear_regression python.statistics.regression-result
# polyglot-covers: python.statistics.paired-input-length python.statistics.constant-input
# polyglot-covers: python.statistics.relation-positional-only python.statistics.python310-relations

from decimal import Decimal
from fractions import Fraction
from statistics import (
    StatisticsError,
    correlation,
    covariance,
    linear_regression,
    mean,
    pstdev,
    pvariance,
    stdev,
    variance,
)

import pytest


def test_population_and_sample_variance_use_different_denominators():
    """同一组数据作为完整总体时除以 N；作为样本估计总体时除以 N-1。"""

    data = [1, 2, 3]

    assert pvariance(data) == pytest.approx(2 / 3)
    assert variance(data) == pytest.approx(1.0)


def test_standard_deviation_is_the_square_root_of_matching_variance():
    """pstdev 必须配 pvariance、stdev 必须配 variance，不能交叉混用总体/样本语义。"""

    data = [1.5, 2.5, 2.5, 2.75, 3.25, 4.75]

    assert pstdev(data) ** 2 == pytest.approx(pvariance(data))
    assert stdev(data) ** 2 == pytest.approx(variance(data))


def test_population_spread_accepts_one_value_but_sample_spread_needs_two():
    """单元素完整总体的离散程度为零；单元素无法估计带 N-1 分母的样本方差。"""

    assert pvariance([42]) == 0
    assert pstdev([42]) == 0.0

    with pytest.raises(StatisticsError):
        variance([42])
    with pytest.raises(StatisticsError):
        stdev([42])


def test_empty_population_spread_raises_statistics_error():
    """空总体没有均值或离散程度，函数不会返回一个看似可传播的 NaN。"""

    with pytest.raises(StatisticsError):
        pvariance([])
    with pytest.raises(StatisticsError):
        pstdev([])


def test_precomputed_mean_avoids_recalculation_when_it_is_correct():
    """已经计算过中心值时可作为第二参数复用，结果应与内部计算一致。"""

    data = [0.0, 0.25, 0.25, 1.25, 1.5, 1.75, 2.75, 3.25]
    center = mean(data)

    assert pvariance(data, center) == pytest.approx(pvariance(data))
    assert variance(data, center) == pytest.approx(variance(data))


def test_supplied_center_is_trusted_and_not_checked_against_the_data():
    """mu/xbar 传错不会报错；函数围绕错误中心计算二阶矩，结果可以严重偏离。"""

    data = [0, 1, 2]

    assert pvariance(data, mu=0) == pytest.approx(5 / 3)
    assert pvariance(data) == pytest.approx(2 / 3)
    assert variance(data, xbar=0) == pytest.approx(5 / 2)
    assert variance(data) == pytest.approx(1)


def test_population_variance_preserves_fraction_and_decimal_results():
    """方差与 mean 一样支持同类精确数值；不需要为方便而先损失成 float。"""

    fractions = [Fraction(1, 4), Fraction(5, 4), Fraction(1, 2)]
    decimals = [Decimal("27.5"), Decimal("30.25"), Decimal("30.25"), Decimal("34.5"), Decimal("41.75")]

    fraction_result = pvariance(fractions)
    decimal_result = pvariance(decimals)

    assert fraction_result == Fraction(13, 72)
    assert decimal_result == Decimal("24.815")
    assert type(fraction_result) is Fraction
    assert type(decimal_result) is Decimal


def test_sample_variance_preserves_fraction_and_decimal_results():
    """N-1 校正不要求浮点运算，Fraction 与 Decimal 仍可保留各自精度模型。"""

    fractions = [Fraction(1, 6), Fraction(1, 2), Fraction(5, 3)]
    decimals = [Decimal("27.5"), Decimal("30.25"), Decimal("30.25"), Decimal("34.5"), Decimal("41.75")]

    assert variance(fractions) == Fraction(67, 108)
    assert variance(decimals) == Decimal("31.01875")


def test_covariance_measures_joint_sample_variation():
    """两个变量一起高于或低于各自均值时贡献为正，反向移动时贡献为负。"""

    x = [1, 2, 3]

    assert covariance(x, [2, 4, 6]) == pytest.approx(2.0)
    assert covariance(x, [6, 4, 2]) == pytest.approx(-2.0)
    assert covariance(x, [10, 10, 10]) == pytest.approx(0.0)


def test_covariance_is_symmetric_but_not_scale_free():
    """交换 x/y 不改变 covariance；放大一个变量会同比放大结果，因此不同单位难直接比较。"""

    x = [1, 2, 4, 8]
    y = [3, 1, 5, 7]

    assert covariance(x, y) == pytest.approx(covariance(y, x))
    assert covariance(x, [10 * value for value in y]) == pytest.approx(10 * covariance(x, y))


def test_correlation_is_scale_free_and_reports_linear_direction():
    """Pearson r 归一化到 [-1,1]；正比例为 +1，反比例为 -1。"""

    x = [1, 2, 3, 4, 5]

    assert correlation(x, [2, 4, 6, 8, 10]) == pytest.approx(1.0)
    assert correlation(x, [10, 8, 6, 4, 2]) == pytest.approx(-1.0)


def test_correlation_is_unchanged_by_positive_shift_and_scale():
    """改变原点或正向单位不改变线性相关强度；这正是它比 covariance 更易跨单位解释之处。"""

    x = [1, 2, 4, 8, 16]
    y = [2, 3, 7, 9, 20]
    transformed_y = [100 + 5 * value for value in y]

    assert correlation(x, transformed_y) == pytest.approx(correlation(x, y))


def test_linear_regression_returns_searchable_slope_and_intercept_fields():
    """3.10 返回 named tuple 风格结果，既可 unpack，也可按字段名访问，模型是 y=slope*x+intercept。"""

    result = linear_regression([0, 1, 2, 3], [1, 3, 5, 7])
    slope, intercept = result

    assert slope == pytest.approx(2.0)
    assert intercept == pytest.approx(1.0)
    assert result.slope == slope
    assert result.intercept == intercept


def test_linear_regression_supports_prediction_with_unexplained_residuals():
    """普通最小二乘给出最佳直线，不承诺每个带噪观测点都落在直线上。"""

    x = [0, 1, 2, 3, 4]
    y = [1.0, 2.9, 5.2, 6.8, 9.1]
    model = linear_regression(x, y)
    predictions = [model.slope * value + model.intercept for value in x]
    residuals = [actual - predicted for actual, predicted in zip(y, predictions)]

    assert sum(residuals) == pytest.approx(0.0, abs=1e-12)
    assert any(abs(residual) > 0.0 for residual in residuals)


@pytest.mark.parametrize("function", [covariance, correlation, linear_regression])
def test_relationship_functions_reject_mismatched_or_too_short_inputs(function):
    """双变量 API 不会像 zip 一样静默截断；必须是相同长度且至少包含两个配对点。"""

    with pytest.raises(StatisticsError):
        function([1, 2, 3], [4, 5])
    with pytest.raises(StatisticsError):
        function([1], [2])


def test_correlation_rejects_a_constant_input():
    """常量序列的标准差为零，Pearson r 分母为零，因此相关系数没有定义。"""

    with pytest.raises(StatisticsError):
        correlation([1, 1, 1], [2, 3, 4])
    with pytest.raises(StatisticsError):
        correlation([1, 2, 3], [4, 4, 4])


def test_linear_regression_rejects_constant_independent_variable():
    """所有 x 相同时没有横向变化可估计 slope；y 是否变化都无法解除这个约束。"""

    with pytest.raises(StatisticsError):
        linear_regression([1, 1, 1], [2, 3, 4])


@pytest.mark.parametrize("function", [covariance, correlation, linear_regression])
def test_python_310_relationship_arguments_are_positional_only(function):
    """签名中的 / 禁止用 x=、y= 调用；3.10 新增 API 时这就是公开调用契约。"""

    with pytest.raises(TypeError):
        function(x=[1, 2], y=[2, 4])
