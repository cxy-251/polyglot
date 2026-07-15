"""111｜html.escape/unescape 的文本、属性与 HTML5 字符引用规则。

escape 默认同时处理 ``&<>`` 和两种引号，适合放入带引号的 HTML 属性；quote=False 只适合
普通文本节点。unescape 按 HTML5 规则接受命名、十进制、十六进制甚至部分缺分号引用，也会把
历史数值区间映射和非法码点修正成 Unicode；它不是 XML 严格实体解析器。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.html.escape
# polyglot-covers: python.html.escape-amp-lt-gt
# polyglot-covers: python.html.escape-quote-true
# polyglot-covers: python.html.escape-quote-false
# polyglot-covers: python.html.escape-attribute-context
# polyglot-covers: python.html.unescape
# polyglot-covers: python.html.unescape-named-reference
# polyglot-covers: python.html.unescape-decimal-reference
# polyglot-covers: python.html.unescape-hex-reference
# polyglot-covers: python.html.unescape-optional-semicolon-html5
# polyglot-covers: python.html.unescape-invalid-codepoint-replacement
# polyglot-covers: python.html.unescape-windows-1252-remap
# polyglot-covers: python.html.unescape-unknown-reference-preserved



from html import escape, unescape
from html.entities import codepoint2name, entitydefs, html5, name2codepoint
from html.parser import HTMLParser
import pytest
import inspect

def test_escape_distinguishes_text_content_from_quoted_attribute_context():
    source = 'Tom & <tag title="x">\'s'

    assert escape(source) == "Tom &amp; &lt;tag title=&quot;x&quot;&gt;&#x27;s"
    assert escape(source, quote=False) == 'Tom &amp; &lt;tag title="x"&gt;\'s'


def test_unescape_accepts_named_decimal_hex_and_legacy_semicolonless_references():
    assert unescape("&gt; &#62; &#x3E;") == "> > >"
    assert unescape("Copyright &copy 2024") == "Copyright © 2024"
    assert unescape("&doesnotexist;") == "&doesnotexist;"


def test_unescape_applies_html5_error_recovery_instead_of_strict_unicode_decoding():
    assert unescape("&#0;") == "\ufffd"
    assert unescape("&#xD800;") == "\ufffd"
    # HTML5 为兼容旧页面，把 0x80 映射为 Windows-1252 的 EURO SIGN，而不是 U+0080。
    assert unescape("&#128;") == "€"


# html.entities 的 HTML5、HTML4 与 XHTML 实体映射表。
#
# html5 的 key 通常含分号，但标准允许省略分号的少数名字会同时出现两种 key；value 可能包含
# 多个 Unicode 码点，不能假设总能用 chr() 表示。name2codepoint/codepoint2name 是 HTML4
# 整数映射，entitydefs 则保留 XHTML 1.0 的替换文本，三者并非 html5 的可逆视图。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.html.entities.html5
# polyglot-covers: python.html.entities.html5-semicolon-key
# polyglot-covers: python.html.entities.html5-semicolonless-alias
# polyglot-covers: python.html.entities.html5-multi-codepoint-value
# polyglot-covers: python.html.entities.name2codepoint
# polyglot-covers: python.html.entities.codepoint2name
# polyglot-covers: python.html.entities.entitydefs
# polyglot-covers: python.html.entities-html4-versus-html5
# polyglot-covers: python.html.entities-global-table-do-not-mutate



def test_html5_table_includes_semicolon_keys_optional_aliases_and_multi_codepoints():
    assert html5["gt;"] == ">"
    assert html5["copy;"] == "©"
    assert html5["copy"] == "©"
    assert html5["NotEqualTilde;"] == "≂̸"
    assert len(html5["NotEqualTilde;"]) == 2


def test_legacy_tables_map_names_codepoints_and_xhtml_replacement_text():
    assert name2codepoint["nbsp"] == 160
    assert codepoint2name[160] == "nbsp"
    assert entitydefs["nbsp"] == "\xa0"
    assert "NotEqualTilde" not in name2codepoint


def test_global_entity_tables_should_be_copied_before_application_customization():
    local_entities = dict(html5)
    local_entities["project;"] = "P"

    assert local_entities["project;"] == "P"
    assert "project;" not in html5


# HTMLParser 的 tag/attribute 回调、原始开始标签与宽容结构。
#
# HTMLParser 把 tag 和属性名转小写、去掉属性引号并解码属性中的字符引用；get_starttag_text
# 仍保留原始大小写和空白，适合低损重写。``<tag/>`` 默认依次分派 start/end。解析器只做词法
# 事件流，不校验开始结束标签是否配对，也不会按浏览器规则隐式补闭合标签。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.html.parser.HTMLParser
# polyglot-covers: python.html.parser.HTMLParser.feed
# polyglot-covers: python.html.parser.HTMLParser.close
# polyglot-covers: python.html.parser.handle_starttag
# polyglot-covers: python.html.parser.handle_endtag
# polyglot-covers: python.html.parser.handle_startendtag
# polyglot-covers: python.html.parser.startend-default-start-then-end
# polyglot-covers: python.html.parser.tag-name-lowercasing
# polyglot-covers: python.html.parser.attribute-name-lowercasing
# polyglot-covers: python.html.parser.attribute-value-unquoting
# polyglot-covers: python.html.parser.attribute-character-reference-conversion
# polyglot-covers: python.html.parser.HTMLParser.get_starttag_text
# polyglot-covers: python.html.parser.tolerates-mismatched-tags
# polyglot-covers: python.html.parser.no-implicit-close-events



class TagRecorder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.events = []

    def handle_starttag(self, tag, attrs):
        self.events.append(("start", tag, attrs, self.get_starttag_text()))

    def handle_endtag(self, tag):
        self.events.append(("end", tag))

    def handle_data(self, data):
        self.events.append(("data", data))


def test_start_tag_normalizes_structure_but_preserves_raw_lexical_text():
    parser = TagRecorder()
    parser.feed('<A  HREF="/a?x=1&amp;y=2" DISABLED>link</A>')
    parser.close()

    assert parser.events == [
        (
            "start",
            "a",
            [("href", "/a?x=1&y=2"), ("disabled", None)],
            '<A  HREF="/a?x=1&amp;y=2" DISABLED>',
        ),
        ("data", "link"),
        ("end", "a"),
    ]


def test_xhtml_empty_tag_uses_default_start_then_end_fallback():
    parser = TagRecorder()
    # XHTML 风格的 ``/>`` 紧跟未加引号的属性值时，HTML 语法会把 slash 当作值的一部分；
    # 为了触发 startendtag，最后一个属性值必须加引号或在 slash 前留空格。
    parser.feed('<BR class="gap"/>')
    assert parser.events == [
        ("start", "br", [("class", "gap")], '<BR class="gap"/>'),
        ("end", "br"),
    ]


def test_parser_reports_mismatched_source_events_without_repairing_the_tree():
    parser = TagRecorder()
    parser.feed("<p><b>text</p>")
    parser.close()

    assert [(event[0], event[1]) for event in parser.events if event[0] != "data"] == [
        ("start", "p"),
        ("start", "b"),
        ("end", "p"),
    ]


# HTMLParser 字符引用分派、增量缓冲、reset 与源码位置。
#
# convert_charrefs=True 时普通文本中的引用先转 Unicode 再交给 handle_data；设为 False 才调用
# handle_entityref/handle_charref。feed 可接任意 str 分块并缓存未完成 token，但 data 回调边界不是
# 稳定文本分块协议，消费者应自行拼接。getpos 是当前事件起点，reset 会丢弃尚未处理的缓冲。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.html.parser.convert_charrefs-true
# polyglot-covers: python.html.parser.convert_charrefs-false
# polyglot-covers: python.html.parser.handle_data
# polyglot-covers: python.html.parser.handle_entityref
# polyglot-covers: python.html.parser.handle_charref
# polyglot-covers: python.html.parser.feed-incomplete-token-buffering
# polyglot-covers: python.html.parser.data-callback-chunk-boundary-unstable
# polyglot-covers: python.html.parser.HTMLParser.getpos
# polyglot-covers: python.html.parser.HTMLParser.reset
# polyglot-covers: python.html.parser.feed-requires-str




class ReferenceRecorder(HTMLParser):
    def __init__(self, *, convert_charrefs=True):
        super().__init__(convert_charrefs=convert_charrefs)
        self.events = []

    def handle_data(self, data):
        self.events.append(("data", data, self.getpos()))

    def handle_entityref(self, name):
        self.events.append(("entity", name, self.getpos()))

    def handle_charref(self, name):
        self.events.append(("char", name, self.getpos()))


def test_character_references_are_data_or_explicit_events_based_on_configuration():
    converted = ReferenceRecorder(convert_charrefs=True)
    converted.feed("&gt;&#62;&#x3E;")
    converted.close()
    assert "".join(event[1] for event in converted.events) == ">>>"
    assert {event[0] for event in converted.events} == {"data"}

    explicit = ReferenceRecorder(convert_charrefs=False)
    explicit.feed("&gt;&#62;&#x3E;")
    explicit.close()
    assert [(kind, value) for kind, value, _ in explicit.events] == [
        ("entity", "gt"),
        ("char", "62"),
        ("char", "x3E"),
    ]


def test_incremental_feed_buffers_tags_but_callers_must_join_data_events():
    parser = ReferenceRecorder(convert_charrefs=False)
    for chunk in ["<sp", "an>buff", "ered ", "text</s", "pan>"]:
        parser.feed(chunk)
    parser.close()

    text = "".join(value for kind, value, _ in parser.events if kind == "data")
    assert text == "buffered text"
    assert parser.events[0][2] == (1, 6)


def test_reset_discards_incomplete_buffer_and_feed_requires_text():
    parser = ReferenceRecorder()
    parser.feed("<unfinished")
    parser.reset()
    parser.feed("safe")
    parser.close()
    assert "".join(event[1] for event in parser.events) == "safe"

    with pytest.raises(TypeError):
        parser.feed(b"not text")


# HTMLParser comment/doctype/PI/unknown declaration、raw-text 与 scripting 模式。
#
# comment、doctype、processing instruction 和未知 ``<![...]>`` 各有独立回调；XHTML 风格 PI
# 末尾的 ``?`` 会留在 data 中。script/style 是 raw-text 元素，内部标签和字符引用都按原文交给
# handle_data。3.10.20 新增 scripting 参数，使 noscript 内容在脚本启用时也按原文返回。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.html.parser.handle_comment
# polyglot-covers: python.html.parser.handle_decl
# polyglot-covers: python.html.parser.handle_pi
# polyglot-covers: python.html.parser.processing-instruction-trailing-question-mark
# polyglot-covers: python.html.parser.unknown_decl
# polyglot-covers: python.html.parser.script-style-raw-text
# polyglot-covers: python.html.parser.script-charrefs-not-converted
# polyglot-covers: python.html.parser.scripting-parameter-3.10.20
# polyglot-covers: python.html.parser.noscript-raw-text-when-scripting



class MarkupRecorder(HTMLParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events = []

    def handle_starttag(self, tag, attrs):
        self.events.append(("start", tag))

    def handle_endtag(self, tag):
        self.events.append(("end", tag))

    def handle_data(self, data):
        self.events.append(("data", data))

    def handle_comment(self, data):
        self.events.append(("comment", data))

    def handle_decl(self, decl):
        self.events.append(("decl", decl))

    def handle_pi(self, data):
        self.events.append(("pi", data))

    def unknown_decl(self, data):
        self.events.append(("unknown", data))


def test_special_markup_forms_are_dispatched_to_distinct_callbacks():
    parser = MarkupRecorder()
    parser.feed("<!DOCTYPE html><!-- note --><?proc value?><![CDATA[raw]]>")
    parser.close()

    assert parser.events == [
        ("decl", "DOCTYPE html"),
        ("comment", " note "),
        ("pi", "proc value?"),
        ("unknown", "CDATA[raw"),
    ]


def test_script_and_style_contents_are_raw_text_even_with_charref_conversion_enabled():
    parser = MarkupRecorder(convert_charrefs=True)
    parser.feed("<script><b>&amp;</b></script><style>a>b&amp;c</style>")
    parser.close()

    assert parser.events == [
        ("start", "script"),
        ("data", "<b>&amp;</b>"),
        ("end", "script"),
        ("start", "style"),
        ("data", "a>b&amp;c"),
        ("end", "style"),
    ]


def test_scripting_true_makes_noscript_raw_when_supported_by_patch_version():
    if "scripting" not in inspect.signature(HTMLParser).parameters:
        return

    parser = MarkupRecorder(convert_charrefs=True, scripting=True)
    parser.feed("<noscript><b>fallback</b>&amp;</noscript>")
    parser.close()
    assert parser.events == [
        ("start", "noscript"),
        ("data", "<b>fallback</b>&amp;"),
        ("end", "noscript"),
    ]
