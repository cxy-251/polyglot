"""038｜``difflib`` 序列匹配与人类可读差异示例。

``SequenceMatcher`` 寻找递归的最长连续匹配块，目标是产生“人看起来合理”的结果，
并不保证最小编辑脚本。上层的 ``Differ``、unified/context diff、``HtmlDiff`` 和
``get_close_matches`` 复用相似度思想，但各自有不同的输出契约与安全边界。

本文件用固定小序列解释 opcode 坐标、缓存、autojunk 和 newline；它不是 patch
解析器或拼写纠正质量基准。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.difflib python.difflib.SequenceMatcher
# polyglot-covers: python.difflib.set-sequences python.difflib.cache
# polyglot-covers: python.difflib.isjunk python.difflib.autojunk
# polyglot-covers: python.difflib.find_longest_match
# polyglot-covers: python.difflib.get_matching_blocks python.difflib.get_opcodes
# polyglot-covers: python.difflib.get_grouped_opcodes
# polyglot-covers: python.difflib.ratio python.difflib.quick-ratio
# polyglot-covers: python.difflib.Differ python.difflib.ndiff python.difflib.restore
# polyglot-covers: python.difflib.unified_diff python.difflib.context_diff
# polyglot-covers: python.difflib.diff_bytes python.difflib.HtmlDiff
# polyglot-covers: python.difflib.get_close_matches python.difflib.junk-helpers

import difflib
import html

import pytest


def test_sequence_matcher_requires_hashable_elements_and_indexes_sequence_b():
    """元素作为 b2j 的键必须 hashable；详细索引只围绕第二个序列建立。"""

    matcher = difflib.SequenceMatcher(
        None,
        "abXd",
        "abcd",
        autojunk=False,
    )

    assert matcher.a == "abXd"
    assert matcher.b == "abcd"
    assert matcher.bjunk == set()
    assert matcher.bpopular == set()
    assert matcher.b2j == {"a": [0], "b": [1], "c": [2], "d": [3]}

    with pytest.raises(TypeError, match="unhashable"):
        difflib.SequenceMatcher(None, [[1]], [[1]])


def test_set_seq1_reuses_b_index_while_set_seq2_and_set_seqs_rebuild_state():
    """一对多比较应固定 b 并反复 set_seq1；改变 b 才需重建昂贵的 b2j。"""

    matcher = difflib.SequenceMatcher(None, "", "abcd", autojunk=False)
    expected_b2j = dict(matcher.b2j)

    matcher.set_seq1("abXd")
    assert matcher.ratio() == 0.75
    assert matcher.b == "abcd"
    assert matcher.b2j == expected_b2j

    matcher.set_seq1("abcd")
    assert matcher.ratio() == 1.0
    assert matcher.b2j == expected_b2j

    matcher.set_seq2("wxyz")
    assert matcher.b == "wxyz"
    assert matcher.b2j == {"w": [0], "x": [1], "y": [2], "z": [3]}

    matcher.set_seqs("wxyZ", "wxyz")
    assert matcher.a == "wxyZ"
    assert matcher.b == "wxyz"
    assert matcher.ratio() == 0.75


def test_mutating_a_sequence_in_place_does_not_invalidate_matcher_caches():
    """SequenceMatcher 保存序列引用；原地修改后必须传入新对象才能可靠重建缓存。"""

    before = list("abc")
    after = list("abc")
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)

    assert matcher.ratio() == 1.0
    after[1] = "X"

    # ratio/matching_blocks 已缓存；SequenceMatcher 不监听外部 list 的原地变化。
    assert matcher.b is after
    assert matcher.ratio() == 1.0

    # set_seq2 对同一对象可直接返回，因此用快照明确表示“这是新的 b”。
    matcher.set_seq2(after.copy())
    assert matcher.ratio() == pytest.approx(2 / 3)


def test_find_longest_match_uses_earliest_tie_breaking_and_slice_bounds():
    """最长块同长时先选 a 中较早者，再选 b 中较早者；范围使用半开区间。"""

    matcher = difflib.SequenceMatcher(None, "abXab", "abYab", autojunk=False)

    first = matcher.find_longest_match()
    restricted = matcher.find_longest_match(2, 5, 2, 5)

    assert tuple(first) == (0, 0, 2)
    assert first.a == 0
    assert first.b == 0
    assert first.size == 2
    assert tuple(restricted) == (3, 3, 2)

    empty = matcher.find_longest_match(2, 3, 2, 3)
    assert tuple(empty) == (2, 2, 0)


def test_isjunk_changes_sync_points_but_adjacent_equal_junk_can_extend_a_match():
    """junk 不作为核心同步点；核心找到后，两侧相同 junk 仍可并入结果。"""

    documented = difflib.SequenceMatcher(
        lambda char: char == " ",
        " abcd",
        "abcd abcd",
        autojunk=False,
    )
    assert tuple(documented.find_longest_match()) == (1, 0, 4)
    assert documented.bjunk == {" "}

    with_adjacent_spaces = difflib.SequenceMatcher(
        lambda char: char == " ",
        " abcd ",
        "xx abcd yy",
        autojunk=False,
    )
    match = with_adjacent_spaces.find_longest_match()

    assert tuple(match) == (0, 2, 6)
    assert with_adjacent_spaces.a[match.a : match.a + match.size] == " abcd "


def test_matching_blocks_are_ordered_and_end_with_one_zero_size_sentinel():
    """sentinel 让消费方无需为序列末尾另写分支；它是唯一 size 为零的块。"""

    matcher = difflib.SequenceMatcher(None, "abxcd", "abcd", autojunk=False)
    blocks = matcher.get_matching_blocks()

    assert [tuple(block) for block in blocks] == [
        (0, 0, 2),
        (3, 2, 2),
        (5, 4, 0),
    ]
    assert blocks[-1].size == 0
    assert all(block.size > 0 for block in blocks[:-1])

    for current, following in zip(blocks, blocks[1:]):
        assert current.a + current.size <= following.a
        assert current.b + current.size <= following.b


def test_opcodes_describe_contiguous_half_open_ranges_that_rebuild_target():
    """每个 opcode 给出 a/b 的半开坐标；相邻 opcode 在两边都无缝衔接。"""

    source = "qabxcd"
    target = "abycdf"
    matcher = difflib.SequenceMatcher(None, source, target, autojunk=False)
    opcodes = matcher.get_opcodes()

    assert opcodes == [
        ("delete", 0, 1, 0, 0),
        ("equal", 1, 3, 0, 2),
        ("replace", 3, 4, 2, 3),
        ("equal", 4, 6, 3, 5),
        ("insert", 6, 6, 5, 6),
    ]

    rebuilt = []
    previous_i2 = previous_j2 = 0
    for tag, i1, i2, j1, j2 in opcodes:
        assert (i1, j1) == (previous_i2, previous_j2)
        if tag in {"equal", "replace", "insert"}:
            rebuilt.append(target[j1:j2])
        if tag == "equal":
            assert source[i1:i2] == target[j1:j2]
        if tag == "delete":
            assert j1 == j2
        if tag == "insert":
            assert i1 == i2
        previous_i2, previous_j2 = i2, j2

    assert "".join(rebuilt) == target


def test_grouped_opcodes_trim_long_equal_regions_to_requested_context():
    """相距很远的修改分成多个 group；每组边缘只保留 n 个 equal 元素。"""

    source = list("0123456789abcdefghij")
    target = source.copy()
    target[2] = "X"
    target[17] = "Y"

    matcher = difflib.SequenceMatcher(None, source, target, autojunk=False)
    groups = list(matcher.get_grouped_opcodes(n=1))

    assert len(groups) == 2
    assert groups[0] == [
        ("equal", 1, 2, 1, 2),
        ("replace", 2, 3, 2, 3),
        ("equal", 3, 4, 3, 4),
    ]
    assert groups[1] == [
        ("equal", 16, 17, 16, 17),
        ("replace", 17, 18, 17, 18),
        ("equal", 18, 19, 18, 19),
    ]


def test_ratio_approximations_are_upper_bounds_and_ratio_can_depend_on_order():
    """quick 方法用于廉价筛选；最终 ratio 也不是对称距离或编辑距离。"""

    matcher = difflib.SequenceMatcher(None, "abcd", "bcde", autojunk=False)

    assert matcher.ratio() == 0.75
    assert matcher.quick_ratio() == 0.75
    assert matcher.real_quick_ratio() == 1.0
    assert matcher.ratio() <= matcher.quick_ratio() <= matcher.real_quick_ratio()

    assert difflib.SequenceMatcher(None, "tide", "diet").ratio() == 0.25
    assert difflib.SequenceMatcher(None, "diet", "tide").ratio() == 0.5


def test_autojunk_marks_high_frequency_items_only_for_long_second_sequences():
    """b 至少 200 项且某元素的重复项超过 1% 时，默认启发式把它标为 popular。"""

    repeated = ["anchor"] + ["x"] * 199
    query = ["x"] * 50

    automatic = difflib.SequenceMatcher(None, query, repeated)
    explicit = difflib.SequenceMatcher(None, query, repeated, autojunk=False)

    assert len(repeated) == 200
    assert automatic.bpopular == {"x"}
    assert "x" not in automatic.b2j
    assert automatic.ratio() == 0.0

    assert explicit.bpopular == set()
    assert explicit.b2j["x"] == list(range(1, 200))
    assert explicit.ratio() == 0.4

    # 对重复 token 有业务含义的长序列，应评估并显式选择 autojunk。


def test_ndiff_and_differ_emit_human_readable_lines_and_restore_both_inputs():
    """问号行只标注行内变化，不属于任一输入；restore 会忽略它们并去掉两字符前缀。"""

    before = ["cat\n", "same\n"]
    after = ["cut\n", "same\n", "new\n"]
    delta = list(difflib.ndiff(before, after))

    assert delta[0] == "- cat\n"
    assert delta[1] == "?  ^\n"
    assert delta[2] == "+ cut\n"
    assert delta[3] == "?  ^\n"
    assert "  same\n" in delta
    assert "+ new\n" in delta
    assert all(line[2:] not in before + after for line in delta if line.startswith("? "))

    differ_delta = list(
        difflib.Differ(charjunk=difflib.IS_CHARACTER_JUNK).compare(before, after)
    )
    assert differ_delta == delta
    assert list(difflib.restore(delta, 1)) == before
    assert list(difflib.restore(delta, 2)) == after

    with pytest.raises(ValueError, match="unknown delta choice"):
        list(difflib.restore(delta, 3))


def test_unified_diff_includes_file_metadata_hunks_and_configured_context():
    """输入行含 newline 时，默认 control line 也含 newline，可直接交给 writelines。"""

    before = ["alpha\n", "old\n", "omega\n"]
    after = ["alpha\n", "new\n", "omega\n"]

    delta = list(
        difflib.unified_diff(
            before,
            after,
            fromfile="before.txt",
            tofile="after.txt",
            fromfiledate="2026-07-13",
            tofiledate="2026-07-14",
            n=1,
        )
    )

    assert delta == [
        "--- before.txt\t2026-07-13\n",
        "+++ after.txt\t2026-07-14\n",
        "@@ -1,3 +1,3 @@\n",
        " alpha\n",
        "-old\n",
        "+new\n",
        " omega\n",
    ]


def test_context_diff_uses_separate_before_after_sections():
    """context diff 的修改以 before/after 两段呈现，``! `` 标记两边被替换的行。"""

    before = ["alpha\n", "old\n", "omega\n"]
    after = ["alpha\n", "new\n", "omega\n"]
    delta = list(
        difflib.context_diff(
            before,
            after,
            fromfile="before.txt",
            tofile="after.txt",
            n=1,
        )
    )

    assert delta[:3] == [
        "*** before.txt\n",
        "--- after.txt\n",
        "***************\n",
    ]
    assert "*** 1,3 ****\n" in delta
    assert "--- 1,3 ----\n" in delta
    assert "! old\n" in delta
    assert "! new\n" in delta


def test_lineterm_must_match_inputs_that_do_not_carry_newlines():
    """无 newline 输入若保留默认 lineterm，会让 control line 与数据行采用混合契约。"""

    before = ["old"]
    after = ["new"]

    mixed = list(
        difflib.unified_diff(before, after, fromfile="before", tofile="after")
    )
    uniform = list(
        difflib.unified_diff(
            before,
            after,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )

    assert mixed[:3] == ["--- before\n", "+++ after\n", "@@ -1 +1 @@\n"]
    assert mixed[-2:] == ["-old", "+new"]
    assert uniform == ["--- before", "+++ after", "@@ -1 +1 @@", "-old", "+new"]
    assert all(not line.endswith("\n") for line in uniform)


def test_diff_bytes_preserves_unknown_bytes_through_a_text_diff_function():
    """diff_bytes 用无损代理转换调用文本 diff，再把未知编码的内容和元数据还原为 bytes。"""

    before = [b"\xffold\n"]
    after = [b"\xffnew\n"]
    delta = list(
        difflib.diff_bytes(
            difflib.unified_diff,
            before,
            after,
            fromfile=b"before-\xff",
            tofile=b"after-\xfe",
            n=0,
        )
    )

    assert all(isinstance(line, bytes) for line in delta)
    assert delta[0] == b"--- before-\xff\n"
    assert delta[1] == b"+++ after-\xfe\n"
    assert b"-\xffold\n" in delta
    assert b"+\xffnew\n" in delta


def test_html_diff_escapes_file_lines_but_description_fields_are_raw_html():
    """fromdesc/todesc 是调用方提供的 HTML；不可信描述必须先显式 escape。"""

    formatter = difflib.HtmlDiff()
    unsafe_description = "<b>FROM</b>"
    raw_table = formatter.make_table(
        ["<old>\n"],
        ["<new>\n"],
        fromdesc=unsafe_description,
        todesc="TO",
    )

    assert '<table class="diff"' in raw_table
    assert unsafe_description in raw_table
    assert "<old>" not in raw_table
    assert "&lt;" in raw_table and "&gt;" in raw_table

    safe_description = html.escape(unsafe_description)
    full_page = formatter.make_file(
        ["old\n"],
        ["new\n"],
        fromdesc=safe_description,
        todesc="TO",
        charset="utf-8",
    )
    assert safe_description in full_page
    assert "charset=utf-8" in full_page
    assert "<html" in full_page


def test_get_close_matches_ranks_candidates_and_validates_search_controls():
    """结果按相似度降序且最多 n 个；cutoff 是启发式门槛，不是语言学置信度。"""

    possibilities = ["ape", "apple", "peach", "puppy"]

    assert difflib.get_close_matches("appel", possibilities) == ["apple", "ape"]
    assert difflib.get_close_matches("appel", possibilities, n=1) == ["apple"]
    assert difflib.get_close_matches(
        "appel",
        possibilities,
        cutoff=0.9,
    ) == []

    with pytest.raises(ValueError, match="n must be"):
        difflib.get_close_matches("appel", possibilities, n=0)
    with pytest.raises(ValueError, match="cutoff"):
        difflib.get_close_matches("appel", possibilities, cutoff=1.1)


def test_junk_helpers_choose_sync_noise_without_erasing_real_differences():
    """内置 junk predicate 只影响同步点选择；Differ 输出仍能恢复两个完整输入。"""

    assert difflib.IS_LINE_JUNK("\n") is True
    assert difflib.IS_LINE_JUNK("  #  \n") is True
    assert difflib.IS_LINE_JUNK("##\n") is False

    assert difflib.IS_CHARACTER_JUNK(" ") is True
    assert difflib.IS_CHARACTER_JUNK("\t") is True
    assert difflib.IS_CHARACTER_JUNK("\n") is False
    assert difflib.IS_CHARACTER_JUNK("x") is False

    before = ["#\n", "old\n"]
    after = ["#\n", "new\n"]
    delta = list(
        difflib.ndiff(
            before,
            after,
            linejunk=difflib.IS_LINE_JUNK,
            charjunk=difflib.IS_CHARACTER_JUNK,
        )
    )

    assert list(difflib.restore(delta, 1)) == before
    assert list(difflib.restore(delta, 2)) == after
