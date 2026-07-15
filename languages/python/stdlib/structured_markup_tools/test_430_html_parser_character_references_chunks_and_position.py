"""430｜HTMLParser 字符引用分派、增量缓冲、reset 与源码位置。

convert_charrefs=True 时普通文本中的引用先转 Unicode 再交给 handle_data；设为 False 才调用
handle_entityref/handle_charref。feed 可接任意 str 分块并缓存未完成 token，但 data 回调边界不是
稳定文本分块协议，消费者应自行拼接。getpos 是当前事件起点，reset 会丢弃尚未处理的缓冲。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from html.parser import HTMLParser

import pytest


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
