"""466｜XMLGenerator 从 SAX 事件生成 XML、命名空间声明与空元素样式。

XMLGenerator 是 ContentHandler，可接在 parser 或 filter 后把事件重新写成 XML。它负责转义
文本/属性并输出 encoding 声明；``short_empty_elements`` 只改变无内容元素的表层写法。namespace
模式要先提供 prefix mapping，AttributesNS 同时携带扩展名与用于输出的 qname。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.saxutils.XMLGenerator
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.startDocument
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.startElement
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.characters
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.endElement
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.processingInstruction
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.short_empty_elements
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.startPrefixMapping
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.startElementNS
# polyglot-covers: python.xml.sax.saxutils.XMLGenerator.endElementNS

import io
from xml.sax import saxutils
from xml.sax import xmlreader


def test_generator_escapes_content_and_can_self_close_an_empty_element():
    output = io.StringIO()
    generator = saxutils.XMLGenerator(
        output,
        encoding="utf-8",
        short_empty_elements=True,
    )

    generator.startDocument()
    generator.processingInstruction("build", "fast")
    generator.startElement("root", xmlreader.AttributesImpl({"a": "1 & 2"}))
    generator.characters("x < y")
    generator.startElement("empty", xmlreader.AttributesImpl({}))
    generator.endElement("empty")
    generator.endElement("root")
    generator.endDocument()

    wire = output.getvalue()
    assert wire.startswith('<?xml version="1.0" encoding="utf-8"?>\n')
    assert "<?build fast?>" in wire
    assert '<root a="1 &amp; 2">x &lt; y<empty/></root>' in wire


def test_namespace_generator_uses_mapping_and_attribute_qnames_for_output():
    output = io.StringIO()
    generator = saxutils.XMLGenerator(
        output,
        encoding="utf-8",
        short_empty_elements=True,
    )
    state = ("urn:parts", "state")
    attrs = xmlreader.AttributesNSImpl(
        {state: "ready"},
        {state: "p:state"},
    )

    generator.startDocument()
    generator.startPrefixMapping("p", "urn:parts")
    generator.startElementNS(("urn:parts", "item"), "p:item", attrs)
    generator.endElementNS(("urn:parts", "item"), "p:item")
    generator.endPrefixMapping("p")
    generator.endDocument()

    assert '<p:item xmlns:p="urn:parts" p:state="ready"/>' in output.getvalue()
