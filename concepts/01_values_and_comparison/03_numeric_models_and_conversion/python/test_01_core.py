"""数值模型与转换。

共同问题：整数是否溢出；浮点特殊值如何表现；显式转换如何报告失败；
混合运算采用什么结果类型。
"""

# polyglot-family: values_and_comparison
# polyglot-concept: numeric_models_and_conversion
# polyglot-related: languages/python/builtins/test_019_boolean_and_integer_types.py
# polyglot-related: languages/python/builtins/test_020_float_and_complex_types.py

import math

import pytest


def test_integers_expand_instead_of_overflowing_at_a_fixed_width():
    large = 2**100

    assert large + 1 == 1267650600228229401496703205377
    assert large.bit_length() == 101
    assert isinstance(large, int)

    # Python int 的内存会随数值增长；不能迁移 C++ 固定宽度整数或 JavaScript Number 的溢出假设。


def test_float_keeps_ieee_special_values_and_loses_large_integer_precision():
    rounded = float(2**53 + 1)

    assert rounded == float(2**53)
    assert math.isnan(float("nan"))
    assert math.isinf(float("inf"))
    assert math.copysign(1.0, -0.0) == -1.0


def test_explicit_numeric_conversion_has_visible_failure_rules():
    assert int("101", 2) == 5
    assert int(3.9) == 3
    assert float("1.25") == 1.25

    with pytest.raises(ValueError):
        int("1.5")


def test_mixed_numeric_operations_promote_but_division_modes_remain_distinct():
    assert 3 + 0.5 == 3.5
    assert isinstance(3 + 0.5, float)
    assert 7 / 2 == 3.5
    assert -7 // 2 == -4
    assert -7 % 2 == 1
