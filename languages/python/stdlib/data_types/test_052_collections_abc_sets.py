"""052｜``Set`` 与 ``MutableSet`` 的比较、代数运算和 mutation mixin。

ABC 只规定有限集合接口及算法关系，不要求 hash-table 存储。本文件使用 list-backed
实现来容纳不可哈希元素，并保留首次出现顺序以便断言稳定。
这个顺序不是 Set 合同。

结果类型由 ``_from_iterable()`` 决定，可变算法通过 ``add()`` / ``discard()`` 回调
具体实现。当前文件尚未经过 pytest 验证。
"""

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

from collections.abc import MutableSet
from collections.abc import Set

import pytest


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


def test_clear_repeatedly_pops_until_empty_and_returns_none():
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
