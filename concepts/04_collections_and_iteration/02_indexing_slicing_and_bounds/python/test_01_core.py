"""索引、切片与边界。

共同问题：负索引如何解释；切片是否复制；越界如何报告；
自定义类型通过什么入口接收索引与切片。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: indexing_slicing_and_bounds
# polyglot-related: languages/python/language/test_005_subscription_and_slicing_protocols.py

import pytest


def test_negative_index_counts_from_the_end():
    values = ["a", "b", "c"]

    assert values[-1] == "c"
    assert values[-3] == "a"


def test_slice_clamps_bounds_and_returns_a_new_list():
    values = [0, 1, 2, 3]
    sliced = values[-10:10:2]

    assert sliced == [0, 2]
    assert sliced is not values


def test_single_index_out_of_range_raises_but_slice_does_not():
    values = [1, 2]

    with pytest.raises(IndexError):
        _ = values[2]
    assert values[2:100] == []


def test_getitem_receives_index_or_slice_object():
    class Recorder:
        def __init__(self):
            self.keys = []

        def __getitem__(self, key):
            self.keys.append(key)
            return key

    value = Recorder()

    assert value[2] == 2
    assert value[1:5:2] == slice(1, 5, 2)
    assert value.keys == [2, slice(1, 5, 2)]
