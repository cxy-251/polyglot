"""横向概念 001｜真假值与逻辑运算结果。

共同问题：数值零、空文本、空集合和空值如何判断；自定义对象能否定义真假；
逻辑运算符返回布尔值还是原操作数。
"""

# polyglot-concept: truthiness
# polyglot-related: languages/python/language/test_001_truth_value_testing.py


class ExplicitFlag:
    def __init__(self, enabled):
        self.enabled = enabled

    def __bool__(self):
        return self.enabled


class SizedQueue:
    def __init__(self, items):
        self.items = list(items)

    def __len__(self):
        return len(self.items)


def test_zero_empty_text_and_none_are_false():
    assert bool(0) is False
    assert bool(1) is True
    assert bool("") is False
    assert bool("0") is True
    assert bool(None) is False


def test_empty_builtin_collections_are_false():
    assert bool([]) is False
    assert bool({}) is False
    assert bool(set()) is False
    assert bool([0]) is True


def test_custom_objects_can_define_truth_with_two_protocol_levels():
    assert bool(object()) is True
    assert bool(ExplicitFlag(False)) is False
    assert bool(ExplicitFlag(True)) is True
    assert bool(SizedQueue([])) is False
    assert bool(SizedQueue(["job"])) is True


def test_and_or_return_the_selected_operand():
    fallback = {"source": "default"}
    payload = ["ready"]

    assert ([] or fallback) is fallback
    assert (payload and fallback) is fallback
    assert ([] and fallback) == []
