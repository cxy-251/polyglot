"""零宽匹配、游标推进与编译失败。

共同问题：零宽成功如何避免无限迭代；复用 matcher 是否泄漏游标；
非法模式在什么阶段报告。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/python/stdlib/036-040_text_processing/test_036_regular_expressions.py

import re

import pytest


def test_finditer_advances_after_zero_width_matches():
    pattern = re.compile(r"(?=.)")

    matches = list(pattern.finditer("ab"))

    assert [match.span() for match in matches] == [(0, 0), (1, 1)]
    assert [match.group() for match in matches] == ["", ""]


def test_position_is_an_explicit_call_argument_not_pattern_state():
    pattern = re.compile(r"\d")
    text = "1a2"

    assert pattern.search(text, pos=0).span() == (0, 1)
    assert pattern.search(text, pos=1).span() == (2, 3)
    assert pattern.search(text, pos=0).span() == (0, 1)


def test_invalid_pattern_fails_during_compile():
    with pytest.raises(re.error):
        re.compile("(")
