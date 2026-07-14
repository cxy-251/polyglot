"""076｜``random`` 可复现状态、整数生成与序列抽样。

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
