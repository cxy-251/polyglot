"""运算符与协议定制。

共同问题：类型能否重载运算符；左右操作数如何协商；转换协议何时触发；
不支持的组合在编译期还是运行期失败。
"""

# polyglot-family: objects_and_dispatch
# polyglot-concept: operator_and_protocol_customization
# polyglot-related: languages/python/language/test_003_binary_operator_dispatch.py
# polyglot-related: languages/python/language/test_004_unary_and_conversion_protocols.py

import operator

import pytest


class Distance:
    def __init__(self, meters):
        self.meters = meters

    def __add__(self, other):
        if isinstance(other, Distance):
            return Distance(self.meters + other.meters)
        return NotImplemented

    def __radd__(self, other):
        if other == 0:
            return self
        return NotImplemented

    def __bool__(self):
        return self.meters != 0

    def __index__(self):
        return self.meters


def test_binary_operator_uses_special_method_dispatch():
    result = Distance(2) + Distance(3)

    assert isinstance(result, Distance)
    assert result.meters == 5


def test_not_implemented_allows_reflected_fallback():
    assert sum([Distance(2), Distance(3)]).meters == 5

    with pytest.raises(TypeError):
        _ = Distance(1) + 1


def test_conversion_protocols_serve_distinct_syntax():
    zero = Distance(0)
    three = Distance(3)

    assert bool(zero) is False
    assert bool(three) is True
    assert operator.index(three) == 3


def test_special_methods_are_looked_up_on_the_type():
    value = Distance(2)
    value.__add__ = lambda other: Distance(100)

    assert (value + Distance(3)).meters == 5
    assert value.__add__(Distance(3)).meters == 100
