"""463｜SAX DTDHandler 与可选 LexicalHandler 的低频结构事件。

ContentHandler 不报告 comment、CDATA 边界或 DTD 边界；需要这些词法信息时，把 LexicalHandler
作为 ``property_lexical_handler`` 注册。DTDHandler 只处理 notation 和未解析实体声明。CDATA
内容仍走 characters，词法回调只标记边界。案例只解析内部声明，不访问外部 system ID。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.handler.DTDHandler
# polyglot-covers: python.xml.sax.handler.DTDHandler.notationDecl
# polyglot-covers: python.xml.sax.handler.DTDHandler.unparsedEntityDecl
# polyglot-covers: python.xml.sax.handler.LexicalHandler
# polyglot-covers: python.xml.sax.handler.property_lexical_handler
# polyglot-covers: python.xml.sax.handler.LexicalHandler.comment
# polyglot-covers: python.xml.sax.handler.LexicalHandler.startDTD
# polyglot-covers: python.xml.sax.handler.LexicalHandler.endDTD
# polyglot-covers: python.xml.sax.handler.LexicalHandler.startCDATA
# polyglot-covers: python.xml.sax.handler.LexicalHandler.endCDATA

import io
import xml.sax
from xml.sax import handler
from xml.sax import xmlreader


class DTDRecorder(handler.DTDHandler):
    def __init__(self):
        super().__init__()
        self.events = []

    def notationDecl(self, name, public_id, system_id):
        self.events.append(("notation", name, public_id, system_id))

    def unparsedEntityDecl(self, name, public_id, system_id, ndata):
        self.events.append(("entity", name, public_id, system_id, ndata))


class LexicalRecorder(handler.LexicalHandler):
    def __init__(self):
        super().__init__()
        self.events = []

    def comment(self, content):
        self.events.append(("comment", content))

    def startDTD(self, name, public_id, system_id):
        self.events.append(("start-dtd", name, public_id, system_id))

    def endDTD(self):
        self.events.append(("end-dtd",))

    def startCDATA(self):
        self.events.append(("start-cdata",))

    def endCDATA(self):
        self.events.append(("end-cdata",))


class CharacterRecorder(handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.parts = []

    def characters(self, content):
        self.parts.append(content)


def test_dtd_and_lexical_handlers_receive_declarations_comments_and_cdata_bounds():
    xml = """\
<!DOCTYPE root [
  <!ELEMENT root (#PCDATA)>
  <!NOTATION png SYSTEM "image/png">
  <!ENTITY logo SYSTEM "logo.png" NDATA png>
]>
<root><![CDATA[x < y]]><!--note--></root>
"""
    parser = xml.sax.make_parser()
    dtd = DTDRecorder()
    lexical = LexicalRecorder()
    content = CharacterRecorder()
    parser.setDTDHandler(dtd)
    parser.setContentHandler(content)
    parser.setProperty(handler.property_lexical_handler, lexical)
    source = xmlreader.InputSource()
    source.setCharacterStream(io.StringIO(xml))

    parser.parse(source)

    assert ("notation", "png", None, "image/png") in dtd.events
    assert ("entity", "logo", None, "logo.png", "png") in dtd.events
    assert lexical.events == [
        ("start-dtd", "root", None, None),
        ("end-dtd",),
        ("start-cdata",),
        ("end-cdata",),
        ("comment", "note"),
    ]
    assert "x < y" in "".join(content.parts)
