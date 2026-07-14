"""084｜``functools`` 函数缓存与实例缓存属性。

cache/lru_cache 以可哈希调用参数为 key，并强引用参数和返回值直到淘汰或清空；
它们适合纯函数和可复用结果，不适合时间、随机、副作用或每次都应新建的可变对象。
缓存结构在并发更新下保持一致，但两个并发 miss 仍可能重复执行底层函数。
cached_property 把首次结果写进实例 __dict__，之后普通属性读写会遮蔽 descriptor。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.functools.cache python.functools.unbounded-cache
# polyglot-covers: python.functools.lru_cache python.functools.lru-eviction
# polyglot-covers: python.functools.lru-maxsize-zero python.functools.lru-maxsize-none
# polyglot-covers: python.functools.lru-typed python.functools.lru-keyword-order
# polyglot-covers: python.functools.cache-hashable-arguments python.functools.cache-strong-references
# polyglot-covers: python.functools.cache_info python.functools.cache_parameters
# polyglot-covers: python.functools.cache_clear python.functools.cache-wrapped
# polyglot-covers: python.functools.cache-pure-function python.functools.mutable-result-trap
# polyglot-covers: python.functools.method-cache-self
# polyglot-covers: python.functools.cached_property python.functools.cached-property-dict
# polyglot-covers: python.functools.cached-property-write python.functools.cached-property-delete
# polyglot-covers: python.functools.cached-property-slots python.functools.property-cache-alternative

import gc
from functools import cache, cached_property, lru_cache
import weakref

import pytest


def test_cache_reuses_recursive_results_without_an_eviction_limit():
    """@cache 等价于 lru_cache(maxsize=None)，递归子问题只会真正计算一次。"""

    calls = []

    @cache
    def fibonacci(number):
        calls.append(number)
        if number < 2:
            return number
        return fibonacci(number - 1) + fibonacci(number - 2)

    assert fibonacci(10) == 55
    assert sorted(calls) == list(range(11))

    before = len(calls)
    assert fibonacci(8) == 21
    assert len(calls) == before
    assert fibonacci.cache_parameters() == {"maxsize": None, "typed": False}


def test_lru_cache_records_hits_misses_capacity_and_current_size():
    """cache_info 是 named tuple，可用于判断容量是否匹配真实命中模式。"""

    @lru_cache(maxsize=2)
    def square(number):
        return number * number

    assert square(2) == 4
    assert square(2) == 4
    assert square(3) == 9

    info = square.cache_info()
    assert (info.hits, info.misses, info.maxsize, info.currsize) == (1, 2, 2, 2)


def test_lru_eviction_uses_recent_access_not_insertion_order():
    """命中会把 key 提升为最近使用；容量满后淘汰最久未使用项。"""

    calls = []

    @lru_cache(maxsize=2)
    def identify(value):
        calls.append(value)
        return value

    identify("A")
    identify("B")
    identify("A")
    identify("C")
    identify("A")
    identify("B")

    assert calls == ["A", "B", "C", "B"]
    assert identify.cache_info().hits == 2
    assert identify.cache_info().misses == 4


def test_lru_maxsize_zero_tracks_calls_without_storing_results():
    """maxsize=0 可保留 wrapper/统计接口但禁用存储，每次调用都是 miss。"""

    calls = 0

    @lru_cache(maxsize=0)
    def compute(value):
        nonlocal calls
        calls += 1
        return value * 2

    assert compute(5) == 10
    assert compute(5) == 10
    assert calls == 2
    assert compute.cache_info().currsize == 0
    assert compute.cache_info().misses == 2


def test_lru_maxsize_none_disables_eviction_but_not_memoization():
    """无界缓存只做 dict lookup，适合 key 空间本身有界的纯函数；开放输入会持续增长。"""

    @lru_cache(maxsize=None)
    def identity(value):
        return value

    for value in range(20):
        identity(value)
    for value in range(20):
        identity(value)

    info = identity.cache_info()
    assert (info.hits, info.misses, info.currsize) == (20, 20, 20)


def test_typed_true_separates_equal_immediate_arguments_by_type():
    """bool/int/float 可能数值相等；typed=True 把直接参数类型纳入 cache key。"""

    calls = []

    @lru_cache(maxsize=None, typed=True)
    def describe(value):
        calls.append(type(value).__name__)
        return type(value).__name__

    assert describe(1) == "int"
    assert describe(1.0) == "float"
    assert describe(True) == "bool"
    assert describe(1) == "int"
    assert calls == ["int", "float", "bool"]


def test_keyword_order_can_create_distinct_cache_entries():
    """缓存不承诺规范化 keyword 顺序；语义等价的不同传参顺序可能分别 miss。"""

    @lru_cache(maxsize=None)
    def items(**values):
        return tuple(sorted(values.items()))

    assert items(left=1, right=2) == items(right=2, left=1)
    assert items.cache_info().misses == 2
    assert items.cache_info().hits == 0


def test_cache_arguments_must_be_hashable():
    """cache 底层使用 dict；list/dict 等可变参数不能直接作为 key，应先转 tuple 或稳定标识。"""

    @cache
    def total(values):
        return sum(values)

    with pytest.raises(TypeError, match="unhashable"):
        total([1, 2, 3])
    assert total((1, 2, 3)) == 6


def test_cache_parameters_returns_an_informational_copy():
    """修改 cache_parameters() 的新 dict 不会动态重配现有 wrapper。"""

    @lru_cache(maxsize=4, typed=True)
    def identity(value):
        return value

    parameters = identity.cache_parameters()
    parameters["maxsize"] = 999

    assert identity.cache_parameters() == {"maxsize": 4, "typed": True}


def test_cache_clear_invalidates_entries_and_resets_statistics():
    """清空不仅释放结果，还把 hits/misses/currsize 重置，适合测试隔离或数据版本切换。"""

    @lru_cache(maxsize=2)
    def identity(value):
        return value

    identity(1)
    identity(1)
    assert identity.cache_info().hits == 1

    identity.cache_clear()

    assert identity.cache_info().hits == 0
    assert identity.cache_info().misses == 0
    assert identity.cache_info().currsize == 0


def test_wrapped_attribute_bypasses_cache_for_introspection_or_recomputation():
    """直接调用 __wrapped__ 执行原函数，不查缓存，也不改变 wrapper 的 hit/miss 统计。"""

    calls = 0

    @lru_cache(maxsize=2)
    def compute(value: int) -> int:
        """返回加一后的值。"""

        nonlocal calls
        calls += 1
        return value + 1

    assert compute(4) == 5
    assert compute(4) == 5
    assert compute.__wrapped__(4) == 5

    assert calls == 2
    assert (compute.cache_info().hits, compute.cache_info().misses) == (1, 1)
    assert compute.__name__ == "compute"
    assert compute.__annotations__ == {"value": int, "return": int}


def test_cache_holds_strong_references_until_clear():
    """参数和结果不会因外部引用消失而自动释放；长生命周期服务应限制容量或主动 clear。"""

    class Payload:
        pass

    @cache
    def remember(payload):
        return payload

    payload = Payload()
    reference = weakref.ref(payload)
    remember(payload)

    del payload
    gc.collect()
    assert reference() is not None

    remember.cache_clear()
    gc.collect()
    assert reference() is None


def test_caching_a_mutable_result_reuses_the_same_mutated_object():
    """需要“每次新对象”的 factory 不应缓存；调用者修改返回值会污染所有后续命中。"""

    @cache
    def make_bucket(name):
        return [name]

    first = make_bucket("jobs")
    first.append("mutated")
    second = make_bucket("jobs")

    assert second is first
    assert second == ["jobs", "mutated"]


def test_cached_method_keys_include_self_and_separate_instances():
    """装饰实例方法时 self 是 cache key 的一部分，同参数在不同实例上分别缓存。"""

    class Multiplier:
        def __init__(self, factor):
            self.factor = factor
            self.calls = 0

        @lru_cache(maxsize=None)
        def apply(self, value):
            self.calls += 1
            return self.factor * value

    double = Multiplier(2)
    triple = Multiplier(3)

    assert double.apply(5) == 10
    assert double.apply(5) == 10
    assert triple.apply(5) == 15
    assert (double.calls, triple.calls) == (1, 1)


def test_cached_property_computes_once_then_stores_a_normal_instance_attribute():
    """首次读取调用 descriptor 并写入 __dict__；之后直接由实例 dict 命中。"""

    class Report:
        def __init__(self):
            self.calls = 0

        @cached_property
        def summary(self):
            self.calls += 1
            return {"version": self.calls}

    report = Report()
    first = report.summary
    second = report.summary

    assert first is second
    assert report.calls == 1
    assert report.__dict__["summary"] is first


def test_cached_property_allows_override_and_delete_for_recomputation():
    """普通 assignment 遮蔽 descriptor；del 删除缓存/覆盖值，下一次读取重新执行方法。"""

    class Sequence:
        def __init__(self, values):
            self.values = values
            self.calls = 0

        @cached_property
        def total(self):
            self.calls += 1
            return sum(self.values)

    sequence = Sequence([1, 2])
    assert sequence.total == 3

    sequence.total = 99
    assert sequence.total == 99
    assert sequence.calls == 1

    del sequence.total
    sequence.values.append(3)
    assert sequence.total == 6
    assert sequence.calls == 2


def test_cached_property_without_a_mutable_instance_dict_fails():
    """只定义 __slots__ 且不包含 __dict__ 的实例没有位置保存同名缓存属性。"""

    class Slotted:
        __slots__ = ("value",)

        def __init__(self, value):
            self.value = value

        @cached_property
        def doubled(self):
            return self.value * 2

    with pytest.raises(TypeError, match="__dict__"):
        Slotted(5).doubled


def test_property_over_cache_is_an_alternative_for_hashable_slotted_instances():
    """property 不写实例 dict，内层 cache 以 self 为 key；代价是 cache 会强引用实例。"""

    class Slotted:
        __slots__ = ("value",)

        def __init__(self, value):
            self.value = value

        @property
        @cache
        def doubled(self):
            return self.value * 2

    instance = Slotted(5)

    assert instance.doubled == 10
    assert instance.doubled == 10
    assert Slotted.doubled.fget.cache_info().hits == 1
