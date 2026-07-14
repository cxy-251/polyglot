"""050｜``collections.abc`` 接口识别、基础协议与运行时能力边界。

ABC 判定可以来自真实继承、``register()`` 虚拟注册，或简单接口的
``__subclasshook__`` 结构扫描。这些判定回答“类型是否声明/看起来提供接口”，
并不会调用方法验证行为。真正需要使用某项能力时，
仍应执行相应操作并处理失败。

本文件先处理简单同步接口；复杂容器 mixin 与异步 ABC 留给后续测试套。当前文件
尚未经过 pytest 验证。
"""

# polyglot-covers: python.collections.abc python.abc.direct-inheritance
# polyglot-covers: python.abc.abstract-instantiation python.abc.concrete-implementation
# polyglot-covers: python.abc.virtual-registration python.abc.registration-cache-token
# polyglot-covers: python.abc.structural-subclasshook python.abc.method-none
# polyglot-covers: python.abc.Container python.abc.Collection
# polyglot-covers: python.abc.Sized python.abc.Callable
# polyglot-covers: python.abc.Iterable python.iterable.getitem-fallback
# polyglot-covers: python.abc.Iterator python.iterator.self-iter
# polyglot-covers: python.abc.Reversible python.reversed.sequence-fallback
# polyglot-covers: python.abc.Hashable python.hashable.runtime-failure
# polyglot-covers: python.abc.complex-interface-boundary python.abc.builtin-relations
# polyglot-covers: python.abc.generic-alias python.abc.parameterized-isinstance

from abc import get_cache_token
from collections.abc import Callable
from collections.abc import Collection
from collections.abc import Container
from collections.abc import Hashable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Reversible
from collections.abc import Sequence
from collections.abc import Sized
from types import GenericAlias

import pytest


def test_direct_abc_subclass_cannot_instantiate_with_abstract_methods_left():
    """class body 可以建立未完成类型；真正实例化时 ABCMeta 才拒绝遗漏的 __len__。"""

    class IncompleteBatch(Sized):
        pass

    assert issubclass(IncompleteBatch, Sized)
    assert "__len__" in IncompleteBatch.__abstractmethods__

    with pytest.raises(TypeError, match=r"abstract method __len__"):
        IncompleteBatch()


def test_direct_abc_subclass_becomes_concrete_after_required_method_is_defined():
    """补齐 abstract method 后既获得名义继承关系，也可直接交给对应内置操作。"""

    class Batch(Sized):
        def __init__(self, records):
            self.records = list(records)

        def __len__(self):
            return len(self.records)

    batch = Batch(["a", "b", "c"])

    assert Batch.__abstractmethods__ == frozenset()
    assert issubclass(Batch, Sized)
    assert isinstance(batch, Sized)
    assert len(batch) == 3


def test_virtual_registration_changes_checks_not_mro_or_available_mixins():
    """register 是声明，不是适配器；它不插入 Sequence，也不会复制 index/count。"""

    class ExternalRows:
        def __init__(self, rows):
            self.rows = list(rows)

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, index):
            return self.rows[index]

    before = get_cache_token()
    returned = Sequence.register(ExternalRows)
    after = get_cache_token()
    rows = ExternalRows(["first", "second"])

    # register 返回原 class，因此同一个调用也能直接当 class decorator 使用。
    assert returned is ExternalRows
    assert before != after
    assert issubclass(ExternalRows, Sequence)
    assert isinstance(rows, Sequence)
    assert isinstance(rows, Collection)
    assert Sequence not in ExternalRows.__mro__
    assert "index" not in dir(rows)
    assert "count" not in dir(rows)

    # __getitem__ sequence fallback 确实使这个特定对象可迭代，但不是注册补出来的。
    assert list(rows) == ["first", "second"]


def test_virtual_registration_applies_to_descendants_without_validating_semantics():
    """注册类的子类也通过检查；方法签名和返回语义仍完全由实现者负责。"""

    class DeclaredSized:
        def __len__(self):
            return "not-an-integer"

    Sized.register(DeclaredSized)

    class Child(DeclaredSized):
        pass

    value = Child()

    assert issubclass(Child, Sized)
    assert isinstance(value, Sized)
    with pytest.raises(TypeError, match="integer"):
        len(value)


def test_simple_abcs_are_structurally_recognized_from_methods_in_the_mro():
    """简单 ABC 只扫描必需 method 是否存在且不是 None，无须显式继承或注册。"""

    class Dashboard:
        def __init__(self, widgets):
            self.widgets = tuple(widgets)

        def __len__(self):
            return len(self.widgets)

        def __iter__(self):
            return iter(self.widgets)

        def __contains__(self, widget):
            return widget in self.widgets

    dashboard = Dashboard(["latency", "errors"])

    assert Dashboard.__mro__ == (Dashboard, object)
    assert isinstance(dashboard, Sized)
    assert isinstance(dashboard, Iterable)
    assert isinstance(dashboard, Container)
    assert isinstance(dashboard, Collection)
    assert len(dashboard) == 2
    assert list(dashboard) == ["latency", "errors"]
    assert "errors" in dashboard


def test_callable_abc_recognizes_call_method_but_does_not_call_it_during_check():
    """Callable 判定是结构扫描；副作用或异常只在真正 value(...) 时出现。"""

    class Command:
        def __init__(self):
            self.calls = []

        def __call__(self, name):
            self.calls.append(name)
            return name.upper()

    command = Command()

    assert isinstance(command, Callable)
    assert command.calls == []
    assert command("build") == "BUILD"
    assert command.calls == ["build"]


def test_collection_requires_contains_iter_and_len_together():
    """只满足部分 one-trick ABC 不足以结构化成为 Collection。"""

    class IterableAndSized:
        def __iter__(self):
            return iter((1, 2))

        def __len__(self):
            return 2

    value = IterableAndSized()

    assert isinstance(value, Iterable)
    assert isinstance(value, Sized)
    assert not isinstance(value, Container)
    assert not isinstance(value, Collection)


def test_setting_iter_to_none_disables_structural_match_and_getitem_fallback():
    """显式 ``__iter__ = None`` 表示“不支持”；iter() 不再退回旧式 __getitem__。"""

    class LegacyBase:
        def __getitem__(self, index):
            values = ("a", "b")
            return values[index]

    class IterationDisabled(LegacyBase):
        __iter__ = None

    disabled = IterationDisabled()

    assert not isinstance(disabled, Iterable)
    with pytest.raises(TypeError, match="not iterable"):
        iter(disabled)


def test_getitem_sequence_fallback_can_iterate_without_iterable_abc_match():
    """Iterable.__subclasshook__ 只寻找 __iter__；iter() 还支持历史 sequence fallback。"""

    class LegacyPages:
        def __init__(self, pages):
            self.pages = tuple(pages)

        def __getitem__(self, index):
            return self.pages[index]

    pages = LegacyPages(["intro", "protocols", "stdlib"])

    assert not isinstance(pages, Iterable)
    iterator = iter(pages)
    assert list(iterator) == ["intro", "protocols", "stdlib"]
    assert list(pages) == ["intro", "protocols", "stdlib"]


def test_iter_operation_is_a_stronger_capability_probe_than_iterable_abc():
    """方法名存在就能通过 ABC；返回 list 而非 iterator 的坏语义要到 iter() 才暴露。"""

    class BrokenIterable:
        def __iter__(self):
            return ["this", "is", "not", "an", "iterator"]

    broken = BrokenIterable()

    assert isinstance(broken, Iterable)
    with pytest.raises(TypeError, match="non-iterator"):
        iter(broken)


def test_iterator_direct_subclass_gets_self_returning_iter_mixin():
    """Iterator 已实现 __iter__；自定义 iterator 通常只需提供有状态的 __next__。"""

    class Countdown(Iterator):
        def __init__(self, start):
            self.current = start

        def __next__(self):
            if self.current <= 0:
                raise StopIteration
            value = self.current
            self.current -= 1
            return value

    countdown = Countdown(3)

    assert isinstance(countdown, Iterator)
    assert isinstance(countdown, Iterable)
    assert iter(countdown) is countdown
    assert next(countdown) == 3
    assert list(countdown) == [2, 1]

    # iterator 一旦耗尽，后续 next() 也必须持续 StopIteration。
    with pytest.raises(StopIteration):
        next(countdown)
    with pytest.raises(StopIteration):
        next(countdown)


def test_reversible_structural_match_requires_iter_and_reversed_methods():
    """Reversible 结构检查同时寻找 __iter__ 和 __reversed__，后者可提供更高效路径。"""

    class Route:
        def __init__(self, stops):
            self.stops = tuple(stops)
            self.reverse_calls = 0

        def __iter__(self):
            return iter(self.stops)

        def __reversed__(self):
            self.reverse_calls += 1
            return iter(self.stops[::-1])

    route = Route(["A", "B", "C"])

    assert isinstance(route, Iterable)
    assert isinstance(route, Reversible)
    assert list(reversed(route)) == ["C", "B", "A"]
    assert route.reverse_calls == 1


def test_reversed_sequence_fallback_can_work_without_reversible_abc_match():
    """reversed() 可用 __len__ + __getitem__ 倒序索引；成功不等于 Reversible instance。"""

    class IndexedRoute:
        def __init__(self, stops):
            self.stops = tuple(stops)

        def __len__(self):
            return len(self.stops)

        def __getitem__(self, index):
            return self.stops[index]

    route = IndexedRoute(["A", "B", "C"])

    assert isinstance(route, Sized)
    assert not isinstance(route, Reversible)
    assert list(reversed(route)) == ["C", "B", "A"]


def test_hashable_detects_hash_none_but_not_a_hash_method_that_raises():
    """定义 __eq__ 会令 __hash__ 成为 None；若 method 存在但运行失败，ABC 无法预知。"""

    class EqualityOnly:
        def __eq__(self, other):
            return isinstance(other, EqualityOnly)

    class BrokenHash:
        def __hash__(self):
            raise RuntimeError("hash backend unavailable")

    equality_only = EqualityOnly()
    broken = BrokenHash()

    assert EqualityOnly.__hash__ is None
    assert not isinstance(equality_only, Hashable)
    with pytest.raises(TypeError, match="unhashable"):
        hash(equality_only)

    assert isinstance(broken, Hashable)
    with pytest.raises(RuntimeError, match="backend"):
        hash(broken)


def test_complex_container_interfaces_are_not_inferred_from_ambiguous_methods():
    """getitem/iter/len 无法说明 key 类型，故不会自动判成 Sequence/Mapping。"""

    class AmbiguousContainer:
        def __init__(self):
            self.data = {0: "zero", "name": "atlas"}

        def __getitem__(self, key):
            return self.data[key]

        def __iter__(self):
            return iter(self.data)

        def __len__(self):
            return len(self.data)

        def __contains__(self, key):
            return key in self.data

    value = AmbiguousContainer()

    assert isinstance(value, Collection)
    assert not isinstance(value, Sequence)
    assert not isinstance(value, Mapping)
    assert value[0] == "zero"
    assert value["name"] == "atlas"


def test_parameterized_abcs_are_generic_aliases_not_isinstance_targets():
    """Iterable[int] 保存注解元数据；运行时检查必须使用未参数化的 Iterable。"""

    alias = Iterable[int]
    value = [1, 2, 3]

    assert isinstance(alias, GenericAlias)
    assert alias.__origin__ is Iterable
    assert alias.__args__ == (int,)
    assert isinstance(value, Iterable)

    with pytest.raises(TypeError, match="parameterized generic"):
        isinstance(value, alias)


def test_common_builtin_types_have_distinct_abc_relationships():
    """内置容器的 ABC 关系描述接口族，不应把所有 Collection 都当 Sequence。"""

    assert isinstance([1, 2], Sequence)
    assert isinstance([1, 2], Collection)
    assert isinstance([1, 2], Reversible)

    assert isinstance({"name": "Ada"}, Mapping)
    assert isinstance({"name": "Ada"}, Collection)
    assert not isinstance({"name": "Ada"}, Sequence)

    assert isinstance({1, 2}, Collection)
    assert isinstance({1, 2}, Container)
    assert not isinstance({1, 2}, Sequence)
    assert not isinstance({1, 2}, Mapping)

    assert isinstance(iter([1, 2]), Iterator)
    assert isinstance(lambda value: value, Callable)
