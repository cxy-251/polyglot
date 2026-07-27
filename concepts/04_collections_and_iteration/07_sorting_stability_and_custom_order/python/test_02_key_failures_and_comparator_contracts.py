"""排序回调、失败与次序契约。

共同问题：排序回调可能调用多少次；回调失败时输入是否改变；
不一致的次序关系是否由运行时修复。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: sorting_stability_and_custom_order
# polyglot-related: languages/python/builtins/test_023_general_sequence_types.py

from functools import cmp_to_key

import pytest


def test_sorted_key_failure_leaves_the_input_iterable_unchanged():
    values = ["bbb", "stop", "a"]
    calls = []

    def key(value):
        calls.append(value)
        if value == "stop":
            raise ValueError("cannot rank")
        return len(value)

    with pytest.raises(ValueError, match="rank"):
        sorted(values, key=key)

    assert values == ["bbb", "stop", "a"]
    assert calls == ["bbb", "stop"]


def test_cmp_to_key_adapts_a_repeated_comparator_protocol():
    calls = []

    def compare(left, right):
        calls.append((left, right))
        return (left > right) - (left < right)

    assert sorted([3, 1, 2], key=cmp_to_key(compare)) == [1, 2, 3]
    assert calls

    # 普通 key 每个元素只求值一次；cmp_to_key 包装的 comparator 可被重复调用。比较器
    # 必须给出一致次序，排序实现不会验证传递性或替调用方修复矛盾结果。
