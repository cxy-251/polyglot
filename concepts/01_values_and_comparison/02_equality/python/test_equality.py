"""横向概念 002｜值相等、对象身份与数值特例。

共同问题：跨数值类型是否转换；NaN 和负零如何比较；集合按内容还是身份比较；
自定义类型如何提供值语义。
"""

# polyglot-family: values_and_comparison
# polyglot-concept: equality
# polyglot-related: languages/python/language/test_002_comparison_semantics.py


class Version:
    def __init__(self, major, minor):
        self.parts = (major, minor)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.parts == other.parts


def test_numeric_equality_has_explicit_special_cases():
    nan = float("nan")

    assert 1 == 1.0
    assert 1 != "1"
    assert nan != nan
    assert 0.0 == -0.0


def test_builtin_collections_compare_contents_while_is_compares_identity():
    first = [1, 2]
    same_value = [1, 2]
    alias = first

    assert first == same_value
    assert first is not same_value
    assert first is alias


def test_custom_eq_defines_value_semantics_and_can_decline_other_types():
    stable = Version(3, 10)
    same = Version(3, 10)
    newer = Version(3, 11)

    assert stable == same
    assert stable != newer
    assert stable != (3, 10)
