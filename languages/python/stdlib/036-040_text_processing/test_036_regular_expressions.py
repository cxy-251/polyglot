"""036｜``re`` 正则表达式的匹配、捕获、替换与 flags 示例。

正则同时经过 Python 字符串语法和 regex 语法两层解释，因此 pattern 通常写 raw
string。search/match/fullmatch 决定搜索范围；捕获组会改变 findall/split/sub 的
结果结构；flags 又会改变锚点、点号和 Unicode 字符类语义。

内容基于 Python 3.10 re 文档与 Regular Expression HOWTO。性能陷阱只用小输入
说明结构，不做阻塞式压力测试。
"""

# polyglot-covers: python.stdlib.re python.re.compile python.re.cache
# polyglot-covers: python.re.search python.re.match python.re.fullmatch
# polyglot-covers: python.re.findall python.re.finditer python.re.split
# polyglot-covers: python.re.sub python.re.subn python.re.escape
# polyglot-covers: python.re.Match python.re.groups python.re.named-groups
# polyglot-covers: python.re.backreference python.re.lookaround
# polyglot-covers: python.re.greedy-lazy python.re.alternation python.re.anchors
# polyglot-covers: python.re.flags python.re.unicode-ascii
# polyglot-covers: python.re.bytes python.re.error python.re.zero-length
# polyglot-covers: python.re.backtracking-risk

import re

import pytest


def test_raw_string_prevents_python_from_consuming_regex_backslashes():
    r"""普通字符串中的 ``\b`` 是 backspace，raw string 中才交给 regex 作单词边界。"""

    ordinary = "\bword\b"
    raw = r"\bword\b"

    assert ordinary == "\x08word\x08"
    assert re.search(ordinary, "a word b") is None
    assert re.search(raw, "a word b").group() == "word"

    # raw string 只关闭 Python 层转义；regex 引擎仍会把 r"\n" 解释成换行匹配。
    assert re.search(r"\n", "first\nsecond").span() == (5, 6)


def test_compile_exposes_pattern_metadata_and_named_group_index():
    """编译对象可复用，并记录原 pattern、flags、捕获组数和命名组编号。"""

    pattern = re.compile(
        r"(?P<key>[a-z]+)=(?P<value>\d+)",
        re.IGNORECASE,
    )

    assert pattern.pattern == r"(?P<key>[a-z]+)=(?P<value>\d+)"
    assert pattern.flags & re.IGNORECASE
    assert pattern.groups == 2
    assert pattern.groupindex == {"key": 1, "value": 2}
    assert pattern.fullmatch("Port=8080")


def test_compile_uses_cache_and_purge_clears_cached_patterns():
    """模块会缓存最近使用的 pattern；purge 清空缓存但不使旧对象失效。"""

    re.purge()
    first = re.compile(r"item-\d+")
    second = re.compile(r"item-\d+")

    assert first is second
    assert first.fullmatch("item-42")

    re.purge()
    third = re.compile(r"item-\d+")

    assert third is not first
    assert first.fullmatch("item-7")
    assert third.fullmatch("item-7")


def test_search_match_and_fullmatch_have_different_ranges():
    """search 扫描任意位置，match 固定起点，fullmatch 要求消费整个范围。"""

    text = "prefix item-42 suffix"
    pattern = r"item-\d+"

    assert re.search(pattern, text).span() == (7, 14)
    assert re.match(pattern, text) is None
    assert re.fullmatch(pattern, text) is None
    assert re.fullmatch(pattern, "item-42").group() == "item-42"

    # 输入验证应使用 fullmatch；match 成功仍可能留下未验证尾部。
    assert re.match(r"\d+", "123oops").group() == "123"
    assert re.fullmatch(r"\d+", "123oops") is None


def test_pattern_methods_accept_pos_endpos_without_slicing_original_string():
    """pos/endpos 限制搜索窗口，Match.string 仍指向完整原字符串。"""

    pattern = re.compile(r"\d+")
    text = "xx123yy"
    match = pattern.fullmatch(text, 2, 5)

    assert match.group() == "123"
    assert match.span() == (2, 5)
    assert match.string is text
    assert match.pos == 2
    assert match.endpos == 5


def test_findall_return_shape_depends_on_number_of_capturing_groups():
    """无组返回整段，一组返回该组，多组返回 tuple；non-capturing 不计入。"""

    text = "x=1 y=22"

    assert re.findall(r"\w+=\d+", text) == ["x=1", "y=22"]
    assert re.findall(r"\w+=(\d+)", text) == ["1", "22"]
    assert re.findall(r"(\w+)=(\d+)", text) == [("x", "1"), ("y", "22")]
    assert re.findall(r"(?:\w+)=(\d+)", text) == ["1", "22"]

    # 只为优先级加括号时写 `(?:...)`，否则重构会悄悄改变 findall API。


def test_finditer_returns_match_objects_with_groups_and_spans():
    """需要位置、命名组或延迟消费时使用 finditer。"""

    pattern = re.compile(r"(?P<name>\w+)=(?P<value>\d+)")
    matches = list(pattern.finditer("x=1 y=22"))

    assert [match.groupdict() for match in matches] == [
        {"name": "x", "value": "1"},
        {"name": "y", "value": "22"},
    ]
    assert [match.span("value") for match in matches] == [(2, 3), (6, 8)]


def test_split_includes_captured_delimiters_and_respects_maxsplit():
    """分隔 pattern 有捕获组时，分隔符也插入结果。"""

    text = "alpha,beta;gamma"

    assert re.split(r"[,;]", text) == ["alpha", "beta", "gamma"]
    assert re.split(r"([,;])", text) == [
        "alpha",
        ",",
        "beta",
        ";",
        "gamma",
    ]
    assert re.split(r"([,;])", text, maxsplit=1) == ["alpha", ",", "beta;gamma"]

    assert re.split(r"\s*", "ab") == ["", "a", "b", ""]


def test_sub_and_subn_support_count_and_unambiguous_group_references():
    r"""``\g<name>``/``\g<number>`` 避免反向引用后紧跟数字时的歧义。"""

    pattern = re.compile(r"(?P<first>\w+)\s+(?P<last>\w+)")

    assert pattern.sub(r"\g<last>, \g<first>", "Ada Lovelace") == "Lovelace, Ada"
    assert re.sub(r"(\d+)", r"[\g<1>]", "x1 y22", count=1) == "x[1] y22"
    assert re.subn(r"\d+", "#", "x1 y22") == ("x# y#", 2)


def test_callable_replacement_can_compute_from_each_match():
    """replacement callable 接收 Match，可实现上下文相关转换而不手工切片。"""

    calls = []

    def increment(match):
        calls.append((match.group(), match.span()))
        return str(int(match.group()) + 1)

    result = re.sub(r"\d+", increment, "version 7 build 41")

    assert result == "version 8 build 42"
    assert calls == [("7", (8, 9)), ("41", (16, 18))]


def test_escape_builds_literal_pattern_not_literal_replacement():
    """re.escape 让用户文本按字面匹配；replacement 有另一套反斜杠规则。"""

    literal = "price ($5.00) + tax?"
    pattern = re.compile(re.escape(literal))

    assert pattern.fullmatch(literal)
    assert pattern.search(f"before {literal} after").group() == literal

    # replacement 只需按 replacement 语法处理反斜杠；不要机械 re.escape(replacement)。


def test_match_group_apis_describe_optional_named_captures():
    """未参与匹配的可选组 group 为 None，位置为 -1；groups 可指定默认值。"""

    pattern = re.compile(
        r"(?P<year>\d{4})-(?P<month>\d{2})(?:-(?P<day>\d{2}))?"
    )
    match = pattern.fullmatch("2026-07")

    assert match.group() == "2026-07"
    assert match.group(1, 2, 3) == ("2026", "07", None)
    assert match["year"] == "2026"
    assert match.groups(default="missing") == ("2026", "07", "missing")
    assert match.groupdict(default="missing") == {
        "year": "2026",
        "month": "07",
        "day": "missing",
    }
    assert match.span("year") == (0, 4)
    assert match.start("day") == -1
    assert match.end("day") == -1
    assert match.lastindex == 2
    assert match.lastgroup == "month"


def test_named_numbered_backreferences_and_noncapturing_groups():
    """pattern 内 backreference 要求后文重复此前捕获的实际文本。"""

    repeated = re.compile(r"\b(?P<word>\w+)\s+(?P=word)\b", re.IGNORECASE)

    assert repeated.search("This is is repeated").group() == "is is"
    assert repeated.search("This is not repeated") is None
    assert re.fullmatch(r"(ha)-\1", "ha-ha")

    noncapturing = re.fullmatch(r"(?:ha)-(ha)", "ha-ha")
    assert noncapturing.groups() == ("ha",)


def test_greedy_and_lazy_quantifiers_choose_different_endpoints():
    """量词默认尽可能多匹配；尾随 ``?`` 改为满足整体 pattern 的最少匹配。"""

    text = "<b>bold</b><i>italic</i>"

    assert re.findall(r"<.*>", text) == ["<b>bold</b><i>italic</i>"]
    assert re.findall(r"<.*?>", text) == ["<b>", "</b>", "<i>", "</i>"]

    # 即使 lazy 也不是 HTML 解析器；嵌套/引号/错误恢复需要专用 parser。


def test_alternation_is_left_to_right_not_automatically_longest():
    """首个能完成匹配的分支获胜，即使后续分支可消费更多字符。"""

    left_first = re.match(r"a|ab", "ab")
    longer_first = re.match(r"ab|a", "ab")

    assert left_first.group() == "a"
    assert longer_first.group() == "ab"


def test_anchors_and_multiline_change_line_vs_whole_string_boundaries():
    r"""MULTILINE 只改变 ``^``/``$``；``\A``/``\Z`` 始终是整个字符串边界。"""

    text = "first\nsecond\nthird"

    assert re.findall(r"^\w+", text) == ["first"]
    assert re.findall(r"^\w+", text, re.MULTILINE) == ["first", "second", "third"]
    assert re.search(r"\Afirst", text)
    assert re.search(r"third\Z", text)
    assert re.search(r"\Asecond", text) is None

    # `$` 还可匹配末尾换行之前；严格整串验证仍优先 fullmatch。
    assert re.match(r"^value$", "value\n")
    assert re.fullmatch(r"value", "value\n") is None


def test_dotall_and_verbose_flags_change_pattern_readability_and_newlines():
    """DOTALL 让点号跨行；VERBOSE 忽略未转义空白/注释。"""

    text = "begin\nmiddle\nend"

    assert re.search(r"begin.*end", text) is None
    assert re.search(r"begin.*end", text, re.DOTALL).group() == text

    date = re.compile(
        r"""
        (?P<year>\d{4})  # four-digit year
        -
        (?P<month>\d{2})
        -
        (?P<day>\d{2})
        """,
        re.VERBOSE,
    )
    assert date.fullmatch("2026-07-14").groupdict() == {
        "year": "2026",
        "month": "07",
        "day": "14",
    }

    assert re.fullmatch(r"value[ ][#][ ]1", "value # 1", re.VERBOSE)


def test_unicode_character_classes_and_ascii_flag_have_different_domains():
    r"""str pattern 默认 Unicode；ASCII 把 ``\w \d \s`` 限制到 ASCII 集合。"""

    assert re.fullmatch(r"\w+", "café")
    assert re.fullmatch(r"\w+", "café", re.ASCII) is None
    assert re.fullmatch(r"\d+", "٣")
    assert re.fullmatch(r"\d+", "٣", re.ASCII) is None
    assert re.fullmatch(r"\s", "\u00a0")
    assert re.fullmatch(r"\s", "\u00a0", re.ASCII) is None


def test_ignorecase_is_unicode_aware_unless_combined_with_ascii():
    """Unicode IGNORECASE 的 `[a-z]` 还匹配少量非 ASCII 等价字符。"""

    kelvin_sign = "K"

    assert re.fullmatch(r"[a-z]", kelvin_sign, re.IGNORECASE)
    assert re.fullmatch(
        r"[a-z]",
        kelvin_sign,
        re.IGNORECASE | re.ASCII,
    ) is None


def test_lookahead_and_fixed_width_lookbehind_assert_without_consuming():
    """lookaround 检查上下文但不把上下文纳入 group()。"""

    assert re.search(r"\w+(?=:)", "name:value").group() == "name"
    assert re.search(r"\w+(?!:)", "name value").group() == "name"
    assert re.search(r"(?<=USD )\d+", "total USD 42").group() == "42"
    assert re.search(r"(?<!USD )\d+", "total EUR 42").group() == "42"

    with pytest.raises(re.error, match="fixed-width"):
        re.compile(r"(?<=a+)b")


def test_bytes_patterns_require_bytes_subject_and_return_bytes_groups():
    """str/bytes 两套 regex 不能混合；bytes 模式按字节工作。"""

    pattern = re.compile(br"(?P<key>[A-Z]+)=(?P<value>\d+)")
    match = pattern.fullmatch(b"PORT=8080")

    assert match.group("key") == b"PORT"
    assert match.group("value") == b"8080"

    with pytest.raises(TypeError, match="cannot use a bytes pattern"):
        pattern.search("PORT=8080")

    with pytest.raises(TypeError, match="cannot use a string pattern"):
        re.search(r"PORT", b"PORT=8080")


def test_regex_compile_error_exposes_location_metadata():
    """re.error 提供 pattern 内位置，便于配置型正则报告用户错误。"""

    broken = r"(?P<name>"

    with pytest.raises(re.error) as captured:
        re.compile(broken)

    error = captured.value
    assert error.pattern == broken
    assert isinstance(error.msg, str) and error.msg
    assert isinstance(error.pos, int)
    assert error.lineno == 1
    assert isinstance(error.colno, int)


def test_zero_length_matches_advance_so_iteration_terminates():
    """finditer 可返回空 span；引擎随后推进位置，避免永远停在同一点。"""

    matches = list(re.finditer(r"(?=.)", "ab"))

    assert [match.group() for match in matches] == ["", ""]
    assert [match.span() for match in matches] == [(0, 0), (1, 1)]


def test_nested_ambiguous_quantifiers_are_a_backtracking_risk():
    """``(a+)+`` 有大量等价分割路径；小输入正确不代表恶意长输入安全。"""

    risky = re.compile(r"^(a+)+$")
    linear = re.compile(r"^a+$")

    assert risky.fullmatch("aaaa")
    assert linear.fullmatch("aaaa")
    assert risky.fullmatch("aaaa!") is None
    assert linear.fullmatch("aaaa!") is None

    # 不在测试里放大输入。外部 pattern/文本需要长度限制、结构审计或具备超时的隔离层。
