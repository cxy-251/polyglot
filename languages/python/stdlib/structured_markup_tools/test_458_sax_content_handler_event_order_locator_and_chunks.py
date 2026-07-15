"""458｜SAX ContentHandler 回调顺序、Locator 有效期与字符分块陷阱。

事件顺序映射源文档顺序，``setDocumentLocator`` 若提供必先于其他内容事件。Locator 只保证在
回调期间位置准确，需立即复制行列。``characters()`` 的 chunk 边界没有语义保证，同一连续文本
可能被拆成多次回调；消费方应累积后在 endElement 处解释，不能把一次回调当作完整字段。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.handler.ContentHandler
# polyglot-covers: python.xml.sax.handler.ContentHandler.setDocumentLocator
# polyglot-covers: python.xml.sax.handler.ContentHandler.startDocument
# polyglot-covers: python.xml.sax.handler.ContentHandler.endDocument
# polyglot-covers: python.xml.sax.handler.ContentHandler.startElement
# polyglot-covers: python.xml.sax.handler.ContentHandler.endElement
# polyglot-covers: python.xml.sax.handler.ContentHandler.characters
# polyglot-covers: python.xml.sax.handler.ContentHandler.processingInstruction
# polyglot-covers: python.xml.sax.handler.characters-chunk-boundaries-unspecified
# polyglot-covers: python.xml.sax.handler.startElement-attrs-may-be-reused
# polyglot-covers: python.xml.sax.xmlreader.Locator
# polyglot-covers: python.xml.sax.xmlreader.Locator-callback-only-validity

import xml.sax
from xml.sax import handler


class EventRecorder(handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.events = []
        self.locator = None

    def setDocumentLocator(self, locator):
        self.locator = locator
        self.events.append(("locator",))

    def startDocument(self):
        self.events.append(("start-document",))

    def endDocument(self):
        self.events.append(("end-document",))

    def startElement(self, name, attrs):
        position = (self.locator.getLineNumber(), self.locator.getColumnNumber())
        # attrs 对象可能被解析器复用；copy 后才适合跨回调保存。
        self.events.append(("start", name, attrs.copy(), position))

    def endElement(self, name):
        self.events.append(("end", name))

    def characters(self, content):
        if content:
            self.events.append(("text", content))

    def processingInstruction(self, target, data):
        self.events.append(("pi", target, data))


def test_content_events_follow_document_order_and_locator_is_copied_in_callback():
    recorder = EventRecorder()
    xml.sax.parseString(
        "<?build fast?><root id='one'>left<child/>right</root>",
        recorder,
    )

    event_kinds = [event[0] for event in recorder.events]
    assert event_kinds == [
        "locator",
        "start-document",
        "pi",
        "start",
        "text",
        "start",
        "end",
        "text",
        "end",
        "end-document",
    ]
    root_start = next(event for event in recorder.events if event[:2] == ("start", "root"))
    assert root_start[2] == {"id": "one"}
    assert root_start[3][0] == 1


def test_incremental_input_may_split_text_so_consumers_join_character_events():
    recorder = EventRecorder()
    parser = xml.sax.make_parser()
    parser.setContentHandler(recorder)

    parser.feed("<root>alpha")
    parser.feed("beta")
    parser.feed("gamma</root>")
    parser.close()

    text = "".join(event[1] for event in recorder.events if event[0] == "text")
    assert text == "alphabetagamma"
