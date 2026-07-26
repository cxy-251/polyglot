"""025｜``set`` / ``frozenset`` 的去重、集合代数与偏序语义示例。

set 是可变的唯一元素集合，frozenset 是不可变且可 hash 的集合值。集合不保存
可依赖的位置顺序；比较运算表达包含关系的偏序，而不是按元素数量或字典序排序。

通用比较、二元运算和 hash 协议已在 002、003、014 展示；本文件聚焦内置集合
类型自身。内容基于 Python 3.10 Set Types。
"""

# polyglot-covers: python.type.set python.type.frozenset
# polyglot-covers: python.builtin.set python.builtin.frozenset python.literal.set
# polyglot-covers: python.set.hashable-elements python.set.uniqueness
# polyglot-covers: python.set.union python.set.intersection python.set.difference
# polyglot-covers: python.set.symmetric-difference python.set.relations
# polyglot-covers: python.set.update-methods python.set.removal-methods
# polyglot-covers: python.set.copy python.set.iteration-mutation
# polyglot-covers: python.frozenset.hashability python.set.mixed-result-type

import pytest


def test_set_literal_constructor_and_comprehension_create_unique_elements():
    """literal 适合已有元素，set(iterable) 消费输入并按 equality/hash 去重。"""

    literal = {"read", "write", "read"}
    from_iterable = set(["read", "write", "read"])
    normalized = {name.casefold() for name in ["Admin", "ADMIN", "User"]}

    assert literal == from_iterable == {"read", "write"}
    assert normalized == {"admin", "user"}
    assert set("mississippi") == {"m", "i", "s", "p"}


def test_empty_braces_create_dict_so_empty_set_requires_constructor():
    """``{}`` 已分配给空 dict 语法；空 set 没有单独字面量。"""

    assert type({}) is dict
    assert type(set()) is set
    assert set() == set([])
    assert frozenset() == frozenset([])


def test_set_elements_must_be_hashable_and_equal_values_are_one_member():
    """集合使用与 dict key 相同的 equality/hash 契约。"""

    numeric = {True, 1, 1.0}

    assert len(numeric) == 1
    assert True in numeric and 1.0 in numeric

    with pytest.raises(TypeError):
        {[1, 2]}

    with pytest.raises(TypeError):
        {set([1, 2])}

    # 需要嵌套集合时把内层转换为 frozenset；元素本身必须在集合生命周期内可 hash。


def test_set_has_membership_but_no_position_or_stable_iteration_contract():
    """集合回答“是否存在”，不提供按位置读取。"""

    tags = {"python", "testing", "examples"}

    assert "python" in tags
    assert "missing" not in tags
    assert len(tags) == 3

    with pytest.raises(TypeError):
        tags[0]

    # 可以迭代 set，但不要把观察到的顺序写入协议、快照断言或用户界面排序规则。
    assert set(iter(tags)) == tags


def test_set_algebra_models_permissions_and_changes():
    """并、交、差和对称差分别表达任一、共同、仅左、恰好一侧。"""

    current = {"read", "write"}
    requested = {"write", "delete"}

    assert current | requested == {"read", "write", "delete"}
    assert current & requested == {"write"}
    assert current - requested == {"read"}
    assert current ^ requested == {"read", "delete"}

    # difference 有方向，`current - requested` 与反向结果不同。
    assert requested - current == {"delete"}


def test_set_methods_accept_any_iterable_but_operators_require_sets():
    """方法适合与普通 iterable 交互；运算符保持集合对集合的明确性。"""

    base = {"read"}

    assert base.union(["write"], ("delete",)) == {"read", "write", "delete"}
    assert {"a", "b"}.intersection("bread") == {"a", "b"}
    assert {"read", "write"}.difference(["write"]) == {"read"}
    assert base.isdisjoint(["write", "delete"])

    with pytest.raises(TypeError):
        base | ["write"]

    with pytest.raises(TypeError):
        base & ["read"]


def test_subset_superset_and_disjoint_methods_express_relationships():
    """包含关系与集合大小相关但不等同于只比较 len。"""

    guest = {"read"}
    editor = {"read", "write"}
    admin = {"read", "write", "delete"}

    assert guest.issubset(editor)
    assert editor.issuperset(guest)
    assert guest <= editor < admin
    assert admin > guest
    assert set().issubset(guest)
    assert guest.isdisjoint({"write", "delete"})
    assert not editor.isdisjoint({"write", "delete"})


def test_set_ordering_is_partial_not_a_total_sort_order():
    """两个各有独占元素的集合互不可比，即使元素数量不同。"""

    left = {"a", "b"}
    right = {"b", "c", "d"}

    assert left != right
    assert not (left < right)
    assert not (left > right)
    assert not (left <= right)
    assert not (left >= right)

    # `<` 表示“真子集”，不是 len(left) < len(right)。需要展示排序时显式提供 key。


def test_add_and_update_modify_in_place_and_return_none():
    """add 接收一个元素，update 逐项消费一个或多个 iterable。"""

    tags = {"python"}

    assert tags.add("testing") is None
    assert tags.add("testing") is None
    assert tags.update(["examples"], ("reference",)) is None

    assert tags == {"python", "testing", "examples", "reference"}

    characters = set()
    characters.update("ab")
    assert characters == {"a", "b"}

    # update("ab") 添加两个字符；把字符串作为单个标签时应使用 add("ab")。


def test_in_place_set_algebra_methods_replace_contents_and_return_none():
    """update 家族把运算结果写回原 set，调用者不要接收其返回值。"""

    allowed = {"read", "write", "delete"}

    assert allowed.intersection_update({"read", "write"}) is None
    assert allowed == {"read", "write"}

    assert allowed.difference_update({"write"}) is None
    assert allowed == {"read"}

    assert allowed.symmetric_difference_update({"read", "audit"}) is None
    assert allowed == {"audit"}

    allowed |= {"read"}
    allowed &= {"read", "audit"}
    assert allowed == {"read", "audit"}


def test_remove_discard_pop_and_clear_have_different_missing_behavior():
    """remove 要求元素存在，discard 幂等；pop 返回任意元素而非首末元素。"""

    values = {"a", "b", "c"}

    values.remove("a")
    values.discard("missing")

    before_pop = values.copy()
    popped = values.pop()
    assert popped in before_pop
    assert popped not in values

    with pytest.raises(KeyError):
        values.remove("missing")

    assert values.clear() is None
    assert values == set()

    with pytest.raises(KeyError):
        values.pop()

    # `pop()` 的选择不可依赖；需要确定策略时先按业务规则选择元素再 remove。


def test_set_copy_is_a_new_container_but_shares_element_objects():
    """copy 只复制外层哈希表，不复制其中的对象。"""

    class Label:
        pass

    label = Label()
    label.name = "before"
    original = {label}
    copied = original.copy()

    assert copied == original
    assert copied is not original
    assert next(iter(copied)) is label

    label.name = "after"
    assert next(iter(original)).name == "after"
    assert next(iter(copied)).name == "after"

    copied.add(Label())
    assert len(copied) == 2
    assert len(original) == 1


def test_frozenset_is_immutable_hashable_and_supports_nested_sets():
    """冻结集合可安全作为 dict key 或另一个 set 的元素。"""

    permissions = frozenset(["read", "write", "read"])
    cache = {permissions: "editor"}
    groups = {frozenset({"a", "b"}), frozenset({"b", "c"})}

    assert permissions == frozenset({"read", "write"})
    assert cache[frozenset({"write", "read"})] == "editor"
    assert len(groups) == 2
    assert hash(permissions) == hash(frozenset({"write", "read"}))

    with pytest.raises(AttributeError):
        permissions.add("delete")


def test_mixed_set_and_frozenset_operations_use_left_operand_result_type():
    """相同元素结果的可变性由二元运算左侧类型决定。"""

    mutable = {1, 2}
    frozen = frozenset({2, 3})

    left_mutable = mutable | frozen
    left_frozen = frozen | mutable

    assert left_mutable == left_frozen == {1, 2, 3}
    assert type(left_mutable) is set
    assert type(left_frozen) is frozenset

    # API 需要 hashable 结果时把 frozenset 放左边并不够清楚；显式 frozenset(result)
    # 更能表达边界意图。


def test_frozenset_copy_and_set_copy_preserve_value_equality():
    """冻结/可变副本内容相同，但只有 frozenset 可作键。"""

    frozen = frozenset({1, 2})
    mutable = set(frozen)

    assert frozen.copy() == frozen
    assert mutable.copy() == mutable
    assert frozen == mutable

    with pytest.raises(TypeError):
        hash(mutable)


def test_changing_set_size_during_iteration_raises_runtime_error():
    """set iterator 在结构变化后失效，异常前的删除不会自动回滚。"""

    values = {1, 2, 3}
    original_size = len(values)

    with pytest.raises(RuntimeError, match="changed size during iteration"):
        for value in values:
            values.remove(value)

    assert len(values) == original_size - 1


def test_snapshot_or_comprehension_supports_safe_set_rewrite():
    """遍历副本可原地改写；推导式适合生成新的过滤集合。"""

    in_place = {1, 2, 3, 4}
    for value in in_place.copy():
        if value % 2 == 0:
            in_place.remove(value)

    rebuilt = {value for value in {1, 2, 3, 4} if value % 2 == 1}

    assert in_place == {1, 3}
    assert rebuilt == {1, 3}
