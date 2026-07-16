"""021｜``str`` 的 Unicode 文本、序列操作与处理工作流示例。

str 是不可变的 Unicode code point 序列。它同时提供序列接口和大量文本方法，
但不会替调用者解决 grapheme cluster、显示宽度、语言学分词或字节编码协议。

通用订阅/切片协议和格式化特殊方法已在 005、014 展示；本文件聚焦内置 str 的
实际行为。内容基于 Python 3.10 Text Sequence Type、String Methods 和 Unicode
HOWTO。
"""

# polyglot-covers: python.type.str python.literal.string python.literal.raw-string
# polyglot-covers: python.builtin.str python.builtin.ord python.builtin.chr
# polyglot-covers: python.str.find python.str.rfind python.str.index python.str.rindex
# polyglot-covers: python.str.count python.str.expandtabs
# polyglot-covers: python.str.startswith python.str.endswith
# polyglot-covers: python.str.split python.str.rsplit python.str.splitlines
# polyglot-covers: python.str.partition python.str.rpartition python.str.join
# polyglot-covers: python.str.strip python.str.removeprefix python.str.removesuffix
# polyglot-covers: python.str.replace python.str.translate python.str.maketrans
# polyglot-covers: python.str.casefold python.str.character-classification
# polyglot-covers: python.str.alignment python.str.encode python.str.format

import keyword
import unicodedata

import pytest


def test_string_literals_support_quotes_escapes_raw_text_and_concatenation():
    """不同字面量形式解决定界、换行、转义和长常量拼接问题。"""

    single = 'He said "hello".'
    double = "It's ready."
    multiline = """first
second"""
    raw_path = r"C:\new\tests"
    adjacent = (
        "a long literal can be "
        "split across source lines"
    )

    assert single == 'He said "hello".'
    assert double == "It's ready."
    assert multiline.splitlines() == ["first", "second"]
    assert raw_path == "C:\\new\\tests"
    assert adjacent == "a long literal can be split across source lines"

    # 相邻字面量拼接发生在编译期，只适合源代码中的常量；运行时变量要用 + 或 join。


def test_raw_string_still_cannot_end_with_one_unpaired_backslash():
    """raw 关闭大多数转义解释，但引号仍必须能被词法分析器正确识别。"""

    invalid_source = "value = r'ends with " + "\\" + "'"

    with pytest.raises(SyntaxError):
        compile(invalid_source, "<raw-string>", "exec")

    assert r"ends with \\" == "ends with \\\\"

    # Windows 路径末尾需要两个反斜杠、普通字符串转义，或用 pathlib 组合路径；
    # raw string 不是“任意内容都原样合法”的独立字符串语法。


def test_str_is_a_sequence_of_unicode_code_points():
    """len、索引、ord 和 chr 都按 Unicode code point 工作。"""

    text = "Aé😀"

    assert len(text) == 3
    assert list(text) == ["A", "é", "😀"]
    assert text[1] == "é"
    assert ord("é") == 0xE9
    assert chr(0x1F600) == "😀"

    with pytest.raises(TypeError):
        ord("AB")


def test_code_point_count_is_not_user_perceived_character_or_display_width():
    """组合字符和 ZWJ 序列能用多个 code point 表示一个可见字符。"""

    composed = "é"
    decomposed = "e\u0301"
    technologist = "👩\u200d💻"

    assert len(composed) == 1
    assert len(decomposed) == 2
    assert composed != decomposed
    assert unicodedata.normalize("NFC", decomposed) == composed
    assert len(technologist) == 3

    # str 不承诺终端列宽或 grapheme cluster 数。UI 截断、光标移动等需求需要使用
    # 理解 Unicode grapheme/显示宽度的专用层，不能直接把 len 当屏幕字符数。


def test_string_indexing_slicing_and_membership_follow_sequence_rules():
    """单字符索引仍返回 str，切片产生新值，字符串本身不能原地改写。"""

    text = "python"

    assert text[0] == "p"
    assert type(text[0]) is str
    assert text[-1] == "n"
    assert text[1:5:2] == "yh"
    assert text[::-1] == "nohtyp"
    assert "tho" in text

    with pytest.raises(TypeError):
        text[0] = "P"

    # `[::-1]` 反转 code point；包含组合字符或 ZWJ 的用户文本可能被拆坏。


def test_search_methods_choose_between_sentinel_exception_and_counts():
    """find 返回 -1，index 抛 ValueError；count 统计不重叠出现次数。"""

    text = "banana"

    assert text.find("na") == 2
    assert text.rfind("na") == 4
    assert text.find("missing") == -1
    assert text.index("na", 3) == 4
    assert text.rindex("na") == 4
    assert text.count("an") == 2
    assert "aaaa".count("aa") == 2

    with pytest.raises(ValueError):
        text.index("missing")

    with pytest.raises(ValueError):
        text.rindex("missing")

    # 只需判断存在性时优先使用 `needle in text`；它比拿 find 结果与 -1 比更直白。


def test_prefix_and_suffix_checks_accept_one_value_or_a_tuple():
    """startswith/endswith 表达边界判断，不需要先切片。"""

    url = "https://example.test/report.csv"

    assert url.startswith(("https://", "http://"))
    assert url.endswith((".csv", ".tsv"))
    assert url.startswith("example", 8)
    assert not url.endswith("report")


def test_split_without_separator_collapses_runs_of_whitespace():
    """无参数 split 是面向空白字段的特殊算法，不等于 split(' ')。"""

    text = "  alpha\t beta\n\ngamma  "

    assert text.split() == ["alpha", "beta", "gamma"]
    assert "".split() == []
    assert " a  b ".split(" ") == ["", "a", "", "b", ""]
    assert "".split(",") == [""]

    # 显式分隔符不会折叠连续出现，也保留边缘空字段；解析表格时两种行为不能互换。


def test_split_rsplit_and_maxsplit_control_which_boundaries_are_consumed():
    """maxsplit 限制切割次数，rsplit 从右侧优先寻找边界。"""

    path = "team:project:item:42"

    assert path.split(":", 2) == ["team", "project", "item:42"]
    assert path.rsplit(":", 1) == ["team:project:item", "42"]

    key, value = "content-type: text/plain".split(":", 1)
    assert key == "content-type"
    assert value.strip() == "text/plain"


def test_splitlines_understands_line_boundaries_and_optional_endings():
    """splitlines 识别多种行边界，并可选择是否保留终止符。"""

    text = "first\r\nsecond\n"

    assert text.splitlines() == ["first", "second"]
    assert text.splitlines(keepends=True) == ["first\r\n", "second\n"]
    assert "".splitlines() == []

    # 与 split("\n") 不同，末尾单个行边界不会额外产生一个空行字段。
    assert text.split("\n") == ["first\r", "second", ""]


def test_expandtabs_uses_tab_stops_and_resets_the_column_after_a_newline():
    """tabsize 表示制表位间隔，不是给每个 tab 固定替换若干空格。"""

    assert "ab\tc".expandtabs(4) == "ab  c"
    assert "a\tbc".expandtabs(4) == "a   bc"
    assert "a\n\tb".expandtabs(4) == "a\n    b"

    # 替换数量取决于 tab 前的当前列；换行后列位置重新从零计算。


def test_partition_always_returns_three_parts_for_protocol_like_text():
    """partition 适合只拆第一处边界，并把“未找到”编码在固定结构中。"""

    text = "name=alice=admin"

    assert text.partition("=") == ("name", "=", "alice=admin")
    assert text.rpartition("=") == ("name=alice", "=", "admin")
    assert "name".partition("=") == ("name", "", "")
    assert "name".rpartition("=") == ("", "", "name")

    # 固定三元组便于解包；必须检查中间 separator 是否为空，不能把未找到误当空值。


def test_join_places_one_separator_between_existing_strings():
    """分隔符是 join 的接收者，输入元素必须已经是 str。"""

    assert ", ".join(["red", "green", "blue"]) == "red, green, blue"
    assert ", ".join([]) == ""
    assert ", ".join(["only"]) == "only"
    assert "".join(["py", "thon"]) == "python"

    with pytest.raises(TypeError):
        ",".join(["items", 3])

    # join 不隐式 str(3)，因为静默转换会掩盖数据边界；应在上游显式格式化元素。


def test_strip_removes_a_set_of_edge_characters_not_a_literal_token():
    """strip 参数中的每个字符都可反复从两端移除。"""

    assert " \t ready \n".strip() == "ready"
    assert "www.example.com".strip("cmowz.") == "example"
    assert "xyxpayloadxy".lstrip("xy") == "payloadxy"
    assert "xyxpayloadxy".rstrip("xy") == "xyxpayload"

    # `strip("prefix")` 不是删除字符串 prefix；参数顺序和重复次数都没有词语语义。


def test_remove_prefix_and_suffix_only_remove_one_exact_boundary_token():
    """removeprefix/removesuffix 明确表达固定标记清理。"""

    name = "test_report.csv"

    assert name.removeprefix("test_") == "report.csv"
    assert name.removesuffix(".csv") == "test_report"
    assert name.removeprefix("report_") == name
    assert "test_test_item".removeprefix("test_") == "test_item"

    # 一次只删一个完全匹配项；需要循环剥离时应显式写循环并确定终止规则。


def test_replace_and_translate_handle_tokens_and_character_maps():
    """replace 面向子串，translate 用单次字符映射完成替换或删除。"""

    assert "banana".replace("a", "o", 2) == "bonona"

    table = str.maketrans({"&": " and ", "\u00a0": " ", "!": None})
    normalized = "tea\u00a0& coffee!".translate(table)

    assert normalized == "tea  and  coffee"

    # translate 的映射键最终是 Unicode ordinal，值可为 ordinal、str 或 None；
    # maketrans 让常见的单字符键更易读。它不会自动合并映射后产生的重复空格。


def test_casefold_is_stronger_than_lower_for_caseless_matching():
    """casefold 为无大小写比较做更积极的 Unicode 规范化。"""

    street = "Straße"

    assert street.lower() == "straße"
    assert street.casefold() == "strasse"
    assert street.casefold() == "STRASSE".casefold()
    assert "ß".upper() == "SS"

    # 大小写转换可能改变长度，因此 swapcase 两次也不保证还原原字符串。
    assert street.swapcase().swapcase() == "Strasse"
    assert street.swapcase().swapcase() != street


def test_title_and_capitalize_are_simple_character_algorithms():
    """title 不是完整的人名/自然语言标题规则。"""

    assert "hello WORLD".capitalize() == "Hello world"
    assert "hello WORLD".title() == "Hello World"
    assert "they're bill's friends".title() == "They'Re Bill'S Friends"
    assert "PyThOn".swapcase() == "pYtHoN"

    # 撇号会被算法当作单词边界；面向自然语言的标题格式需要领域规则。


def test_character_classification_methods_answer_different_questions():
    """decimal、digit、numeric 的集合逐步扩大，不能互相替代。"""

    ascii_digits = "42"
    superscript = "²"
    roman_numeral = "Ⅻ"

    assert ascii_digits.isdecimal() and ascii_digits.isdigit()
    assert ascii_digits.isnumeric()
    assert not superscript.isdecimal() and superscript.isdigit()
    assert superscript.isnumeric()
    assert not roman_numeral.isdecimal() and not roman_numeral.isdigit()
    assert roman_numeral.isnumeric()

    assert "中文".isalpha()
    assert "café42".isalnum()
    assert "\u00a0".isspace()
    assert "plain ASCII".isascii()
    assert not "café".isascii()
    assert "abc".islower() and not "123".islower()
    assert "ABC".isupper() and not "123".isupper()
    assert "Hello World".istitle()
    assert "visible text".isprintable()
    assert not "line\nbreak".isprintable()

    # 分类检查单个字符集合，不验证 int() 的正负号、base、空白等完整语法。
    with pytest.raises(ValueError):
        int(superscript)


def test_isidentifier_does_not_exclude_reserved_keywords():
    """词法上可作标识符的文本仍可能是 Python 保留关键字。"""

    assert "变量_1".isidentifier()
    assert "class".isidentifier()
    assert keyword.iskeyword("class")
    assert not "two words".isidentifier()
    assert not "2fast".isidentifier()


def test_alignment_and_zfill_make_padding_rules_visible():
    """对齐方法填充到最小宽度；zfill 会把符号保留在零之前。"""

    assert "cat".center(7, "-") == "--cat--"
    assert "cat".ljust(5, ".") == "cat.."
    assert "cat".rjust(5, ".") == "..cat"
    assert "42".zfill(5) == "00042"
    assert "-42".zfill(5) == "-0042"
    assert "already long".center(5) == "already long"

    with pytest.raises(TypeError):
        "cat".center(7, "ab")


def test_encode_makes_the_unicode_to_bytes_boundary_explicit():
    """str 保存文本；encode 按明确字符编码产生协议/文件所需 bytes。"""

    text = "咖啡"
    encoded = text.encode("utf-8")

    assert encoded == b"\xe5\x92\x96\xe5\x95\xa1"
    assert encoded.decode("utf-8") == text
    assert len(text) == 2
    assert len(encoded) == 6

    # code point 数与 UTF-8 字节数是两个不同维度，网络长度字段必须基于编码后 bytes。


def test_encode_error_policy_must_be_an_explicit_data_loss_decision():
    """严格模式拒绝不可编码字符；其他策略会替换或丢弃信息。"""

    text = "café"

    with pytest.raises(UnicodeEncodeError):
        text.encode("ascii")

    assert text.encode("ascii", errors="ignore") == b"caf"
    assert text.encode("ascii", errors="replace") == b"caf?"
    assert text.encode("ascii", errors="xmlcharrefreplace") == b"caf&#233;"

    # ignore 不应作为修复乱码的默认手段；它让失败消失的同时不可逆地删除数据。


def test_str_and_bytes_do_not_mix_implicitly():
    """文本与已编码字节的边界必须由 encode/decode 明确跨越。"""

    with pytest.raises(TypeError):
        "header:" + b"value"

    assert "header:".encode("ascii") + b"value" == b"header:value"
    assert (b"header:" + b"value").decode("ascii") == "header:value"

    # 默认 UTF-8 很方便，但外部协议已有编码约定时应显式写出，避免环境/协议误解。


def test_str_of_bytes_produces_a_representation_instead_of_decoding_text():
    """单参数 str() 不猜 bytes 的编码；解码必须提供明确编码。"""

    encoded = "咖啡".encode("utf-8")

    assert str() == ""
    assert str(42) == "42"
    assert str(encoded) == repr(encoded)
    assert str(encoded) != "咖啡"
    assert str(encoded, encoding="utf-8") == "咖啡"
    assert encoded.decode("utf-8") == "咖啡"

    # `str(bytes_value)` 常见结果形如 "b'...'"，那是诊断表示，不是文本解码。


def test_percent_format_format_and_format_map_are_distinct_entry_points():
    """三种 str 格式化入口都能复用格式迷你语言，但参数来源不同。"""

    assert "%s=%04d" % ("items", 7) == "items=0007"
    assert "{}={:04d}".format("items", 7) == "items=0007"
    assert "{name}={count:04d}".format_map(
        {"name": "items", "count": 7}
    ) == "items=0007"

    # f-string、format() 的求值和 `__format__` 分派见 014；不要通过拼接手工实现
    # 数值宽度、对齐和表示规则。
