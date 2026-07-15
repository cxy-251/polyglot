"""429｜HTMLParser 的 tag/attribute 回调、原始开始标签与宽容结构。

HTMLParser 把 tag 和属性名转小写、去掉属性引号并解码属性中的字符引用；get_starttag_text
仍保留原始大小写和空白，适合低损重写。``<tag/>`` 默认依次分派 start/end。解析器只做词法
事件流，不校验开始结束标签是否配对，也不会按浏览器规则隐式补闭合标签。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from html.parser import HTMLParser


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
    parser.feed("<BR class=gap/>")
    assert parser.events == [
        ("start", "br", [("class", "gap")], "<BR class=gap/>"),
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
