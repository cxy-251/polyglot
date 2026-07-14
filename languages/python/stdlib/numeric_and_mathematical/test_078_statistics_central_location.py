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
