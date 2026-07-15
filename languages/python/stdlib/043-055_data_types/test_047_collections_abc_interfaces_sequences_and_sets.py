"""047｜``collections.abc`` 接口识别、基础协议与运行时能力边界。

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
from collections.abc import ByteString
from collections.abc import MutableSequence
from collections.abc import MutableSet
from collections.abc import Set

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


# ``Sequence``、``MutableSequence`` 与 ``ByteString`` mixin 示例。
#
# 真正继承 sequence ABC 时，少量 primitive method 会换来一组可运行的默认算法。
# 这些算法通过 ``self[...]`` 等公开协议回调具体实现。
# 它们不会替实现者决定负索引、切片、元素约束或存储复杂度。
#
# 辅助类型中的调用日志只用于讲清分派路径，不是内部调用次数的通用承诺。
# 当前文件尚未经过 pytest 验证。

# polyglot-covers: python.collections.abc.Sequence python.sequence.abstract-primitives
# polyglot-covers: python.sequence.iter-mixin python.sequence.contains-mixin
# polyglot-covers: python.sequence.reversed-mixin python.sequence.index-mixin
# polyglot-covers: python.sequence.count-mixin python.sequence.identity-before-equality
# polyglot-covers: python.sequence.index-error-termination python.sequence.slice-responsibility
# polyglot-covers: python.sequence.negative-index-responsibility python.sequence.mixin-complexity
# polyglot-covers: python.collections.abc.MutableSequence python.mutable-sequence.primitives
# polyglot-covers: python.mutable-sequence.append-extend python.mutable-sequence.iadd
# polyglot-covers: python.mutable-sequence.pop-remove python.mutable-sequence.reverse
# polyglot-covers: python.mutable-sequence.slice-mutation python.mutable-sequence.insert-normalization
# polyglot-covers: python.mutable-sequence.failure-atomicity python.mutable-sequence.clear
# polyglot-covers: python.collections.abc.ByteString python.bytes.integer-elements




class AtlasSequence(Sequence):
    """以 tuple 存储的正确只读示例；getitem 日志暴露默认 mixin 的回调。"""

    def __init__(self, values):
        self.values = tuple(values)
        self.getitem_calls = []

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        self.getitem_calls.append(index)
        # 直接委托 tuple，因此负索引、slice 和越界 IndexError 都有明确语义。
        return self.values[index]


class EditableSequence(MutableSequence):
    """用 list 实现五个 mutable primitive，并记录 mixin 如何回调它们。"""

    def __init__(self, values=()):
        self.storage = list(values)
        self.calls = []

    def __len__(self):
        return len(self.storage)

    def __getitem__(self, index):
        self.calls.append(("get", index))
        return self.storage[index]

    def __setitem__(self, index, value):
        self.calls.append(("set", index, value))
        self.storage[index] = value

    def __delitem__(self, index):
        self.calls.append(("del", index))
        del self.storage[index]

    def insert(self, index, value):
        self.calls.append(("insert", index, value))
        self.storage.insert(index, value)


def test_sequence_requires_getitem_and_len_before_instantiation():
    """Sequence 是名义 ABC；仅写 class 声明不会自动提供两个核心 primitive。"""

    class MissingPrimitives(Sequence):
        pass

    assert MissingPrimitives.__abstractmethods__ == {
        "__getitem__",
        "__len__",
    }
    with pytest.raises(TypeError, match="abstract method"):
        MissingPrimitives()


def test_sequence_primitives_unlock_iteration_membership_and_reverse_mixins():
    """只实现 getitem/len 后，ABC 的默认算法仍通过公开 self[index] 工作。"""

    sequence = AtlasSequence(["language", "builtins", "stdlib"])

    assert isinstance(sequence, Sequence)
    assert len(sequence) == 3
    assert list(sequence) == ["language", "builtins", "stdlib"]
    assert "builtins" in sequence
    assert "missing" not in sequence
    assert list(reversed(sequence)) == ["stdlib", "builtins", "language"]


def test_sequence_iteration_stops_only_when_getitem_raises_index_error():
    """默认 __iter__ 不读取 len；越界返回 sentinel 会让它继续产生值而不是结束。"""

    class SentinelEndedSequence(Sequence):
        def __len__(self):
            return 1

        def __getitem__(self, index):
            if index == 0:
                return "only"
            return None

    iterator = iter(SentinelEndedSequence())

    # 不调用 list(iterator)，否则这个故意错误的实现永远不会停止。
    assert [next(iterator) for _ in range(4)] == ["only", None, None, None]


def test_sequence_does_not_supply_negative_index_or_slice_semantics():
    """ABC 只调用 __getitem__；一个故意受限的 primitive 不会被 mixin 神奇修复。"""

    class ForwardOnlySequence(Sequence):
        def __init__(self, values):
            self.values = tuple(values)

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise TypeError("slicing is not implemented")
            if index < 0:
                raise IndexError("negative indexes are not implemented")
            return self.values[index]

    sequence = ForwardOnlySequence(["a", "b", "c"])

    assert list(sequence) == ["a", "b", "c"]
    with pytest.raises(IndexError, match="negative"):
        sequence[-1]
    with pytest.raises(TypeError, match="slicing"):
        sequence[1:]


def test_concrete_getitem_can_choose_slice_result_type_explicitly():
    """AtlasSequence 委托 tuple，所以 slice 返回 tuple；Sequence 不要求保留自定义 class。"""

    sequence = AtlasSequence(["a", "b", "c", "d"])
    sliced = sequence[1:3]

    assert type(sliced) is tuple
    assert sliced == ("b", "c")
    assert sequence[-1] == "d"


def test_sequence_index_and_count_support_normal_search_workflows():
    """index 处理 start/stop 及负边界；count 遍历所有值并返回出现次数。"""

    sequence = AtlasSequence(["a", "b", "a", "c"])

    assert sequence.index("a") == 0
    assert sequence.index("a", 1) == 2
    assert sequence.index("a", -3) == 2
    assert sequence.index("a", 0, -1) == 0
    assert sequence.count("a") == 2
    assert sequence.count("missing") == 0

    with pytest.raises(ValueError):
        sequence.index("c", 0, -1)
    with pytest.raises(ValueError):
        sequence.index("missing")


def test_sequence_mixins_check_identity_before_calling_equality():
    """contains/index/count 使用 ``is`` 短路，不必对同一对象调用 __eq__。"""

    class IdentityOnly:
        def __eq__(self, other):
            raise AssertionError("equality should not run for identical object")

    marker = IdentityOnly()
    sequence = AtlasSequence([marker])

    assert marker in sequence
    assert sequence.index(marker) == 0
    assert sequence.count(marker) == 1


def test_sequence_mixins_dispatch_through_getitem_with_distinct_patterns():
    """iteration 递增到失败；contains 提前结束；reversed 生成倒序索引。"""

    sequence = AtlasSequence(["a", "b", "c"])

    assert list(sequence) == ["a", "b", "c"]
    assert sequence.getitem_calls == [0, 1, 2, 3]

    sequence.getitem_calls.clear()
    assert "b" in sequence
    assert sequence.getitem_calls == [0, 1]

    sequence.getitem_calls.clear()
    assert list(reversed(sequence)) == ["c", "b", "a"]
    assert sequence.getitem_calls == [2, 1, 0]


def test_linear_getitem_makes_default_iteration_quadratic_in_traversal_work():
    """默认 mixin 假定随机访问合算；线性 getitem 的累计 traversal steps 呈平方增长。"""

    class LinearAccessSequence(Sequence):
        def __init__(self, values):
            self.values = tuple(values)
            self.traversal_steps = 0

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            if index < 0:
                index += len(self)
            if not 0 <= index < len(self):
                raise IndexError(index)

            # 模拟从链表头走到 index；底层 tuple 只用来保持示例简洁、结果稳定。
            self.traversal_steps += index + 1
            return self.values[index]

    sequence = LinearAccessSequence(range(5))

    assert list(sequence) == [0, 1, 2, 3, 4]
    assert sequence.traversal_steps == 1 + 2 + 3 + 4 + 5


def test_overriding_iter_avoids_linear_random_access_for_common_traversal():
    """iteration/count 可提供直接 iterator；index 仍沿用 getitem。"""

    class FastIterationSequence(Sequence):
        def __init__(self, values):
            self.values = tuple(values)
            self.getitem_steps = 0

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            if not 0 <= index < len(self):
                raise IndexError(index)
            self.getitem_steps += index + 1
            return self.values[index]

        def __iter__(self):
            return iter(self.values)

    sequence = FastIterationSequence(range(5))

    assert list(sequence) == [0, 1, 2, 3, 4]
    assert sequence.count(4) == 1
    assert sequence.getitem_steps == 0

    assert sequence.index(4) == 4
    assert sequence.getitem_steps == 1 + 2 + 3 + 4 + 5


def test_duck_primitives_do_not_structurally_create_a_sequence():
    """Sequence 是复杂接口；未继承/注册的 len+getitem 对象虽可迭代，却不通过 ABC。"""

    class DuckSequence:
        def __len__(self):
            return 2

        def __getitem__(self, index):
            return ("a", "b")[index]

    duck = DuckSequence()

    assert list(duck) == ["a", "b"]
    assert not isinstance(duck, Sequence)
    assert not isinstance(duck, ByteString)


def test_mutable_sequence_requires_three_additional_mutation_primitives():
    """只有只读 primitives 时，set/del/insert 仍保持 abstract，类型不能实例化。"""

    class ReadOnlyImplementation(MutableSequence):
        def __len__(self):
            return 0

        def __getitem__(self, index):
            raise IndexError(index)

    assert ReadOnlyImplementation.__abstractmethods__ == {
        "__delitem__",
        "__setitem__",
        "insert",
    }
    with pytest.raises(TypeError, match="abstract method"):
        ReadOnlyImplementation()


def test_append_extend_and_iadd_route_new_values_through_insert():
    """默认 append 使用 insert(len)，extend 重复 append，+= 调用 extend 并返回 self。"""

    sequence = EditableSequence(["a"])

    assert sequence.append("b") is None
    assert sequence.calls == [("insert", 1, "b")]

    sequence.calls.clear()
    assert sequence.extend(["c", "d"]) is None
    assert sequence.calls == [
        ("insert", 2, "c"),
        ("insert", 3, "d"),
    ]

    sequence.calls.clear()
    identity = id(sequence)
    sequence += ["e", "f"]
    assert id(sequence) == identity
    assert sequence.calls == [
        ("insert", 4, "e"),
        ("insert", 5, "f"),
    ]
    assert sequence.storage == ["a", "b", "c", "d", "e", "f"]


def test_extend_self_snapshots_values_before_mutating():
    """extend(self) 先用 list() 固化原值，避免边迭代边追加导致无限增长。"""

    sequence = EditableSequence(["a", "b"])
    sequence.extend(sequence)

    assert sequence.storage == ["a", "b", "a", "b"]
    assert [call for call in sequence.calls if call[0] == "insert"] == [
        ("insert", 2, "a"),
        ("insert", 3, "b"),
    ]


def test_pop_and_remove_compose_getitem_index_and_delitem():
    """pop 先读取再删除同一位置；remove 用 Sequence.index 找首个相等值后删除。"""

    sequence = EditableSequence(["a", "b", "a"])

    assert sequence.pop() == "a"
    assert sequence.calls == [("get", -1), ("del", -1)]
    assert sequence.storage == ["a", "b"]

    sequence.calls.clear()
    assert sequence.remove("b") is None
    assert sequence.calls == [
        ("get", 0),
        ("get", 1),
        ("del", 1),
    ]
    assert sequence.storage == ["a"]


def test_reverse_uses_paired_get_and_set_primitives_in_place():
    """默认 reverse 交换两端元素并返回 None，无需额外 primitive。"""

    sequence = EditableSequence(["a", "b", "c", "d"])

    identity = id(sequence)
    assert sequence.reverse() is None

    assert id(sequence) == identity
    assert sequence.storage == ["d", "c", "b", "a"]
    assert sequence.calls == [
        ("get", 3),
        ("get", 0),
        ("set", 0, "d"),
        ("set", 3, "a"),
        ("get", 2),
        ("get", 1),
        ("set", 1, "c"),
        ("set", 2, "b"),
    ]


def test_slice_assignment_and_deletion_are_concrete_primitive_responsibilities():
    """语法把 slice 交给 primitive；本示例委托 list 获得完整切片 mutation。"""

    sequence = EditableSequence([0, 1, 2, 3, 4])

    sequence[1:3] = [10, 20, 30]
    assert sequence.calls == [("set", slice(1, 3), [10, 20, 30])]
    assert sequence.storage == [0, 10, 20, 30, 3, 4]

    sequence.calls.clear()
    del sequence[::2]
    assert sequence.calls == [("del", slice(None, None, 2))]
    assert sequence.storage == [10, 30, 4]


def test_concrete_insert_decides_negative_and_oversized_index_normalization():
    """MutableSequence 只调用 insert；这里因委托 list，极小位置归零、极大位置归尾。"""

    sequence = EditableSequence(["middle"])

    assert sequence.insert(-100, "start") is None
    assert sequence.insert(100, "end") is None
    assert sequence.storage == ["start", "middle", "end"]
    assert sequence.calls == [
        ("insert", -100, "start"),
        ("insert", 100, "end"),
    ]


def test_failed_pop_and_remove_do_not_mutate_the_sequence():
    """读取/搜索先失败时 del hook 不会执行，原 storage 保持不变。"""

    sequence = EditableSequence(["a", "b"])

    with pytest.raises(IndexError):
        sequence.pop(99)
    assert sequence.storage == ["a", "b"]
    assert sequence.calls == [("get", 99)]

    sequence.calls.clear()
    with pytest.raises(ValueError):
        sequence.remove("missing")
    assert sequence.storage == ["a", "b"]
    assert all(call[0] == "get" for call in sequence.calls)


def test_mutable_sequence_clear_repeatedly_pops_until_empty_and_returns_none():
    """默认 clear 捕获空容器的 IndexError；它不要求额外 clear primitive。"""

    sequence = EditableSequence(["a", "b", "c"])

    assert sequence.clear() is None
    assert sequence.storage == []
    # 最后一次 get(-1) 在空 list 上失败，随后 clear 正常结束。
    assert sequence.calls[-1] == ("get", -1)
    assert sum(call[0] == "del" for call in sequence.calls) == 3


def test_mutable_sequence_mixin_does_not_enforce_element_domain_rules():
    """ABC 只组合协议；若容器要求同质元素，必须在 insert/set primitive 自行校验。"""

    sequence = EditableSequence([1, 2])
    sequence.append("not-an-integer")
    sequence[0] = None

    assert sequence.storage == [None, 2, "not-an-integer"]


def test_bytes_and_bytearray_are_registered_byte_strings_with_integer_items():
    """ByteString 表示 byte sequence；单元素是 0..255 的 int，不是长度一的 bytes。"""

    immutable = b"ABC"
    mutable = bytearray(b"ABC")

    assert isinstance(immutable, ByteString)
    assert isinstance(immutable, Sequence)
    assert isinstance(mutable, ByteString)
    assert isinstance(mutable, MutableSequence)
    assert list(immutable) == [65, 66, 67]
    assert immutable[0] == 65
    assert mutable[1] == 66


def test_memoryview_is_sequence_but_not_registered_as_byte_string():
    """3.10 将 memoryview 注册为 Sequence；ByteString 只注册 bytes 与 bytearray。"""

    view = memoryview(b"ABC")

    assert isinstance(view, Sequence)
    assert not isinstance(view, ByteString)
    assert list(view) == [65, 66, 67]


def test_direct_byte_string_subclass_still_controls_its_element_semantics():
    """ByteString 本身不验证元素；直接继承只获得 Sequence 合同与 mixin。"""

    class MisnamedByteString(ByteString):
        def __init__(self, values):
            self.values = tuple(values)

        def __len__(self):
            return len(self.values)

        def __getitem__(self, index):
            return self.values[index]

    value = MisnamedByteString(["not", "bytes"])

    assert isinstance(value, ByteString)
    assert list(value) == ["not", "bytes"]


# ``Set`` 与 ``MutableSet`` 的比较、代数运算和 mutation mixin。
#
# ABC 只规定有限集合接口及算法关系，不要求 hash-table 存储。本文件使用 list-backed
# 实现来容纳不可哈希元素，并保留首次出现顺序以便断言稳定。
# 这个顺序不是 Set 合同。
#
# 结果类型由 ``_from_iterable()`` 决定，可变算法通过 ``add()`` / ``discard()`` 回调
# 具体实现。当前文件尚未经过 pytest 验证。

# polyglot-covers: python.collections.abc.Set python.set-abc.abstract-primitives
# polyglot-covers: python.set-abc.comparisons python.set-abc.algebra
# polyglot-covers: python.set-abc.reflected-operators python.set-abc.isdisjoint
# polyglot-covers: python.set-abc.unhashable-elements python.set-abc.result-type
# polyglot-covers: python.set-abc._from_iterable python.set-abc.constructor-contract
# polyglot-covers: python.set-abc._hash python.set-abc.immutable-hash
# polyglot-covers: python.collections.abc.MutableSet python.mutable-set.primitives
# polyglot-covers: python.mutable-set.discard-remove python.mutable-set.pop-clear
# polyglot-covers: python.mutable-set.ior python.mutable-set.iand
# polyglot-covers: python.mutable-set.ixor python.mutable-set.isub
# polyglot-covers: python.mutable-set.self-alias python.mutable-set.identity
# polyglot-covers: python.mutable-set.domain-invariant python.mutable-set.primitive-dispatch




def _contains_equal(values, target):
    """使用 identity-first equality，避免要求元素实现 hash。"""

    return any(value is target or value == target for value in values)


class ListSet(Set):
    """最小只读 set；list 存储使 list/dict 等不可哈希元素也能参与。"""

    def __init__(self, values=()):
        self.elements = []
        for value in values:
            if not _contains_equal(self.elements, value):
                self.elements.append(value)

    def __contains__(self, value):
        return _contains_equal(self.elements, value)

    def __iter__(self):
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)


class TrackedMutableSet(MutableSet):
    """可变 list-backed set；日志只记录 add/discard primitive 调用。"""

    def __init__(self, values=()):
        self.elements = []
        self.calls = []
        self.iter_calls = 0
        for value in values:
            self.add(value)
        self.calls.clear()

    def __contains__(self, value):
        return _contains_equal(self.elements, value)

    def __iter__(self):
        self.iter_calls += 1
        return iter(self.elements)

    def __len__(self):
        return len(self.elements)

    def add(self, value):
        self.calls.append(("add", value))
        if value not in self:
            self.elements.append(value)

    def discard(self, value):
        self.calls.append(("discard", value))
        for index, current in enumerate(self.elements):
            if current is value or current == value:
                del self.elements[index]
                break


def test_set_requires_contains_iter_and_len_before_instantiation():
    """Set 的三个 primitive 对应 membership、遍历和有限大小；遗漏时保持 abstract。"""

    class MissingPrimitives(Set):
        pass

    assert MissingPrimitives.__abstractmethods__ == {
        "__contains__",
        "__iter__",
        "__len__",
    }
    with pytest.raises(TypeError, match="abstract method"):
        MissingPrimitives()


def test_list_backed_set_deduplicates_unhashable_elements_by_equality():
    """Set 接口不要求元素可哈希；这里用线性 equality lookup 保存 list 和 dict。"""

    first_list = [1, 2]
    equal_list = [1, 2]
    first_dict = {"name": "Ada"}
    values = ListSet([first_list, equal_list, first_dict, {"name": "Ada"}])

    assert len(values) == 2
    assert list(values) == [[1, 2], {"name": "Ada"}]
    assert [1, 2] in values
    assert {"name": "Ada"} in values
    assert values.elements[0] is first_list
    assert values.elements[1] is first_dict


def test_set_comparisons_follow_subset_and_superset_semantics():
    """元素 iteration order 不参与 equality；严格关系还要求大小真正不同。"""

    small = ListSet(["a"])
    left = ListSet(["a", "b"])
    same = ListSet(["b", "a"])
    large = ListSet(["a", "b", "c"])

    assert left == same
    assert left != small
    assert small < left
    assert small <= left
    assert left <= same
    assert not left < same
    assert large > left
    assert large >= left
    assert left >= small


def test_set_comparisons_require_another_set_not_just_any_iterable():
    """代数 operator 接受 iterable，但 subset ordering 只对 Set 定义。"""

    values = ListSet(["a", "b"])

    assert values != ["a", "b"]
    with pytest.raises(TypeError):
        values <= ["a", "b"]
    with pytest.raises(TypeError):
        values > ("a",)


def test_set_algebra_accepts_general_iterables_and_preserves_concrete_class():
    """默认 _from_iterable 调用 type(iterable)，所以结果继续是 ListSet。"""

    left = ListSet(["a", "b"])

    intersection = left & ["b", "b", "c"]
    union = left | (value for value in ["b", "c"])
    difference = left - ["b"]
    symmetric = left ^ ["b", "c"]

    for result in (intersection, union, difference, symmetric):
        assert isinstance(result, ListSet)

    assert list(intersection) == ["b"]
    assert list(union) == ["a", "b", "c"]
    assert list(difference) == ["a"]
    assert list(symmetric) == ["a", "c"]


def test_reflected_set_operators_handle_an_iterable_on_the_left():
    """没有相应 operator 的 list 会退回 ListSet 的 __rand__ / __rsub__。"""

    right = ListSet(["b", "c"])

    intersection = ["a", "b"] & right
    difference = ["a", "b"] - right

    assert isinstance(intersection, ListSet)
    assert list(intersection) == ["b"]
    assert isinstance(difference, ListSet)
    assert list(difference) == ["a"]


def test_isdisjoint_short_circuits_after_the_first_shared_value():
    """发现交集后不会继续消费输入 iterable，适合流式或昂贵来源。"""

    consumed = []

    def candidates():
        for value in ["x", "b", "never-consumed"]:
            consumed.append(value)
            yield value

    values = ListSet(["a", "b"])

    assert values.isdisjoint(candidates()) is False
    assert consumed == ["x", "b"]
    assert values.isdisjoint(["x", "y"]) is True


def test_default_from_iterable_requires_a_single_iterable_constructor():
    """额外必需参数与默认结果工厂不兼容，运算会在创建结果时失败。"""

    class LabeledSetWithoutFactory(ListSet):
        def __init__(self, label, values):
            self.label = label
            super().__init__(values)

    values = LabeledSetWithoutFactory("features", ["a", "b"])

    with pytest.raises(TypeError):
        values | ["c"]
    with pytest.raises(TypeError):
        values & ["b"]


def test_instance_from_iterable_override_can_preserve_constructor_context():
    """常规 method override 能读取 self.label，再用正确签名创建同类运算结果。"""

    class LabeledSet(ListSet):
        def __init__(self, label, values=()):
            self.label = label
            super().__init__(values)

        def _from_iterable(self, values):
            return type(self)(self.label, values)

    values = LabeledSet("features", ["a", "b"])
    result = values | ["c"]

    assert isinstance(result, LabeledSet)
    assert result.label == "features"
    assert list(result) == ["a", "b", "c"]


def test_set_mixin_exposes_hash_helper_but_instances_are_not_hashable_by_default():
    """Set 定义 equality，故默认不可哈希；_hash 只是可选 helper。"""

    values = ListSet([1, 2])

    assert ListSet.__hash__ is None
    with pytest.raises(TypeError, match="unhashable"):
        hash(values)


def test_immutable_set_can_bind_set_hash_and_match_equal_frozenset():
    """Set._hash 与 frozenset 算法兼容，使跨实现相等值满足相同 hash。"""

    class FrozenListSet(Set):
        __hash__ = Set._hash

        def __init__(self, values=()):
            unique = ListSet(values)
            self.elements = tuple(unique)

        def __contains__(self, value):
            return _contains_equal(self.elements, value)

        def __iter__(self):
            return iter(self.elements)

        def __len__(self):
            return len(self.elements)

    custom = FrozenListSet([1, 2, 2])
    builtin = frozenset({1, 2})

    assert custom == builtin
    assert hash(custom) == hash(builtin)
    assert {custom: "value"}[FrozenListSet([2, 1])] == "value"


def test_set_hash_helper_still_requires_each_element_to_be_hashable():
    """容器可用 equality 保存 list；计算集合 hash 时仍必须调用每个元素的 hash。"""

    class NominallyFrozenListSet(ListSet):
        __hash__ = Set._hash

    values = NominallyFrozenListSet([[1, 2]])

    assert [1, 2] in values
    with pytest.raises(TypeError, match="unhashable"):
        hash(values)


def test_mutable_set_requires_add_and_discard_beyond_read_only_primitives():
    """实现 membership/iter/len 仍不足以实例化 MutableSet。"""

    class ReadOnlyImplementation(MutableSet):
        def __contains__(self, value):
            return False

        def __iter__(self):
            return iter(())

        def __len__(self):
            return 0

    assert ReadOnlyImplementation.__abstractmethods__ == {"add", "discard"}
    with pytest.raises(TypeError, match="abstract method"):
        ReadOnlyImplementation()


def test_add_and_discard_are_idempotent_primitive_operations():
    """重复 add 不产生副本，缺失 discard 不抛错；调用仍完整到达 primitive。"""

    values = TrackedMutableSet(["a"])

    assert values.add("a") is None
    assert values.add("b") is None
    assert values.discard("missing") is None

    assert values.elements == ["a", "b"]
    assert values.calls == [
        ("add", "a"),
        ("add", "b"),
        ("discard", "missing"),
    ]


def test_remove_uses_membership_then_discard_and_raises_for_missing_value():
    """remove 与 discard 的差异只在缺失分支；存在时复用具体 discard。"""

    values = TrackedMutableSet(["a", "b"])

    assert values.remove("a") is None
    assert values.elements == ["b"]
    assert values.calls == [("discard", "a")]

    values.calls.clear()
    with pytest.raises(KeyError) as error:
        values.remove("missing")
    assert error.value.args == ("missing",)
    assert values.calls == []
    assert values.elements == ["b"]


def test_pop_removes_the_first_iterated_value_but_set_contract_is_unordered():
    """mixin 调用 iter/next 后 discard；这里只因测试实现稳定，首个值才可预测。"""

    values = TrackedMutableSet(["a", "b"])
    original = ListSet(values)

    popped = values.pop()

    assert popped in original
    assert popped not in values
    assert values.elements == ["b"]
    assert values.calls == [("discard", "a")]

    empty = TrackedMutableSet()
    with pytest.raises(KeyError):
        empty.pop()


def test_mutable_set_clear_repeatedly_pops_until_empty_and_returns_none():
    """默认 clear 每轮重新取得 iterator，最后用空 pop 的 KeyError 正常结束。"""

    values = TrackedMutableSet(["a", "b", "c"])

    assert values.clear() is None
    assert values.elements == []
    assert values.iter_calls == 4
    assert values.calls == [
        ("discard", "a"),
        ("discard", "b"),
        ("discard", "c"),
    ]


def test_inplace_union_routes_each_input_through_add_and_preserves_identity():
    """``|=`` 接受 iterable，逐项 add；具体 primitive 负责去重或领域规范化。"""

    values = TrackedMutableSet(["a"])
    identity = id(values)

    values |= ["a", "b", "c"]

    assert id(values) == identity
    assert values.elements == ["a", "b", "c"]
    assert values.calls == [
        ("add", "a"),
        ("add", "b"),
        ("add", "c"),
    ]


def test_inplace_intersection_discards_values_missing_from_other_iterable():
    """``&=`` 先用只读 difference 计算待删集合，再逐项 discard。"""

    values = TrackedMutableSet(["a", "b", "c"])
    identity = id(values)

    values &= ["b", "c", "x"]

    assert id(values) == identity
    assert values.elements == ["b", "c"]
    assert values.calls == [("discard", "a")]


def test_inplace_symmetric_difference_toggles_membership_through_primitives():
    """``^=`` 对已有值 discard、对新值 add；一般 iterable 会先转换成同类 set。"""

    values = TrackedMutableSet(["a", "b"])
    identity = id(values)

    values ^= ["b", "c"]

    assert id(values) == identity
    assert values.elements == ["a", "c"]
    assert values.calls == [
        ("discard", "b"),
        ("add", "c"),
    ]


def test_inplace_difference_discards_each_input_and_ignores_missing_values():
    """``-=`` 直接遍历输入并 discard，因此不存在的值不会造成错误。"""

    values = TrackedMutableSet(["a", "b", "c"])
    identity = id(values)

    values -= ["b", "missing"]

    assert id(values) == identity
    assert values.elements == ["a", "c"]
    assert values.calls == [
        ("discard", "b"),
        ("discard", "missing"),
    ]


def test_self_alias_symmetric_difference_and_subtraction_clear_safely():
    """mixin 先检测 other is self，不会一边迭代同一对象一边删除。"""

    symmetric = TrackedMutableSet(["a", "b"])
    subtraction = TrackedMutableSet(["a", "b"])

    symmetric ^= symmetric
    subtraction -= subtraction

    assert symmetric.elements == []
    assert subtraction.elements == []
    assert symmetric.calls == [("discard", "a"), ("discard", "b")]
    assert subtraction.calls == [("discard", "a"), ("discard", "b")]


def test_mutation_mixins_preserve_a_domain_invariant_through_add_and_discard():
    """规范化集中在 primitive 后，``|=`` 与 ``-=`` 等默认算法自然沿用规则。"""

    class Tags(TrackedMutableSet):
        @staticmethod
        def _normalize(value):
            if not isinstance(value, str):
                raise TypeError("tag must be str")
            return value.strip().casefold()

        def __contains__(self, value):
            try:
                normalized = self._normalize(value)
            except TypeError:
                return False
            return super().__contains__(normalized)

        def add(self, value):
            super().add(self._normalize(value))

        def discard(self, value):
            super().discard(self._normalize(value))

    tags = Tags([" Python ", "PYTHON"])
    tags |= [" Rust ", "python"]
    tags -= ["RUST"]

    assert tags.elements == ["python"]
    assert " PYTHON " in tags

    with pytest.raises(TypeError, match="tag must be str"):
        tags.add(42)
