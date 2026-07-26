"""集合成员、去重与运算。

共同问题：集合使用哪种相等关系；是否保持顺序；如何表达集合运算；
可变集合能否作为另一个集合的成员。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: sets_membership_and_deduplication
# polyglot-related: languages/python/builtins/test_025_set_types.py

import pytest


def test_set_deduplicates_by_hash_and_equality():
    values = {1, 1.0, True}

    assert len(values) == 1
    assert 1 in values


def test_set_algebra_returns_new_sets():
    left = {1, 2}
    right = {2, 3}

    assert left | right == {1, 2, 3}
    assert left & right == {2}
    assert left - right == {1}
    assert left ^ right == {1, 3}


def test_frozenset_is_hashable_but_mutable_set_is_not():
    outer = {frozenset({1, 2})}

    assert frozenset({2, 1}) in outer
    with pytest.raises(TypeError):
        {set()}


def test_custom_equal_objects_collapse_when_hashes_match():
    class Key:
        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            return isinstance(other, Key) and self.value == other.value

        def __hash__(self):
            return hash(self.value)

    assert len({Key(1), Key(1)}) == 1

