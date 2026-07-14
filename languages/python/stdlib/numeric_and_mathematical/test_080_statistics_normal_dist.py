"""080｜``statistics.NormalDist`` 正态分布对象与概率工作流。

NormalDist 把均值与标准差组合成可变换、可求密度/累计概率/分位点的值对象。
两个 NormalDist 相加或相减时按“随机变量相互独立”合成方差；对象没有协方差信息，
因此不能用它表达相关变量相消。seeded samples 适合可重现实验，但仍不是跨版本数据协议。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import math
from statistics import NormalDist, StatisticsError

import pytest


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
