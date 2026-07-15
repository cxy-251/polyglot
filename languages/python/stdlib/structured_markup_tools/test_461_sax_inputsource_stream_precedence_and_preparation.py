"""461｜SAX InputSource 标识符、byte/character stream 优先级与输入准备。

InputSource 可同时保存 public/system ID、encoding、byte stream 和 character stream。若 character
stream 存在，解析器会忽略 byte stream、其 encoding 以及自行打开 system ID；这是注入已解码
受控输入、避免意外 I/O 的关键。``prepare_input_source`` 统一包装字符串、file-like 或已有对象。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.xmlreader.InputSource
# polyglot-covers: python.xml.sax.xmlreader.InputSource.publicId
# polyglot-covers: python.xml.sax.xmlreader.InputSource.systemId
# polyglot-covers: python.xml.sax.xmlreader.InputSource.encoding
# polyglot-covers: python.xml.sax.xmlreader.InputSource.byteStream
# polyglot-covers: python.xml.sax.xmlreader.InputSource.characterStream
# polyglot-covers: python.xml.sax.InputSource-character-stream-precedence
# polyglot-covers: python.xml.sax.saxutils.prepare_input_source

import io
import xml.sax
from xml.sax import handler
from xml.sax import saxutils
from xml.sax import xmlreader


class NameCollector(handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.names = []

    def startElement(self, name, attrs):
        self.names.append(name)


def test_input_source_stores_identifiers_encoding_and_both_stream_kinds():
    source = xmlreader.InputSource("document.xml")
    byte_stream = io.BytesIO(b"<bytes/>")
    character_stream = io.StringIO("<characters/>")

    source.setPublicId("-//POLYGLOT//XML 1.0//EN")
    source.setSystemId("urn:polyglot:document")
    source.setEncoding("utf-8")
    source.setByteStream(byte_stream)
    source.setCharacterStream(character_stream)

    assert source.getPublicId() == "-//POLYGLOT//XML 1.0//EN"
    assert source.getSystemId() == "urn:polyglot:document"
    assert source.getEncoding() == "utf-8"
    assert source.getByteStream() is byte_stream
    assert source.getCharacterStream() is character_stream


def test_character_stream_wins_over_conflicting_byte_stream_and_encoding():
    source = xmlreader.InputSource("https://invalid.example/never-opened.xml")
    source.setEncoding("ascii")
    source.setByteStream(io.BytesIO(b"<wrong/>"))
    source.setCharacterStream(io.StringIO("<right>中文</right>"))
    collector = NameCollector()
    parser = xml.sax.make_parser()
    parser.setContentHandler(collector)

    parser.parse(source)

    assert collector.names == ["right"]


def test_prepare_input_source_preserves_existing_source_and_wraps_file_like():
    existing = xmlreader.InputSource("urn:existing")
    existing.setCharacterStream(io.StringIO("<existing/>"))
    prepared_existing = saxutils.prepare_input_source(existing)
    text_stream = io.StringIO("<root/>")
    prepared_stream = saxutils.prepare_input_source(text_stream, base="urn:base")

    assert prepared_existing is existing
    assert prepared_stream.getCharacterStream() is text_stream
