"""排序、哈希与键语义。

共同问题：排序依赖什么关系；相等对象是否必须同哈希；哪些值能作为键；
映射与集合如何判断同一个键。
"""

# polyglot-family: values_and_comparison
# polyglot-concept: ordering_hashing_and_key_semantics
# polyglot-related: languages/python/language/test_002_comparison_semantics.py
# polyglot-related: languages/python/language/test_014_representation_formatting_and_hashing.py
# polyglot-related: languages/python/builtins/test_024_mapping_dict.py

import pytest


class Ticket:
    def __init__(self, number):
        self.number = number

    def __eq__(self, other):
        if not isinstance(other, Ticket):
            return NotImplemented
        return self.number == other.number

    def __hash__(self):
        return hash(self.number)

    def __lt__(self, other):
        if not isinstance(other, Ticket):
            return NotImplemented
        return self.number < other.number


def test_custom_value_uses_consistent_equality_hash_and_ordering():
    first = Ticket(2)
    same = Ticket(2)
    earlier = Ticket(1)

    assert first == same
    assert hash(first) == hash(same)
    assert sorted([first, earlier]) == [earlier, first]


def test_mapping_and_set_merge_equal_hashable_keys():
    first = Ticket(2)
    same = Ticket(2)

    mapping = {first: "original", same: "replacement"}
    values = {first, same}

    assert len(mapping) == 1
    assert mapping[first] == "replacement"
    assert len(values) == 1


def test_mutable_builtin_containers_are_not_hashable_keys():
    with pytest.raises(TypeError):
        hash([])
    with pytest.raises(TypeError):
        {[]: "value"}


def test_unrelated_types_do_not_gain_an_arbitrary_total_order():
    with pytest.raises(TypeError):
        sorted([1, "1"])

    # JavaScript 默认 sort 会先字符串化；Python 3 要求元素真正支持所需次序关系。
