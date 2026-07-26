"""正则表达式、捕获与状态。

共同问题：全串匹配与搜索如何区分；捕获组如何读取；替换回调获得什么；
复用正则对象是否携带可变游标。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/python/stdlib/036-040_text_processing/test_036_regular_expressions.py

import re


def test_search_and_fullmatch_answer_different_questions():
    pattern = re.compile(r"\d+")

    assert pattern.search("id=12").group() == "12"
    assert pattern.fullmatch("12").group() == "12"
    assert pattern.fullmatch("id=12") is None


def test_numbered_and_named_groups_expose_captures():
    match = re.fullmatch(r"(?P<name>[a-z]+)-(\d+)", "item-12")

    assert match.groups() == ("item", "12")
    assert match.group("name") == "item"


def test_replacement_callback_receives_match_object():
    result = re.sub(r"\d+", lambda match: str(int(match.group()) * 2), "a2b3")

    assert result == "a4b6"


def test_pattern_reuse_does_not_keep_a_global_last_index():
    pattern = re.compile(r"\d")

    assert pattern.search("1").group() == "1"
    assert pattern.search("1").group() == "1"

    # JavaScript global/sticky RegExp 会修改 lastIndex；Python Pattern 查询由每次调用参数定位。

