"""排序稳定性与自定义次序。

共同问题：默认顺序是什么；排序是否稳定；key/comparator 调用模型如何；
排序是原地操作还是返回副本。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/python/builtins/test_023_general_sequence_types.py

import pytest


def test_sorted_returns_a_new_list_and_list_sort_mutates_in_place():
    values = [3, 1, 2]

    copied = sorted(values)
    result = values.sort()

    assert copied == [1, 2, 3]
    assert values == [1, 2, 3]
    assert result is None


def test_sort_is_stable_for_equal_keys():
    records = [("a", 1), ("b", 0), ("c", 1)]

    sorted_records = sorted(records, key=lambda record: record[1])

    assert [record[0] for record in sorted_records] == ["b", "a", "c"]


def test_key_function_runs_once_per_input_element():
    calls = []
    values = ["bbb", "a", "cc"]

    result = sorted(values, key=lambda value: calls.append(value) or len(value))

    assert result == ["a", "cc", "bbb"]
    assert calls == values


def test_unrelated_values_without_order_raise_type_error():
    with pytest.raises(TypeError):
        sorted([1, "2"])

    # JavaScript 默认 sort 会字符串化；Python 不会静默建立跨类型字典序。

