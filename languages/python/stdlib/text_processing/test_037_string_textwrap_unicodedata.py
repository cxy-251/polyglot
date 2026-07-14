"""037｜``string``、``textwrap`` 与 ``unicodedata`` 文本处理示例。

``string`` 提供 ASCII 常量、轻量模板和可扩展格式化器；``textwrap`` 按 Python
字符位置整理普通段落；``unicodedata`` 则暴露 Unicode Character Database 属性与
正规化操作。三者可以串成文本生成、排版和比较前规范化的常见工作流。

需要特别区分“ASCII 集合”“Unicode code point”“grapheme cluster”和终端显示列宽；
它们不是同一个计量单位。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.string python.string.constants
# polyglot-covers: python.string.capwords python.string.Template
# polyglot-covers: python.string.Formatter python.string.custom-format
# polyglot-covers: python.stdlib.textwrap python.textwrap.wrap python.textwrap.fill
# polyglot-covers: python.textwrap.TextWrapper python.textwrap.dedent
# polyglot-covers: python.textwrap.indent python.textwrap.shorten
# polyglot-covers: python.stdlib.unicodedata python.unicodedata.lookup-name
# polyglot-covers: python.unicodedata.numeric python.unicodedata.properties
# polyglot-covers: python.unicodedata.normalize python.unicodedata.is_normalized
# polyglot-covers: python.text.code-point-width python.text.grapheme-pitfall

import string
import textwrap
import unicodedata
from types import SimpleNamespace

import pytest


def test_string_constants_are_fixed_ascii_sets_not_unicode_categories():
    """这些便捷常量固定为 ASCII；它们不会随 locale 或 Unicode 数据库扩张。"""

    assert string.ascii_lowercase == "abcdefghijklmnopqrstuvwxyz"
    assert string.ascii_uppercase == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert string.ascii_letters == string.ascii_lowercase + string.ascii_uppercase
    assert string.digits == "0123456789"
    assert string.octdigits == "01234567"
    assert string.hexdigits == string.digits + "abcdef" + "ABCDEF"
    assert string.whitespace == " \t\n\r\x0b\x0c"
    assert string.printable == (
        string.digits
        + string.ascii_letters
        + string.punctuation
        + string.whitespace
    )

    assert "é" not in string.ascii_letters
    assert "٣" not in string.digits  # U+0663 是 Unicode 数字，但不是 ASCII digit。
    assert "!" in string.punctuation

    # printable 包含换行、tab 等空白，因此整个常量自身并不满足 str.isprintable()。
    assert string.printable.isprintable() is False


def test_capwords_normalizes_default_whitespace_but_explicit_sep_is_literal():
    """默认按任意空白拆分并用单空格连接；指定 sep 后只按该字面分隔符处理。"""

    assert string.capwords("  hello\tWORLD\npython  ") == "Hello World Python"
    assert string.capwords("don't STOP") == "Don't Stop"

    # str.split("-") 会保留相邻/首尾分隔符形成的空字段，所以双连字符和尾连字符仍在。
    assert string.capwords("alpha--BETA-", sep="-") == "Alpha--Beta-"


def test_template_supports_named_braced_and_escaped_dollar_placeholders():
    """Template 只做标识符替换；花括号用于划清名称边界，双美元产生字面美元。"""

    template = string.Template("$greeting, ${user}! $$${amount}; ${item}_code")

    assert template.substitute(
        greeting="Hello",
        user="Ada",
        amount="5",
        item="book",
    ) == "Hello, Ada! $5; book_code"

    # 同时传 mapping 与关键字时，关键字值优先。
    assert string.Template("$name").substitute(
        {"name": "mapping"},
        name="keyword",
    ) == "keyword"


def test_template_substitute_fails_loudly_while_safe_substitute_can_leave_tokens():
    """substitute 适合要求数据完整的路径；safe_substitute 会把问题原样留在输出中。"""

    missing = string.Template("$known/$missing")

    with pytest.raises(KeyError) as captured:
        missing.substitute(known="ready")
    assert captured.value.args == ("missing",)
    assert missing.safe_substitute(known="ready") == "ready/$missing"

    invalid = string.Template("cost: $")
    with pytest.raises(ValueError):
        invalid.substitute()
    assert invalid.safe_substitute() == "cost: $"

    # safe_substitute 不是校验器或安全沙箱；调用方仍需检查残留 placeholder。


def test_template_subclass_can_change_delimiter_at_class_definition_time():
    """Template.__init_subclass__ 会据类属性生成匹配 pattern，实例只负责保存模板文本。"""

    class PercentTemplate(string.Template):
        delimiter = "%"

    template = PercentTemplate("%name bought %% %{item}")

    assert template.substitute(name="Ada", item="book") == "Ada bought % book"
    assert PercentTemplate.delimiter == "%"
    assert PercentTemplate.pattern is not string.Template.pattern


def test_formatter_parse_and_get_field_expose_format_string_structure():
    """Formatter 可把 format string 拆成字面文本、字段名、format spec 和 conversion。"""

    formatter = string.Formatter()
    format_string = "User {user.name!r:>12} has {items[0]:04d}"

    assert list(formatter.parse(format_string)) == [
        ("User ", "user.name", ">12", "r"),
        (" has ", "items[0]", "04d", None),
    ]

    user = SimpleNamespace(name="Ada")
    assert formatter.get_field("user.name", (), {"user": user}) == ("Ada", "user")
    assert formatter.get_field("items[0]", (), {"items": [7]}) == (7, "items")
    assert formatter.convert_field("Ada", "r") == "'Ada'"
    assert formatter.format_field(7, "04d") == "0007"


def test_formatter_subclass_can_add_one_controlled_format_spec():
    """小型 Formatter 子类可扩展 format spec；其余 spec 应委托给标准实现。"""

    class SlugFormatter(string.Formatter):
        def format_field(self, value, format_spec):
            if format_spec == "slug":
                return "-".join(str(value).strip().lower().split())
            return super().format_field(value, format_spec)

    formatter = SlugFormatter()

    assert formatter.format(
        "post={title:slug}; count={count:03d}",
        title="  Hello   Unicode World  ",
        count=7,
    ) == "post=hello-unicode-world; count=007"

    # 自定义 Formatter 不是表达式沙箱；不可信模板仍不应获得任意对象图。


def test_wrap_and_fill_share_width_and_indent_rules():
    """width 包含 indent；wrap 返回行列表，fill 只是用换行连接同一布局。"""

    text = "alpha beta gamma"
    options = {
        "width": 12,
        "initial_indent": "> ",
        "subsequent_indent": "  ",
    }

    assert textwrap.wrap(text, **options) == ["> alpha beta", "  gamma"]
    assert textwrap.fill(text, **options) == "> alpha beta\n  gamma"

    with pytest.raises(ValueError, match="placeholder too large"):
        textwrap.wrap("alpha", width=3, max_lines=1, placeholder=" [...]")


def test_textwrapper_expands_tabs_and_replaces_but_does_not_collapse_whitespace():
    """replace_whitespace 把控制空白换成空格，却不会把连续空格自动压成一个。"""

    wrapper = textwrap.TextWrapper(
        width=20,
        expand_tabs=True,
        tabsize=4,
        replace_whitespace=True,
        drop_whitespace=True,
    )

    # a 后的 tab 扩成三个空格；newline 变成一个空格，内部连续空格仍保留。
    assert wrapper.wrap("a\tb\nc") == ["a   b c"]


def test_long_word_and_hyphen_options_choose_overflow_or_code_point_breaks():
    """默认会切长单词；关闭后单行可超过 width，连字符也影响合法断点。"""

    assert textwrap.wrap("abcdefgh ij", width=5) == ["abcde", "fgh", "ij"]
    assert textwrap.wrap(
        "abcdefgh ij",
        width=5,
        break_long_words=False,
    ) == ["abcdefgh", "ij"]

    assert textwrap.wrap("high-speed", width=6) == ["high-", "speed"]
    assert textwrap.wrap(
        "high-speed",
        width=6,
        break_on_hyphens=False,
    ) == ["high-s", "peed"]


def test_max_lines_uses_placeholder_and_textwrapper_instances_are_reusable():
    """截断占位符也计入 width；固定配置的 TextWrapper 可重复处理多段文本。"""

    assert textwrap.wrap(
        "alpha beta gamma delta epsilon",
        width=11,
        max_lines=2,
        placeholder=" [...]",
    ) == ["alpha beta", "gamma [...]"]

    wrapper = textwrap.TextWrapper(width=9, subsequent_indent="..")
    assert wrapper.wrap("one two three") == ["one two", "..three"]
    assert wrapper.wrap("four five six") == ["four five", "..six"]


def test_dedent_removes_only_common_literal_whitespace_prefix():
    """dedent 计算所有非空行的公共前缀，并把纯空白行规范成单个 newline。"""

    indented = (
        "        first\n"
        "          second\n"
        "        \n"
        "        third\n"
    )

    assert textwrap.dedent(indented) == "first\n  second\n\nthird\n"

    # tab 和空格都是缩进字符，但并不彼此等价；这里没有可删除的公共字面前缀。
    mixed = "  alpha\n\tbeta\n"
    assert textwrap.dedent(mixed) == mixed


def test_indent_predicate_controls_whether_blank_lines_are_prefixed():
    """默认只缩进含非空白字符的行；predicate 可显式包含空行。"""

    text = "alpha\n\nbeta\n"

    assert textwrap.indent(text, "> ") == "> alpha\n\n> beta\n"
    assert textwrap.indent(text, "> ", predicate=lambda _line: True) == (
        "> alpha\n> \n> beta\n"
    )


def test_shorten_collapses_whitespace_before_applying_one_line_wrapper():
    """shorten 会先 split/join 折叠空白，再以 max_lines=1 的方式添加 placeholder。"""

    text = "  alpha\n\tbeta   gamma delta  "
    expected = "alpha beta [...]"

    assert textwrap.shorten(text, width=18, placeholder=" [...]") == expected
    assert textwrap.shorten(
        text,
        width=18,
        placeholder=" [...]",
        replace_whitespace=False,
        drop_whitespace=False,
    ) == expected

    # 上述两个选项无法保留原空白，因为 shorten 在调用 TextWrapper 前已经折叠它。


def test_unicode_lookup_and_name_are_inverse_only_for_named_characters():
    """lookup 按正式名称查字符；name 对无正式名称字符需要 default 或会抛 ValueError。"""

    snowman = "\u2603"
    private_use = "\ue000"

    assert unicodedata.lookup("SNOWMAN") == snowman
    assert unicodedata.name(snowman) == "SNOWMAN"
    assert unicodedata.name(private_use, "<private-use>") == "<private-use>"

    with pytest.raises(ValueError):
        unicodedata.name(private_use)
    with pytest.raises(KeyError):
        unicodedata.lookup("NOT A REAL UNICODE CHARACTER NAME")


def test_decimal_digit_and_numeric_cover_increasingly_broad_character_sets():
    """decimal 最窄、digit 更宽、numeric 最宽；numeric 返回 float。"""

    assert unicodedata.decimal("9") == 9
    assert unicodedata.digit("9") == 9
    assert unicodedata.numeric("9") == 9.0
    assert isinstance(unicodedata.numeric("9"), float)

    superscript_two = "\u00b2"
    roman_twelve = "\u216b"
    one_half = "\u00bd"

    assert unicodedata.decimal(superscript_two, None) is None
    assert unicodedata.digit(superscript_two) == 2
    assert unicodedata.numeric(superscript_two) == 2.0

    assert unicodedata.digit(roman_twelve, None) is None
    assert unicodedata.numeric(roman_twelve) == 12.0
    assert unicodedata.numeric(one_half) == 0.5

    with pytest.raises(ValueError):
        unicodedata.decimal(superscript_two)
    with pytest.raises(ValueError):
        unicodedata.digit(roman_twelve)


def test_unicode_property_functions_reveal_class_width_and_decomposition_data():
    """属性值是 Unicode 数据库代码；空字符串也可能是合法的“未定义”结果。"""

    combining_acute = "\u0301"
    cjk_character = "界"
    unassigned = "\u0378"

    assert unicodedata.category("A") == "Lu"
    assert unicodedata.bidirectional("A") == "L"
    assert unicodedata.combining("A") == 0
    assert unicodedata.east_asian_width("A") == "Na"

    assert unicodedata.category(combining_acute) == "Mn"
    assert unicodedata.combining(combining_acute) == 230
    assert unicodedata.east_asian_width(cjk_character) == "W"
    assert unicodedata.mirrored(">") == 1
    assert unicodedata.bidirectional(unassigned) == ""

    assert unicodedata.decomposition("é") == "0065 0301"
    assert unicodedata.decomposition("①") == "<circle> 0031"
    assert unicodedata.decomposition("A") == ""


def test_canonical_normalization_makes_visually_equal_spellings_comparable():
    """NFC 组合，NFD 分解；canonical equivalent 文本正规化前仍可有不同 code points。"""

    composed = "café"
    decomposed = "cafe\u0301"

    assert composed != decomposed
    assert len(composed) == 4
    assert len(decomposed) == 5
    assert unicodedata.normalize("NFC", decomposed) == composed
    assert unicodedata.normalize("NFD", composed) == decomposed

    assert unicodedata.is_normalized("NFC", composed) is True
    assert unicodedata.is_normalized("NFC", decomposed) is False

    normalized = unicodedata.normalize("NFC", decomposed)
    assert unicodedata.normalize("NFC", normalized) == normalized


def test_compatibility_normalization_can_intentionally_remove_distinctions():
    """NFKC/NFKD 还应用 compatibility mapping，适合搜索键但可能丢失表现语义。"""

    circled_one = "①"
    ligature_ff = "ﬀ"

    assert unicodedata.normalize("NFC", circled_one) == circled_one
    assert unicodedata.normalize("NFKC", circled_one) == "1"
    assert unicodedata.normalize("NFKD", circled_one) == "1"
    assert unicodedata.normalize("NFKC", ligature_ff) == "ff"

    # 不应无条件改写展示/法律标识文本；先确认业务是否允许这些区别消失。


def test_textwrap_width_counts_code_points_not_graphemes_or_terminal_columns():
    """textwrap 直接切 Python 字符串位置，可能拆开组合序列，也不计算全角终端列宽。"""

    combining_grapheme = "e\u0301"
    fullwidth_word = "界界"

    assert len(combining_grapheme) == 2
    assert textwrap.wrap(combining_grapheme, width=1) == ["e", "\u0301"]
    assert textwrap.wrap(fullwidth_word, width=1) == ["界", "界"]

    # “界”通常占两个终端列，但 textwrap 只看到两个各长 1 的 code point。
    assert unicodedata.east_asian_width("界") == "W"
