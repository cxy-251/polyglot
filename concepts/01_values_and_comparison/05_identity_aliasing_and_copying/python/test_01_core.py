"""对象身份、别名与复制。

共同问题：赋值是否复制对象；浅复制保留哪些别名；深复制如何处理对象图；
语言如何表达独占或共享所有权。
"""

# polyglot-family: values_and_comparison
# polyglot-concept: identity_aliasing_and_copying
# polyglot-related: languages/python/builtins/test_023_general_sequence_types.py

import copy


def test_assignment_creates_an_alias_not_a_container_copy():
    original = {"items": [1]}
    alias = original

    alias["items"].append(2)

    assert alias is original
    assert original == {"items": [1, 2]}


def test_shallow_copy_duplicates_outer_container_but_shares_children():
    original = {"items": [1]}
    cloned = copy.copy(original)

    cloned["items"].append(2)

    assert cloned is not original
    assert cloned["items"] is original["items"]
    assert original["items"] == [1, 2]


def test_deepcopy_duplicates_nested_mutable_objects_and_preserves_cycles():
    original = {"items": [1]}
    original["self"] = original

    cloned = copy.deepcopy(original)
    cloned["items"].append(2)

    assert cloned is not original
    assert cloned["items"] is not original["items"]
    assert original["items"] == [1]
    assert cloned["self"] is cloned


def test_immutable_values_may_share_identity_without_making_is_value_equality():
    first = tuple([1, 2])
    second = tuple([1, 2])

    assert first == second
    assert first is not second

    # `is` 只用于单例或身份；实现是否驻留某个不可变值不能作为程序语义。
