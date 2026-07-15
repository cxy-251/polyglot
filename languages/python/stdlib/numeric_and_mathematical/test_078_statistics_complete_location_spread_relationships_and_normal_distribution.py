"""078｜``statistics`` 集中趋势、众数与分位数。

标准库 statistics 面向计算器级别的实数统计，通常支持 int、float、Decimal 和
Fraction；混合数值类型的行为没有定义，真实数据应先统一类型。排序类统计遇到 NaN
也会产生意外结果，应把 NaN 当缺失值显式清洗，而不是期待函数自动忽略。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.statistics.mean python.statistics.exact-numeric-types
# polyglot-covers: python.statistics.fmean python.statistics.float-conversion
# polyglot-covers: python.statistics.geometric_mean python.statistics.geometric-domain
# polyglot-covers: python.statistics.harmonic_mean python.statistics.harmonic-weights
# polyglot-covers: python.statistics.harmonic-zero-early-out
# polyglot-covers: python.statistics.median python.statistics.median-even-interpolation
# polyglot-covers: python.statistics.median_low python.statistics.median_high
# polyglot-covers: python.statistics.median_grouped python.statistics.group-interval
# polyglot-covers: python.statistics.mode python.statistics.mode-first-tie
# polyglot-covers: python.statistics.multimode python.statistics.nominal-data
# polyglot-covers: python.statistics.quantiles python.statistics.quantiles-exclusive
# polyglot-covers: python.statistics.quantiles-inclusive python.statistics.quantile-interpolation
# polyglot-covers: python.statistics.nan-cleaning python.statistics.mixed-type-normalization
# polyglot-covers: python.statistics.StatisticsError python.statistics.iterable-input




from decimal import Decimal
from fractions import Fraction
from itertools import filterfalse
from math import isnan
from statistics import (
    StatisticsError,
    fmean,
    geometric_mean,
    harmonic_mean,
    mean,
    median,
    median_grouped,
    median_high,
    median_low,
    mode,
    multimode,
    quantiles,
)
import pytest
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
import math
from statistics import NormalDist, StatisticsError

def test_mean_preserves_fraction_and_decimal_arithmetic():
    """mean 不强制转 float，因此同类的精确数值输入可以保留精度和结果类型。"""

    fractions = [Fraction(3, 7), Fraction(1, 21), Fraction(5, 3), Fraction(1, 3)]
    decimals = [Decimal("0.5"), Decimal("0.75"), Decimal("0.625"), Decimal("0.375")]

    assert mean(fractions) == Fraction(13, 21)
    assert mean(decimals) == Decimal("0.5625")
    assert type(mean(fractions)) is Fraction
    assert type(mean(decimals)) is Decimal


def test_fmean_converts_inputs_and_always_returns_float():
    """fmean 用浮点路径换取速度；需要精确 Fraction/Decimal 结果时应选择 mean。"""

    values = [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)]
    result = fmean(values)

    assert result == 0.5
    assert type(result) is float


def test_average_functions_accept_one_shot_iterables():
    """data 可以是 iterable，不必预先 materialize；调用后生成器自然已经耗尽。"""

    values = (number for number in [2, 4, 6, 8])

    assert mean(values) == 5
    assert list(values) == []


def test_empty_arithmetic_means_raise_statistics_error():
    """空数据没有平均值；StatisticsError 比返回 NaN 或 sentinel 更早暴露数据问题。"""

    with pytest.raises(StatisticsError):
        mean([])
    with pytest.raises(StatisticsError):
        fmean([])


def test_geometric_mean_describes_multiplicative_growth():
    """几何平均使用乘积而非总和，适合增长因子等乘法过程并返回 float。"""

    result = geometric_mean([1, 4, 16])

    assert result == pytest.approx(4.0)
    assert type(result) is float


@pytest.mark.parametrize("values", [[], [0, 2], [-1, 2]])
def test_geometric_mean_rejects_empty_or_nonpositive_data(values):
    """3.10 的 geometric_mean 定义域要求所有数据严格大于零。"""

    with pytest.raises(StatisticsError):
        geometric_mean(values)


def test_harmonic_mean_is_suited_to_equal_distance_rates():
    """相同路程分别以 40/60 km/h 行驶时应平均时间倒数，不能直接算术平均成 50。"""

    assert harmonic_mean([40, 60]) == 48.0


def test_python_310_harmonic_mean_weights_model_unequal_exposure():
    """3.10 新增 weights；5 km 与 30 km 的路段让较长路段对平均速度贡献更大。"""

    assert harmonic_mean([40, 60], weights=[5, 30]) == 56.0


def test_harmonic_mean_zero_early_out_is_a_version_specific_validation_trap():
    """3.10 遇到零会立即返回零，后面的负数不再校验；不要依赖此实现细节清洗数据。"""

    assert harmonic_mean([0, -1]) == 0

    with pytest.raises(StatisticsError):
        harmonic_mean([-1, 0])


def test_median_handles_odd_and_even_numeric_datasets_differently():
    """奇数个点返回中点；偶数个点插值两个中央值，结果不一定存在于原数据中。"""

    assert median([5, 1, 3]) == 3
    assert median([1, 3, 5, 7]) == 4.0
    assert 4.0 not in [1, 3, 5, 7]


def test_median_is_more_robust_to_an_outlier_than_mean():
    """极端值显著拉动算术平均，而排序后的中央位置保持稳定。"""

    data = [10, 11, 12, 13, 10_000]

    assert mean(data) == pytest.approx(2009.2)
    assert median(data) == 12


def test_low_and_high_medians_keep_an_observed_ordinal_value():
    """序数数据只需可排序；low/high 不做加法，因此也能处理偶数个非数值标签。"""

    ratings = ["D", "A", "C", "B"]

    assert median_low(ratings) == "B"
    assert median_high(ratings) == "C"
    with pytest.raises(TypeError):
        median(ratings)


def test_grouped_median_interpolates_inside_a_frequency_bin():
    """输入值代表组中点，interval 是组宽；函数不会验证真实数据是否符合分组假设。"""

    data = [1, 3, 3, 5, 7]

    assert median_grouped(data, interval=1) == pytest.approx(3.25)
    assert median_grouped(data, interval=2) == pytest.approx(3.5)


def test_mode_supports_nominal_data_and_resolves_ties_by_first_encounter():
    """mode 不要求数值运算；频率相同则返回输入中最先出现者，而不是最小值。"""

    colors = ["red", "blue", "blue", "red", "green"]

    assert mode(colors) == "red"


def test_multimode_returns_all_ties_in_first_encounter_order():
    """需要保留全部并列众数时使用 multimode；空输入的结果是空 list，不抛异常。"""

    assert multimode("aabbbbccddddeeffffgg") == ["b", "d", "f"]
    assert multimode(()) == []


def test_mode_empty_input_raises_while_multimode_returns_empty_list():
    """单一 mode 无法为“无数据”选择值，两个 API 的空输入契约刻意不同。"""

    with pytest.raises(StatisticsError):
        mode([])
    assert multimode([]) == []


def test_quantiles_return_n_minus_one_linearly_interpolated_cut_points():
    """n 表示区间数量而非切点数量；四分位数因此返回三个 cut points。"""

    result = quantiles([0, 10, 20, 30, 40], n=4)

    assert result == pytest.approx([5.0, 20.0, 35.0])
    assert len(result) == 3


def test_exclusive_and_inclusive_quantiles_encode_different_population_assumptions():
    """exclusive 假设总体还可超出样本端点；inclusive 把样本 min/max 当总体 0%/100%。"""

    data = [0, 10, 20, 30, 40]

    assert quantiles(data, n=4, method="exclusive") == pytest.approx([5, 20, 35])
    assert quantiles(data, n=4, method="inclusive") == pytest.approx([10, 20, 30])


def test_quantiles_validate_interval_count_method_and_sample_size():
    """n 至少为 1、算法名必须受支持，而且插值至少需要两个数据点。"""

    assert quantiles([1, 2], n=1) == []

    with pytest.raises(StatisticsError):
        quantiles([1, 2], n=0)
    with pytest.raises(ValueError):
        quantiles([1, 2], method="nearest")
    with pytest.raises(StatisticsError):
        quantiles([1], n=4)


def test_nan_values_are_removed_before_sorting_based_statistics():
    """NaN 的比较不满足普通全序；把它当缺失值清洗后 median/quantiles 才有明确定义。"""

    raw = [20.7, float("nan"), 19.2, 18.3, float("nan"), 14.4]
    clean = list(filterfalse(isnan, raw))

    assert clean == [20.7, 19.2, 18.3, 14.4]
    assert median(clean) == pytest.approx(18.75)


def test_mixed_numeric_sources_are_normalized_before_statistics():
    """混用 Decimal/Fraction/float 的行为未定义；map(float, ...) 建立明确的共同算术域。"""

    raw = [Decimal("1.5"), Fraction(5, 2), 3.0]
    normalized = list(map(float, raw))

    assert normalized == [1.5, 2.5, 3.0]
    assert mean(normalized) == pytest.approx(7 / 3)


def test_statistics_error_is_a_specialized_value_error():
    """调用者既可精准捕获统计输入错误，也可用 ValueError 统一处理非法值。"""

    assert issubclass(StatisticsError, ValueError)


# 079｜``statistics`` 离散程度、协方差、相关与线性回归。
#
# 总体方差使用 N 作分母，样本方差用 N-1 作 Bessel 校正；选择 API 前必须先判断
# 数据代表完整总体还是总体的样本。双变量函数按位置配对输入，长度、常量序列和样本量
# 都有明确约束，不能让 zip 式静默截断掩盖脏数据。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

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


# 080｜``statistics.NormalDist`` 正态分布对象与概率工作流。
#
# NormalDist 把均值与标准差组合成可变换、可求密度/累计概率/分位点的值对象。
# 两个 NormalDist 相加或相减时按“随机变量相互独立”合成方差；对象没有协方差信息，
# 因此不能用它表达相关变量相消。seeded samples 适合可重现实验，但仍不是跨版本数据协议。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.statistics.NormalDist python.statistics.normal-properties
# polyglot-covers: python.statistics.NormalDist-negative-sigma python.statistics.NormalDist-read-only
# polyglot-covers: python.statistics.NormalDist.from_samples python.statistics.NormalDist.samples
# polyglot-covers: python.statistics.NormalDist.pdf python.statistics.density-not-probability
# polyglot-covers: python.statistics.NormalDist.cdf python.statistics.interval-probability
# polyglot-covers: python.statistics.NormalDist.inv_cdf python.statistics.cdf-round-trip
# polyglot-covers: python.statistics.NormalDist.overlap python.statistics.NormalDist.quantiles
# polyglot-covers: python.statistics.NormalDist.zscore python.statistics.standard-score
# polyglot-covers: python.statistics.NormalDist-translate python.statistics.NormalDist-scale
# polyglot-covers: python.statistics.NormalDist-add python.statistics.NormalDist-subtract
# polyglot-covers: python.statistics.independent-normal-variables python.statistics.uncertainty-propagation




def test_constructor_exposes_center_and_spread_as_read_only_properties():
    """正态分布的 mean/median/mode 相同，variance 是 stdev 的平方。"""

    distribution = NormalDist(mu=10.0, sigma=2.5)

    assert distribution.mean == 10.0
    assert distribution.median == 10.0
    assert distribution.mode == 10.0
    assert distribution.stdev == 2.5
    assert distribution.variance == 6.25

    with pytest.raises(AttributeError):
        distribution.mean = 20.0


def test_default_distribution_is_standard_normal_and_negative_sigma_is_invalid():
    """默认值是 N(0,1)；标准差可以为零但不能为负数。"""

    standard = NormalDist()
    point_mass = NormalDist(5.0, 0.0)

    assert (standard.mean, standard.stdev) == (0.0, 1.0)
    assert (point_mass.mean, point_mass.stdev) == (5.0, 0.0)

    with pytest.raises(StatisticsError):
        NormalDist(0.0, -0.1)


def test_from_samples_estimates_mean_and_sample_standard_deviation():
    """from_samples 使用 fmean 与 stdev；三个点 [1,2,3] 的样本标准差是 1。"""

    fitted = NormalDist.from_samples(value for value in [1, 2, 3])

    assert fitted.mean == pytest.approx(2.0)
    assert fitted.stdev == pytest.approx(1.0)

    with pytest.raises(StatisticsError):
        NormalDist.from_samples([1])


def test_seeded_samples_are_reproducible_and_use_a_private_generator():
    """传 seed 会新建底层 Random，因此并发调用可各自重放，不共享模块级推进状态。"""

    distribution = NormalDist(100.0, 15.0)

    first = distribution.samples(8, seed="experiment-80")
    second = distribution.samples(8, seed="experiment-80")

    assert first == second
    assert len(first) == 8
    assert all(type(value) is float for value in first)


def test_pdf_is_symmetric_and_maximal_at_the_mean():
    """pdf 是单位宽度上的密度而非点概率；正态曲线在均值处最高并左右对称。"""

    distribution = NormalDist(10.0, 2.0)

    assert distribution.pdf(8.0) == pytest.approx(distribution.pdf(12.0))
    assert distribution.pdf(10.0) > distribution.pdf(8.0)
    assert distribution.pdf(-math.inf) == 0.0
    assert distribution.pdf(math.inf) == 0.0


def test_probability_density_can_be_greater_than_one():
    """窄分布的 pdf 峰值可大于 1；只有对区间积分后的 probability 才必须位于 [0,1]。"""

    narrow = NormalDist(0.0, 0.1)

    assert narrow.pdf(0.0) > 1.0


def test_cdf_is_monotone_and_equals_one_half_at_the_mean():
    """cdf(x)=P(X<=x)；它随 x 单调增加，正态分布的均值把概率质量平分。"""

    distribution = NormalDist(10.0, 2.0)

    probabilities = [distribution.cdf(value) for value in [6.0, 10.0, 14.0]]

    assert probabilities == sorted(probabilities)
    assert probabilities[1] == pytest.approx(0.5)
    assert distribution.cdf(-math.inf) == 0.0
    assert distribution.cdf(math.inf) == 1.0


def test_interval_probability_is_the_difference_between_two_cdf_values():
    """连续变量落在 [low,high] 的概率用 cdf(high)-cdf(low) 计算，端点本身概率为零。"""

    distribution = NormalDist(100.0, 15.0)
    within_one_sigma = distribution.cdf(115.0) - distribution.cdf(85.0)

    assert within_one_sigma == pytest.approx(0.682689492, rel=1e-8)


def test_inverse_cdf_round_trips_interior_probabilities():
    """inv_cdf 是 quantile function；仅对严格位于 (0,1) 的概率有有限分位点。"""

    distribution = NormalDist(20.0, 3.0)

    for probability in [0.01, 0.25, 0.5, 0.9, 0.99]:
        quantile = distribution.inv_cdf(probability)
        assert distribution.cdf(quantile) == pytest.approx(probability, abs=1e-12)

    with pytest.raises(StatisticsError):
        distribution.inv_cdf(0.0)
    with pytest.raises(StatisticsError):
        distribution.inv_cdf(1.0)


def test_normal_quantiles_split_the_distribution_into_equal_probability_intervals():
    """quantiles(n) 返回 n-1 个切点；对称分布的中央切点就是 mean。"""

    distribution = NormalDist(10.0, 2.0)
    quartiles = distribution.quantiles()
    deciles = distribution.quantiles(n=10)

    assert len(quartiles) == 3
    assert quartiles[1] == pytest.approx(distribution.mean)
    assert quartiles[0] + quartiles[2] == pytest.approx(2 * distribution.mean)
    assert len(deciles) == 9
    assert deciles == sorted(deciles)


def test_overlap_is_symmetric_and_one_for_identical_distributions():
    """overlap 返回两条 pdf 重叠面积；完全相同为 1，分离后介于 0 和 1。"""

    first = NormalDist(0.0, 1.0)
    second = NormalDist(2.0, 1.5)

    assert first.overlap(first) == pytest.approx(1.0)
    assert 0.0 < first.overlap(second) < 1.0
    assert first.overlap(second) == pytest.approx(second.overlap(first))


def test_zscore_reports_signed_standard_deviation_distance():
    """zscore(x)=(x-mean)/stdev；负值在均值下方，绝对值表示相距几个标准差。"""

    distribution = NormalDist(10.0, 2.0)

    assert distribution.zscore(14.0) == pytest.approx(2.0)
    assert distribution.zscore(7.0) == pytest.approx(-1.5)
    assert distribution.zscore(10.0) == pytest.approx(0.0)


def test_translation_changes_mean_without_changing_standard_deviation():
    """加减常数只是平移全部样本，离散程度保持不变，并返回新的 NormalDist。"""

    original = NormalDist(10.0, 2.0)
    translated = original + 5.0
    shifted_back = translated - 3.0

    assert (translated.mean, translated.stdev) == (15.0, 2.0)
    assert (shifted_back.mean, shifted_back.stdev) == (12.0, 2.0)
    assert (original.mean, original.stdev) == (10.0, 2.0)


def test_scaling_transforms_mean_and_absolute_standard_deviation():
    """乘常数缩放均值，stdev 乘绝对值；负比例会镜像均值但不产生负标准差。"""

    distribution = NormalDist(10.0, 2.0)
    doubled = distribution * 2.0
    reflected = distribution * -3.0
    halved = distribution / 2.0

    assert (doubled.mean, doubled.stdev) == (20.0, 4.0)
    assert (reflected.mean, reflected.stdev) == (-30.0, 6.0)
    assert (halved.mean, halved.stdev) == (5.0, 1.0)


def test_temperature_conversion_composes_scale_then_translation():
    """对象运算可直接表达 Celsius 到 Fahrenheit，标准差只受比例 9/5 影响。"""

    celsius = NormalDist(5.0, 2.5)
    fahrenheit = celsius * (9 / 5) + 32

    assert fahrenheit.mean == pytest.approx(41.0)
    assert fahrenheit.stdev == pytest.approx(4.5)


def test_unsupported_scalar_division_directions_fail_explicitly():
    """distribution/constant 仍为正态；constant/distribution 通常不是正态，因此未定义。"""

    distribution = NormalDist(10.0, 2.0)

    with pytest.raises(TypeError):
        10.0 / distribution
    with pytest.raises(ZeroDivisionError):
        distribution / 0.0


def test_independent_normal_sums_add_means_and_variances():
    """独立随机变量相加时均值相加，标准差按 hypot 合成而不是直接相加。"""

    first = NormalDist(10.0, 3.0)
    second = NormalDist(2.0, 4.0)
    combined = first + second

    assert combined.mean == pytest.approx(12.0)
    assert combined.stdev == pytest.approx(5.0)
    assert combined.variance == pytest.approx(first.variance + second.variance)


def test_independent_normal_difference_still_combines_uncertainty():
    """相减只减均值；独立误差的方差仍相加，所以不应把 stdev 写成 3-4。"""

    first = NormalDist(10.0, 3.0)
    second = NormalDist(2.0, 4.0)
    difference = first - second

    assert difference.mean == pytest.approx(8.0)
    assert difference.stdev == pytest.approx(5.0)


def test_subtracting_the_same_object_illustrates_the_independence_assumption():
    """NormalDist 不记录相关性；dist-dist 被解释为两个独立同分布变量，而非同一变量减自身。"""

    distribution = NormalDist(10.0, 3.0)
    modeled_difference = distribution - distribution

    assert modeled_difference.mean == pytest.approx(0.0)
    assert modeled_difference.stdev == pytest.approx(3.0 * math.sqrt(2.0))
