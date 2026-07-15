"""457｜SAX ``make_parser``、文件/字符串便捷入口与 SAXParseException。

SAX 不返回树：``parse*`` 返回 None，业务结果必须由 ContentHandler 在回调中积累。输入可为
文件名、file-like、str 或 bytes；``make_parser()`` 返回 XMLReader。3.7.1 起外部通用实体默认
关闭，但 SAX 整体仍不是恶意 XML 安全边界。格式错误通过带行列和底层异常的 SAXParseException。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.make_parser
# polyglot-covers: python.xml.sax.make_parser.parser_list-iterable-3.8
# polyglot-covers: python.xml.sax.parse
# polyglot-covers: python.xml.sax.parse.filename-and-stream
# polyglot-covers: python.xml.sax.parseString
# polyglot-covers: python.xml.sax.parseString.str-and-bytes
# polyglot-covers: python.xml.sax.parse-return-none-event-result
# polyglot-covers: python.xml.sax.external-general-entities-disabled-3.7.1
# polyglot-covers: python.xml.sax.SAXParseException
# polyglot-covers: python.xml.sax.SAXException.getMessage
# polyglot-covers: python.xml.sax.SAXException.getException
# polyglot-covers: python.xml.sax-untrusted-xml-warning

import io
import xml.sax
from xml.sax import handler
from xml.sax import xmlreader

import pytest


class TextCollector(handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.start_tags = []
        self.text_parts = []

    def startElement(self, name, attrs):
        self.start_tags.append((name, attrs.copy()))

    def characters(self, content):
        self.text_parts.append(content)


def test_parse_string_accepts_text_and_bytes_and_returns_no_tree():
    text_handler = TextCollector()
    bytes_handler = TextCollector()

    text_result = xml.sax.parseString("<root><item>中文</item></root>", text_handler)
    byte_result = xml.sax.parseString(
        "<root><item>中文</item></root>".encode("utf-8"),
        bytes_handler,
    )

    assert text_result is byte_result is None
    assert text_handler.start_tags == bytes_handler.start_tags
    assert "".join(text_handler.text_parts) == "中文"


def test_parse_accepts_a_filename_or_open_character_stream(tmp_path):
    path = tmp_path / "document.xml"
    path.write_text("<root><item id='one'/></root>", encoding="utf-8")
    from_name = TextCollector()
    from_stream = TextCollector()

    xml.sax.parse(str(path), from_name)
    xml.sax.parse(io.StringIO("<other/>"), from_stream)

    assert [name for name, _ in from_name.start_tags] == ["root", "item"]
    assert [name for name, _ in from_stream.start_tags] == ["other"]


def test_make_parser_returns_xmlreader_and_keeps_external_entities_off_by_default():
    # 3.8 起 parser_list 可为任意 iterable；空 tuple 回退到标准解析器列表。
    parser = xml.sax.make_parser(parser_list=())

    assert isinstance(parser, xmlreader.XMLReader)
    assert not parser.getFeature(handler.feature_external_ges)


def test_malformed_xml_raises_sax_parse_exception_with_location_and_cause():
    with pytest.raises(xml.sax.SAXParseException) as caught:
        xml.sax.parseString("<root>\n<item></root>", TextCollector())

    error = caught.value
    assert error.getLineNumber() == 2
    assert error.getColumnNumber() >= 0
    assert isinstance(error.getMessage(), str)
    assert error.getException() is not None
