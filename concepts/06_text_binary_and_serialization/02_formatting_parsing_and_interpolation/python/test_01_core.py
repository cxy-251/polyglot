"""格式化、解析与插值。

共同问题：插值何时求值；格式说明如何控制表示；解析是否接受前缀；
失败通过异常还是特殊值报告。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: formatting_parsing_and_interpolation
# polyglot-related: languages/python/language/test_014_representation_formatting_and_hashing.py

import pytest


def test_f_string_evaluates_expressions_and_uses_format_protocol():
    value = 12.345

    assert f"{value:.2f}" == "12.35"
    assert f"{255:#x}" == "0xff"


def test_custom_format_method_receives_the_format_spec():
    class Label:
        def __format__(self, spec):
            return f"{spec}:value"

    assert f"{Label():upper}" == "upper:value"


def test_integer_parsing_is_strict_and_base_can_be_explicit():
    assert int("101", 2) == 5
    assert int("0xff", 0) == 255

    with pytest.raises(ValueError):
        int("12px")


def test_float_parsing_accepts_whitespace_but_not_a_numeric_prefix():
    assert float(" 1.25 ") == 1.25

    with pytest.raises(ValueError):
        float("1.25px")

