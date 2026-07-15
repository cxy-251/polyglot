"""039｜``stringprep`` 的 RFC 3454 映射、禁止字符与 bidi 表示例。

``stringprep`` 只暴露 RFC 3454 的 table primitive：set table 变成单字符 predicate，
mapping table 变成单字符到字符串的函数。模块没有通用 ``prepare()``，因为具体协议
必须选择映射、正规化、禁止表、未分配字符策略和 bidi 规则，组成自己的 profile。

RFC 3454 与这里的表固定在 Unicode 3.2，且该 RFC 已由 PRECIS 框架取代。下面的小型
profile 只用来演示 map → normalize → prohibit → bidi 的阶段关系，不冒充 Nameprep、
SASLprep、IDNA 2008 或任何可部署协议。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.stringprep python.stringprep.unicode-3.2
# polyglot-covers: python.stringprep.table-a1 python.stringprep.table-b1
# polyglot-covers: python.stringprep.table-b2 python.stringprep.table-b3
# polyglot-covers: python.stringprep.table-c1 python.stringprep.table-c2
# polyglot-covers: python.stringprep.table-c3 python.stringprep.table-c4
# polyglot-covers: python.stringprep.table-c5 python.stringprep.table-c6
# polyglot-covers: python.stringprep.table-c7 python.stringprep.table-c8
# polyglot-covers: python.stringprep.table-c9
# polyglot-covers: python.stringprep.table-d1 python.stringprep.table-d2
# polyglot-covers: python.stringprep.profile-order python.stringprep.bidi-rule

import stringprep
import unicodedata

import pytest


_TABLE_FUNCTIONS = {
    "in_table_a1",
    "in_table_b1",
    "map_table_b2",
    "map_table_b3",
    "in_table_c11",
    "in_table_c12",
    "in_table_c11_c12",
    "in_table_c21",
    "in_table_c22",
    "in_table_c21_c22",
    "in_table_c3",
    "in_table_c4",
    "in_table_c5",
    "in_table_c6",
    "in_table_c7",
    "in_table_c8",
    "in_table_c9",
    "in_table_d1",
    "in_table_d2",
}

_TEACHING_PROHIBITED_TABLES = (
    ("C.1.1 ASCII space", stringprep.in_table_c11),
    ("C.1.2 non-ASCII space", stringprep.in_table_c12),
    ("C.2.1 ASCII control", stringprep.in_table_c21),
    ("C.2.2 non-ASCII control", stringprep.in_table_c22),
    ("C.3 private use", stringprep.in_table_c3),
    ("C.4 non-character", stringprep.in_table_c4),
    ("C.5 surrogate", stringprep.in_table_c5),
    ("C.6 inappropriate plain text", stringprep.in_table_c6),
    ("C.7 canonical representation", stringprep.in_table_c7),
    ("C.8 display/deprecated", stringprep.in_table_c8),
    ("C.9 tagging", stringprep.in_table_c9),
)


class _TeachingStringprepError(ValueError):
    """仅供本测试文件的小型教学 profile 使用。"""


def _teaching_prepare(value):
    """演示 RFC 阶段顺序；表选择和错误策略不是任何已注册 profile。"""

    mapped_parts = []
    for character in value:
        if stringprep.in_table_b1(character):
            continue
        mapped_parts.append(stringprep.map_table_b2(character))

    # 必须使用与 Stringprep 相同的 Unicode 3.2 数据，而不是运行时最新 UCD。
    normalized = unicodedata.ucd_3_2_0.normalize("NFKC", "".join(mapped_parts))

    # 本教学 profile 选择拒绝 A.1；真实 profile 需区分 stored string/query 等策略。
    for character in normalized:
        if stringprep.in_table_a1(character):
            raise _TeachingStringprepError(
                f"unassigned in Unicode 3.2: U+{ord(character):04X}"
            )
        for table_name, predicate in _TEACHING_PROHIBITED_TABLES:
            if predicate(character):
                raise _TeachingStringprepError(
                    f"prohibited by {table_name}: U+{ord(character):04X}"
                )

    has_randal = any(stringprep.in_table_d1(char) for char in normalized)
    if has_randal:
        if any(stringprep.in_table_d2(char) for char in normalized):
            raise _TeachingStringprepError("RandALCat and LCat must not mix")
        if not (
            stringprep.in_table_d1(normalized[0])
            and stringprep.in_table_d1(normalized[-1])
        ):
            raise _TeachingStringprepError(
                "a RandALCat string must start and end with RandALCat"
            )

    return normalized


def test_module_exposes_tables_but_deliberately_has_no_generic_prepare_function():
    """Python 模块提供表积木；协议 profile 才定义完整字符串处理语义。"""

    assert _TABLE_FUNCTIONS <= set(dir(stringprep))
    assert len(_TABLE_FUNCTIONS) == 19
    assert not hasattr(stringprep, "prepare")


def test_table_a1_uses_unicode_3_2_assignment_status_not_current_unicode():
    """U+0221 在 Unicode 3.2 尚未分配，现代 UCD 已把它定义为小写拉丁字母。"""

    added_after_3_2 = "\u0221"
    assigned_in_3_2 = "\u0222"

    assert unicodedata.ucd_3_2_0.unidata_version == "3.2.0"
    assert unicodedata.ucd_3_2_0.category(added_after_3_2) == "Cn"
    assert unicodedata.category(added_after_3_2) == "Ll"
    assert stringprep.in_table_a1(added_after_3_2) is True
    assert stringprep.in_table_a1(assigned_in_3_2) is False

    # 不能用当前 unicodedata.category() 代替 RFC 的 A.1 快照。


def test_table_b1_marks_characters_that_a_profile_can_map_to_nothing():
    """B.1 是 membership table；命中表示 profile 映射阶段应删除该字符。"""

    assert stringprep.in_table_b1("\u00ad") is True  # SOFT HYPHEN
    assert stringprep.in_table_b1("\u200b") is True  # ZERO WIDTH SPACE
    assert stringprep.in_table_b1("\ufeff") is True  # ZERO WIDTH NO-BREAK SPACE
    assert stringprep.in_table_b1("\u00ae") is False

    original = "co\u00adoperate"
    mapped = "".join(char for char in original if not stringprep.in_table_b1(char))
    assert mapped == "cooperate"


def test_b2_and_b3_mapping_functions_can_expand_one_character_to_many():
    """mapping 返回 str 而非单个 code point；case folding 可能改变长度。"""

    for mapper in (stringprep.map_table_b2, stringprep.map_table_b3):
        assert mapper("A") == "a"
        assert mapper("a") == "a"
        assert mapper("ß") == "ss"
        assert mapper("\u0130") == "i\u0307"  # LATIN CAPITAL I WITH DOT ABOVE

    assert len(stringprep.map_table_b2("ß")) == 2


def test_b2_mapping_is_for_an_nfkc_profile_but_does_not_replace_normalization():
    """B.2 内部保证 folding/NFKC 稳定性；profile 仍要在映射后单独执行 NFKC。"""

    circled_one = "①"
    mapped = stringprep.map_table_b2(circled_one)

    # 该字符本身没有 case mapping，所以 table 函数仍返回原字符。
    assert mapped == circled_one
    assert unicodedata.ucd_3_2_0.normalize("NFKC", mapped) == "1"

    # B.3 面向不做 normalization 的 profile；选 B.2/B.3 不能脱离目标 RFC。
    assert stringprep.map_table_b3(circled_one) == circled_one


def test_c1_tables_separate_ascii_and_non_ascii_space_then_offer_a_union():
    """C.1.1 与 C.1.2 是不相交子表；联合 predicate 同时覆盖二者。"""

    ascii_space = " "
    no_break_space = "\u00a0"

    assert stringprep.in_table_c11(ascii_space) is True
    assert stringprep.in_table_c12(ascii_space) is False
    assert stringprep.in_table_c11_c12(ascii_space) is True

    assert stringprep.in_table_c11(no_break_space) is False
    assert stringprep.in_table_c12(no_break_space) is True
    assert stringprep.in_table_c11_c12(no_break_space) is True
    assert stringprep.in_table_c11_c12("A") is False


def test_c2_tables_cover_ascii_controls_and_non_ascii_control_like_values():
    """C.2.2 还含若干非 Cc code point，例如 LINE SEPARATOR。"""

    ascii_unit_separator = "\x1f"
    non_ascii_control = "\u009f"
    line_separator = "\u2028"

    assert stringprep.in_table_c21(ascii_unit_separator) is True
    assert stringprep.in_table_c22(ascii_unit_separator) is False
    assert stringprep.in_table_c21_c22(ascii_unit_separator) is True

    assert stringprep.in_table_c21(non_ascii_control) is False
    assert stringprep.in_table_c22(non_ascii_control) is True
    assert stringprep.in_table_c21_c22(non_ascii_control) is True

    assert unicodedata.ucd_3_2_0.category(line_separator) == "Zl"
    assert stringprep.in_table_c22(line_separator) is True
    assert stringprep.in_table_c21_c22("A") is False


def test_c3_c4_and_c5_distinguish_private_noncharacter_and_surrogate_values():
    """Python str 可持有这些 code point；是否拒绝由 profile 的 prohibited 表决定。"""

    private_use = "\ue000"
    noncharacter = "\ufdd0"
    plane_end_noncharacter = "\U0001fffe"
    surrogate = "\ud800"

    assert stringprep.in_table_c3(private_use) is True
    assert stringprep.in_table_c3("\uf900") is False

    assert stringprep.in_table_c4(noncharacter) is True
    assert stringprep.in_table_c4(plane_end_noncharacter) is True
    assert stringprep.in_table_c4("A") is False

    assert stringprep.in_table_c5(surrogate) is True
    assert stringprep.in_table_c5("\ud7ff") is False

    # surrogate 只在内存中分类；本例不把它编码或写到终端/文件。


def test_c6_through_c9_cover_special_text_display_and_tagging_ranges():
    """后四张禁止表表达不同理由；profile 必须按自身规范选择，而非凭感觉合并。"""

    assert stringprep.in_table_c6("\ufff9") is True  # INTERLINEAR ANNOTATION ANCHOR
    assert stringprep.in_table_c6("\ufffe") is False

    assert stringprep.in_table_c7("\u2ff0") is True  # IDEOGRAPHIC DESCRIPTION
    assert stringprep.in_table_c7("\u2ffc") is False

    assert stringprep.in_table_c8("\u0340") is True  # deprecated combining mark
    assert stringprep.in_table_c8("\u202e") is True  # RIGHT-TO-LEFT OVERRIDE
    assert stringprep.in_table_c8("\u0342") is False

    assert stringprep.in_table_c9("\U000e0001") is True  # LANGUAGE TAG
    assert stringprep.in_table_c9("\U000e0020") is True  # TAG SPACE
    assert stringprep.in_table_c9("\U000e0002") is False


def test_d1_and_d2_classify_randalcat_and_lcat_using_unicode_3_2_bidi_data():
    """D.1 是 R/AL，D.2 是 L；数字/combining mark 不会因此自动落入任一表。"""

    hebrew_alef = "\u05d0"
    arabic_alef = "\u0627"

    assert stringprep.in_table_d1(hebrew_alef) is True
    assert stringprep.in_table_d1(arabic_alef) is True
    assert stringprep.in_table_d1("\u05bf") is False

    assert stringprep.in_table_d2("A") is True
    assert stringprep.in_table_d2("α") is True
    assert stringprep.in_table_d2("1") is False
    assert stringprep.in_table_d2(hebrew_alef) is False

    # 表可能重叠：RIGHT-TO-LEFT MARK 同时属于显示控制 C.8 和 RandALCat D.1。
    assert stringprep.in_table_c8("\u200f") is True
    assert stringprep.in_table_d1("\u200f") is True


def test_table_functions_expect_one_character_but_are_not_uniform_validators():
    """调用方应自己逐字符迭代；不要依赖所有生成函数对错误长度给出同一种异常。"""

    assert isinstance(stringprep.in_table_c3("A"), bool)
    assert isinstance(stringprep.in_table_d1("A"), bool)

    with pytest.raises(TypeError):
        stringprep.in_table_b1("AB")
    with pytest.raises(TypeError):
        stringprep.map_table_b3("AB")

    # C.1.1 恰好只做字符串相等比较，因此多字符输入返回 False；这不是批量扫描。
    assert stringprep.in_table_c11("AB") is False


def test_teaching_profile_maps_removes_and_normalizes_before_prohibition():
    """B.1 删除和 B.2 扩展发生在 NFKC/禁止检查之前，输出长度可以增减。"""

    assert _teaching_prepare("Straße\u00ad") == "strasse"
    assert _teaching_prepare("\u2121") == "tel"  # TELEPHONE SIGN 经 B.2 folding。

    # NBSP 先经 NFKC 变成 ASCII space，随后才被本 profile 选择的 C.1.1 拒绝。
    with pytest.raises(
        _TeachingStringprepError,
        match=r"C\.1\.1 ASCII space: U\+0020",
    ):
        _teaching_prepare("\u00a0")

    with pytest.raises(
        _TeachingStringprepError,
        match=r"C\.3 private use: U\+E000",
    ):
        _teaching_prepare("name\ue000")


def test_teaching_profile_checks_unassigned_characters_against_unicode_3_2():
    """现代已分配不改变本 RFC 的 A.1 判断；真实 profile 还需定义 query/stored 策略。"""

    with pytest.raises(
        _TeachingStringprepError,
        match=r"unassigned in Unicode 3\.2: U\+0221",
    ):
        _teaching_prepare("ok\u0221")


def test_teaching_profile_enforces_bidi_mixing_and_first_last_rules():
    """只要出现 RandALCat，就不能含 LCat，并且首尾都必须属于 RandALCat。"""

    assert _teaching_prepare("אב") == "אב"
    assert _teaching_prepare("א1ב") == "א1ב"  # EN 数字不是 D.2 LCat。

    with pytest.raises(
        _TeachingStringprepError,
        match="RandALCat and LCat must not mix",
    ):
        _teaching_prepare("אaב")

    with pytest.raises(
        _TeachingStringprepError,
        match="start and end with RandALCat",
    ):
        _teaching_prepare("א1")
