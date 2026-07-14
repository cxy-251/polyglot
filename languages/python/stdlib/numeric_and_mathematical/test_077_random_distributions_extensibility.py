"""077｜``random`` 概率分布、生成器扩展与系统随机源。

概率分布案例只验证定义域、参数语义和可复现状态，不用少量样本频率冒充统计检验。
固定 seed 适合复现实验，但文档只承诺兼容 seeder 与 ``random()`` 序列的兼容性；
其他分布算法可能随 Python 版本改变，持久化测试数据时不应把它们当跨版本协议。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import math
from random import Random, SystemRandom

import pytest


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
