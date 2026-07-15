"""431｜HTMLParser comment/doctype/PI/unknown declaration、raw-text 与 scripting 模式。

comment、doctype、processing instruction 和未知 ``<![...]>`` 各有独立回调；XHTML 风格 PI
末尾的 ``?`` 会留在 data 中。script/style 是 raw-text 元素，内部标签和字符引用都按原文交给
handle_data。3.10.20 新增 scripting 参数，使 noscript 内容在脚本启用时也按原文返回。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.html.parser.handle_comment
# polyglot-covers: python.html.parser.handle_decl
# polyglot-covers: python.html.parser.handle_pi
# polyglot-covers: python.html.parser.processing-instruction-trailing-question-mark
# polyglot-covers: python.html.parser.unknown_decl
# polyglot-covers: python.html.parser.script-style-raw-text
# polyglot-covers: python.html.parser.script-charrefs-not-converted
# polyglot-covers: python.html.parser.scripting-parameter-3.10.20
# polyglot-covers: python.html.parser.noscript-raw-text-when-scripting

from html.parser import HTMLParser
import inspect


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
