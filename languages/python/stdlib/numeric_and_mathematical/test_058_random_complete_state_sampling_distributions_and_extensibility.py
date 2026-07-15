"""058｜``random`` 可复现状态、整数生成与序列抽样。

测试和模拟应各自持有 ``Random`` 实例并显式 seed，避免模块级隐藏实例的共享状态。
这些案例只比较同 seed/同 state 的确定性结果，或验证 API 保证的集合与范围不变量；
不以少量抽样频率证明概率分布。Mersenne Twister 也绝不能用于安全 token。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.random.Random python.random.independent-instance
# polyglot-covers: python.random.seed python.random.seed-version python.random.reproducibility
# polyglot-covers: python.random.getstate python.random.setstate
# polyglot-covers: python.random.random python.random.mersenne-twister python.random.not-cryptographic
# polyglot-covers: python.random.randbytes python.random.getrandbits
# polyglot-covers: python.random.randrange python.random.randrange-step python.random.python310-randrange-float
# polyglot-covers: python.random.randint python.random.inclusive-bounds
# polyglot-covers: python.random.choice python.random.empty-choice
# polyglot-covers: python.random.choices python.random.weighted-with-replacement
# polyglot-covers: python.random.relative-weights python.random.cumulative-weights
# polyglot-covers: python.random.shuffle python.random.in-place-permutation
# polyglot-covers: python.random.sample python.random.without-replacement
# polyglot-covers: python.random.sample-counts python.random.range-sampling
# polyglot-covers: python.random.repeated-population python.random.unhashable-members




from decimal import Decimal
from fractions import Fraction
from random import Random
import pytest
import math
from random import Random, SystemRandom

def draw_signature(generator, size=6):
    """组合几类基础调用，证明整个实例状态流而非某一个方法可复现。"""

    return (
        [generator.random() for _ in range(size)],
        [generator.randrange(10_000) for _ in range(size)],
        generator.randbytes(size),
    )


@pytest.mark.parametrize("seed", [2026, 3.5, "polyglot", b"polyglot", bytearray(b"polyglot")])
def test_supported_seed_types_reproduce_the_same_sequence(seed):
    """3.10 支持 int/float/str/bytes/bytearray；相同 seed 与兼容 seeder 保证 random() 序列一致。"""

    first = Random()
    second = Random()
    first.seed(seed, version=2)
    second.seed(seed, version=2)

    assert draw_signature(first) == draw_signature(second)


def test_string_seed_versions_exist_for_backward_compatible_reproduction():
    """version=1 保留旧字符串/bytes seeder；新工作默认 version=2 使用输入的全部 bits。"""

    legacy = Random()
    current = Random()
    legacy.seed("long reproducible seed", version=1)
    current.seed("long reproducible seed", version=2)

    legacy_values = [legacy.random() for _ in range(4)]
    current_values = [current.random() for _ in range(4)]

    assert legacy_values != current_values

    replay = Random()
    replay.seed("long reproducible seed", version=1)
    assert [replay.random() for _ in range(4)] == legacy_values


def test_separate_random_instances_do_not_share_advancement_state():
    """两个同 seed 实例起点相同，但推进其中一个不会消耗另一个的序列。"""

    first = Random(42)
    second = Random(42)

    first_value = first.random()
    second_value = second.random()
    assert first_value == second_value

    first.random()
    expected_second = Random(42)
    expected_second.random()
    assert second.random() == expected_second.random()


def test_getstate_and_setstate_replay_an_exact_future_suffix():
    """state 是 opaque checkpoint；恢复后后续所有依赖同一核心生成器的方法重复相同结果。"""

    generator = Random(12345)
    generator.random()
    checkpoint = generator.getstate()

    first_suffix = draw_signature(generator)
    generator.setstate(checkpoint)
    replayed_suffix = draw_signature(generator)

    assert replayed_suffix == first_suffix


def test_random_returns_a_53_bit_style_float_in_half_open_unit_interval():
    """基础 random() 的范围是 [0.0, 1.0)，上端 1.0 永远不包含。"""

    generator = Random(7)
    values = [generator.random() for _ in range(20)]

    assert all(type(value) is float for value in values)
    assert all(0.0 <= value < 1.0 for value in values)


def test_randbytes_has_deterministic_length_but_is_not_a_security_token_api():
    """3.9+ randbytes 适合模拟/测试二进制；密码学用途应使用 secrets.token_bytes。"""

    first = Random(99)
    second = Random(99)

    assert first.randbytes(0) == b""
    assert first.randbytes(16) == second.randbytes(0) + second.randbytes(16)
    assert len(first.randbytes(7)) == 7
    assert type(first.randbytes(1)) is bytes


def test_getrandbits_handles_zero_and_arbitrarily_large_bit_counts():
    """3.9+ k=0 返回 0；大 k 直接生成 Python 大整数，为巨大 randrange 提供基础。"""

    generator = Random(101)

    assert generator.getrandbits(0) == 0

    value = generator.getrandbits(4096)
    assert value >= 0
    assert value.bit_length() <= 4096
    assert type(value) is int

    with pytest.raises(ValueError):
        generator.getrandbits(-1)


def test_randrange_selects_only_values_from_the_equivalent_range():
    """参数模式与 range 相同，step/负步长都遵守离散候选集合而不构造完整 list。"""

    generator = Random(11)
    positive_range = range(3, 40, 4)
    negative_range = range(10, -10, -3)

    positive_values = [generator.randrange(3, 40, 4) for _ in range(20)]
    negative_values = [generator.randrange(10, -10, -3) for _ in range(20)]

    assert all(value in positive_range for value in positive_values)
    assert all(value in negative_range for value in negative_values)


def test_randrange_rejects_empty_ranges_and_zero_step():
    """没有候选值时不能返回 sentinel；与 range 不同，randrange 必须从非空集合选择。"""

    generator = Random(12)

    with pytest.raises(ValueError, match="empty range"):
        generator.randrange(5, 5)
    with pytest.raises(ValueError, match="zero step"):
        generator.randrange(0, 10, 0)


def test_python_310_randrange_integral_float_conversion_is_deprecated():
    """3.10 仍把 10.0 无损转换为 10，但发 deprecation；未来代码必须传真正整数。"""

    generator = Random(13)

    with pytest.warns(DeprecationWarning):
        value = generator.randrange(10.0)
    assert value in range(10)

    with pytest.raises(ValueError):
        generator.randrange(10.5)


def test_randint_is_randrange_with_an_inclusive_upper_bound():
    """randint(a,b) 包含两端；退化为单点时可无概率地证明 b 没被当作 exclusive stop。"""

    generator = Random(14)

    assert generator.randint(5, 5) == 5
    values = [generator.randint(-2, 2) for _ in range(20)]
    assert all(-2 <= value <= 2 for value in values)


def test_choice_returns_a_member_and_empty_sequence_raises_index_error():
    """choice 需要可按 index 访问的非空 sequence；空输入没有合理随机元素。"""

    generator = Random(15)
    population = ("red", "green", "blue")

    assert all(generator.choice(population) in population for _ in range(20))
    with pytest.raises(IndexError, match="empty sequence"):
        generator.choice(())


def test_choices_returns_k_items_with_replacement_and_keeps_population_unchanged():
    """choices 的结果长度由 k 决定且允许重复；输入 sequence 不被修改。"""

    generator = Random(16)
    population = ["red", "green", "blue"]
    original = population.copy()

    selected = generator.choices(population, k=20)

    assert len(selected) == 20
    assert all(item in population for item in selected)
    assert population == original


def test_relative_and_cumulative_weights_describe_the_same_selection_model():
    """cum_weights 可预计算复用；在相同 generator state 下与对应 relative weights 等价。"""

    relative_generator = Random(17)
    cumulative_generator = Random(17)
    population = ["red", "black", "green"]

    relative = relative_generator.choices(population, weights=[18, 18, 2], k=30)
    cumulative = cumulative_generator.choices(population, cum_weights=[18, 36, 38], k=30)

    assert relative == cumulative


def test_choices_accepts_fraction_weights_but_decimal_does_not_interoperate_with_float_core():
    """weight 必须能和 random() 的 float 运算；Fraction 可以，Decimal 刻意不隐式混用。"""

    generator = Random(18)

    selected = generator.choices("AB", weights=[Fraction(1, 3), Fraction(2, 3)], k=5)
    assert len(selected) == 5

    with pytest.raises(TypeError):
        generator.choices("AB", weights=[Decimal("0.5"), Decimal("0.5")], k=1)


def test_choices_validates_weight_configuration():
    """relative/cumulative 不能同时给；长度要匹配 population，且总权重必须有限并大于零。"""

    generator = Random(19)

    with pytest.raises(TypeError):
        generator.choices("AB", weights=[1, 1], cum_weights=[1, 2], k=1)
    with pytest.raises(ValueError, match="number of weights"):
        generator.choices("AB", weights=[1], k=1)
    with pytest.raises(ValueError, match="greater than zero"):
        generator.choices("AB", weights=[0, 0], k=1)
    with pytest.raises(ValueError, match="finite"):
        generator.choices("AB", weights=[1, float("inf")], k=1)


def test_shuffle_mutates_a_list_in_place_and_same_seed_replays_permutation():
    """shuffle 返回 None；若需保留源 sequence，应先复制或使用 sample。"""

    first = list(range(10))
    second = list(range(10))
    first_generator = Random(20)
    second_generator = Random(20)

    result = first_generator.shuffle(first)
    second_generator.shuffle(second)

    assert result is None
    assert first == second
    assert sorted(first) == list(range(10))


def test_sample_is_without_replacement_and_does_not_mutate_population():
    """sample 返回 selection-order 新 list；当 population 元素唯一时结果也唯一。"""

    generator = Random(21)
    population = list(range(20))
    original = population.copy()

    selected = generator.sample(population, k=8)

    assert len(selected) == 8
    assert len(set(selected)) == 8
    assert all(item in population for item in selected)
    assert population == original


def test_sample_counts_is_equivalent_to_expanding_repeated_occurrences():
    """3.9+ counts 用紧凑方式表达票数/牌数；抽的是 occurrence，因此同值可出现多次。"""

    compact_generator = Random(22)
    expanded_generator = Random(22)

    compact = compact_generator.sample(["red", "blue"], counts=[4, 2], k=5)
    expanded = expanded_generator.sample(["red"] * 4 + ["blue"] * 2, k=5)

    assert compact == expanded
    assert compact.count("red") <= 4
    assert compact.count("blue") <= 2


def test_sample_treats_duplicate_and_unhashable_members_as_separate_occurrences():
    """population 成员无需 hashable 或唯一；without replacement 针对位置而非 value。"""

    generator = Random(23)
    repeated = ["same", "same"]
    unhashable = [{"id": 1}, {"id": 2}, {"id": 3}]

    assert generator.sample(repeated, k=2) == ["same", "same"]
    selected = generator.sample(unhashable, k=2)
    assert len(selected) == 2
    assert all(item in unhashable for item in selected)


def test_sampling_a_range_is_space_efficient_and_large_k_errors_are_explicit():
    """大整数 population 使用 range 避免建表；k 不能超过 occurrence 总数。"""

    generator = Random(24)
    selected = generator.sample(range(10_000_000), k=20)

    assert len(selected) == 20
    assert len(set(selected)) == 20
    assert all(0 <= value < 10_000_000 for value in selected)

    with pytest.raises(ValueError, match="Sample larger than population"):
        generator.sample(range(3), k=4)


# ``random`` 概率分布、生成器扩展与系统随机源。
#
# 概率分布案例只验证定义域、参数语义和可复现状态，不用少量样本频率冒充统计检验。
# 固定 seed 适合复现实验，但文档只承诺兼容 seeder 与 ``random()`` 序列的兼容性；
# 其他分布算法可能随 Python 版本改变，持久化测试数据时不应把它们当跨版本协议。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.random.uniform python.random.triangular
# polyglot-covers: python.random.betavariate python.random.expovariate
# polyglot-covers: python.random.gammavariate python.random.lognormvariate
# polyglot-covers: python.random.gauss python.random.gauss-cache python.random.normalvariate
# polyglot-covers: python.random.vonmisesvariate python.random.paretovariate
# polyglot-covers: python.random.weibullvariate python.random.distribution-domain
# polyglot-covers: python.random.subclass python.random.override-random
# polyglot-covers: python.random.subclass-seed python.random.subclass-state
# polyglot-covers: python.random.optional-getrandbits python.random.large-randrange
# polyglot-covers: python.random.SystemRandom python.random.os-entropy
# polyglot-covers: python.random.SystemRandom-seed python.random.SystemRandom-no-state
# polyglot-covers: python.random.cross-version-reproducibility python.random.security-boundary




class ReplayableRandom(Random):
    """用预设的 [0, 1) 值展示 Random 高层方法怎样委托给 ``random()``。"""

    def __init__(self, values):
        self._values = tuple(values)
        self._index = 0

    def random(self):
        value = self._values[self._index % len(self._values)]
        self._index += 1
        return value

    def seed(self, a=None, version=2):
        # 自定义生成器可以选择自己的 seed 状态模型；这里的教学模型只需回到序列起点。
        self._index = 0

    def getstate(self):
        return self._index

    def setstate(self, state):
        self._index = state


class ZeroBitsRandom(ReplayableRandom):
    """额外实现 getrandbits，记录 randrange 为大整数请求了多少位。"""

    def __init__(self):
        super().__init__([0.5])
        self.requested_bits = []

    def getrandbits(self, k):
        self.requested_bits.append(k)
        return 0


def test_uniform_uses_linear_interpolation_and_accepts_reversed_bounds():
    """uniform 本质是 a + (b-a)*random()；浮点舍入决定端点 b 是否偶尔可达。"""

    forward = ReplayableRandom([0.25])
    reversed_bounds = ReplayableRandom([0.25])

    assert forward.uniform(10.0, 14.0) == 11.0
    assert reversed_bounds.uniform(14.0, 10.0) == 13.0

    generator = Random(77)
    values = [generator.uniform(-2.0, 3.0) for _ in range(4)]
    assert all(-2.0 <= value <= 3.0 for value in values)


def test_triangular_uses_low_high_and_mode_to_shape_a_bounded_result():
    """mode 是峰值位置而非保证返回值；省略时默认为两端中点。"""

    at_mode = ReplayableRandom([0.2])
    assert at_mode.triangular(0.0, 10.0, 2.0) == pytest.approx(2.0)

    generator = Random(78)
    values = [generator.triangular(-5.0, 5.0) for _ in range(20)]
    assert all(-5.0 <= value <= 5.0 for value in values)


def test_beta_distribution_stays_in_unit_interval_and_requires_positive_shapes():
    """alpha/beta 控制 [0,1] 上的形状；它们不是区间端点，且都必须大于零。"""

    generator = Random(79)
    values = [generator.betavariate(2.0, 5.0) for _ in range(20)]

    assert all(0.0 <= value <= 1.0 for value in values)
    with pytest.raises(ValueError):
        generator.betavariate(0.0, 1.0)
    with pytest.raises(ValueError):
        generator.betavariate(1.0, -1.0)


def test_exponential_distribution_sign_follows_nonzero_lambda():
    """lambd 是 1/mean；正值产生正样本，负值产生负样本，零会导致除零。"""

    positive = ReplayableRandom([0.5]).expovariate(2.0)
    negative = ReplayableRandom([0.5]).expovariate(-2.0)

    assert positive == pytest.approx(math.log(2.0) / 2.0)
    assert negative == pytest.approx(-math.log(2.0) / 2.0)
    with pytest.raises(ZeroDivisionError):
        Random(80).expovariate(0.0)


def test_gamma_distribution_uses_positive_shape_and_scale_parameters():
    """gammavariate 的 alpha 是 shape、beta 是 scale；两者都必须为正。"""

    generator = Random(81)
    values = [generator.gammavariate(2.0, 3.0) for _ in range(20)]

    assert all(value > 0.0 for value in values)
    with pytest.raises(ValueError):
        generator.gammavariate(0.0, 1.0)
    with pytest.raises(ValueError):
        generator.gammavariate(1.0, 0.0)


def test_lognormal_distribution_is_the_exponential_of_a_normal_variate():
    """mu/sigma 描述取对数后的正态分布，所以返回值始终为正。"""

    generator = Random(82)
    values = [generator.lognormvariate(0.0, 0.5) for _ in range(20)]

    assert all(value > 0.0 for value in values)


def test_gauss_and_normalvariate_each_replay_from_the_same_seed():
    """两者都生成正态样本但算法不同；只比较各自重放，不能要求二者结果相同。"""

    first_gauss = Random(83)
    second_gauss = Random(83)
    first_normal = Random(83)
    second_normal = Random(83)

    gauss_values = [first_gauss.gauss(10.0, 2.0) for _ in range(8)]
    normal_values = [first_normal.normalvariate(10.0, 2.0) for _ in range(8)]

    assert gauss_values == [second_gauss.gauss(10.0, 2.0) for _ in range(8)]
    assert normal_values == [second_normal.normalvariate(10.0, 2.0) for _ in range(8)]
    assert gauss_values != normal_values


def test_gauss_cached_second_value_is_part_of_random_instance_state():
    """gauss 一次计算两个值并缓存一个；getstate/setstate 连同这个 cache 一起恢复。"""

    generator = Random(84)
    generator.gauss(0.0, 1.0)
    checkpoint = generator.getstate()
    cached_value = generator.gauss(0.0, 1.0)

    replay = Random()
    replay.setstate(checkpoint)
    assert replay.gauss(0.0, 1.0) == cached_value


def test_gauss_concurrency_boundary_favors_one_instance_per_worker():
    """gauss 的备用值 cache 可能让并发调用撞值；常见方案是每个 worker 独占实例。"""

    workers = [Random(seed) for seed in (850, 851, 852)]
    batches = [[worker.gauss(0.0, 1.0) for _ in range(4)] for worker in workers]

    assert len(batches) == 3
    assert all(len(batch) == 4 for batch in batches)
    assert len({tuple(batch) for batch in batches}) == 3


def test_von_mises_distribution_wraps_angles_around_a_circle():
    """返回角度位于 0 到 2π；kappa=0 表示圆上的均匀分布。"""

    generator = Random(86)
    values = [generator.vonmisesvariate(math.pi, 0.0) for _ in range(20)]

    assert all(0.0 <= value <= 2.0 * math.pi for value in values)


def test_pareto_distribution_has_unit_minimum_scale():
    """paretovariate 只接收 shape alpha，隐含 scale=1，因此正常样本不小于 1。"""

    generator = Random(87)
    values = [generator.paretovariate(3.0) for _ in range(20)]

    assert all(value >= 1.0 for value in values)


def test_weibull_distribution_uses_scale_then_shape():
    """weibullvariate(alpha, beta) 中 alpha 是 scale、beta 是 shape，顺序容易和 gamma 混淆。"""

    generator = Random(88)
    values = [generator.weibullvariate(2.0, 1.5) for _ in range(20)]

    assert all(value >= 0.0 for value in values)


def test_random_subclass_high_level_methods_delegate_to_overridden_random():
    """只要 random() 遵守 [0,1) 契约，uniform 等高层方法就能复用自定义核心生成器。"""

    generator = ReplayableRandom([0.25, 0.75])

    assert generator.uniform(0.0, 8.0) == 2.0
    assert generator.uniform(0.0, 8.0) == 6.0


def test_random_subclass_defines_its_own_seed_and_state_protocol():
    """扩展生成器应成套实现 seed/getstate/setstate，才能支持重置和可复现 checkpoint。"""

    generator = ReplayableRandom([0.1, 0.4, 0.9])
    assert generator.random() == 0.1
    checkpoint = generator.getstate()
    expected = [generator.random(), generator.random()]

    generator.setstate(checkpoint)
    assert [generator.random(), generator.random()] == expected

    generator.seed("这个简化实现忽略 seed 内容")
    assert generator.random() == 0.1


def test_optional_getrandbits_supports_uniform_selection_from_huge_integer_ranges():
    """实现 getrandbits 后，基类 randrange 可直接处理远超浮点精度的大整数且避免取模偏差。"""

    generator = ZeroBitsRandom()
    stop = 1 << 200

    assert generator.randrange(stop) == 0
    assert generator.requested_bits == [201]


def test_system_random_uses_os_entropy_for_the_random_api_surface():
    """SystemRandom 复用 random API，但每次从操作系统来源取值，适合不可预测用途。"""

    generator = SystemRandom()
    value = generator.random()
    bits = generator.getrandbits(257)
    token = generator.randbytes(16)

    assert 0.0 <= value < 1.0
    assert 0 <= bits < 1 << 257
    assert type(token) is bytes
    assert len(token) == 16


def test_system_random_seed_is_ignored_and_state_checkpointing_is_unsupported():
    """系统熵没有可重放内部状态：seed 是兼容接口的空操作，state API 明确拒绝调用。"""

    generator = SystemRandom()

    assert generator.seed(12345) is None
    with pytest.raises(NotImplementedError):
        generator.getstate()
    with pytest.raises(NotImplementedError):
        generator.setstate((3, (), None))


def test_seeded_random_and_system_random_serve_different_security_goals():
    """Random 的确定性是模拟优势也是 token 风险；安全选择要用 SystemRandom 或 secrets。"""

    predictable_first = Random(90)
    predictable_second = Random(90)
    secure_source = SystemRandom()

    assert predictable_first.randbytes(12) == predictable_second.randbytes(12)
    assert isinstance(secure_source, Random)
    with pytest.raises(NotImplementedError):
        secure_source.getstate()
