"""460｜XMLReader handler 配置、feature/property 错误与 IncrementalParser 生命周期。

XMLReader 分别持有 content、DTD、entity resolver 和 error handler。feature 必须在解析前设置，
未知名称与实现不支持的值由两种 SAX 异常区分。增量 reader 可 ``feed`` 分块并以 ``close`` 检查
文档结尾；close 后若要解析下一份文档必须先 ``reset``，直接复用的结果没有定义。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.xmlreader.XMLReader
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.setContentHandler
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.getContentHandler
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.setDTDHandler
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.getDTDHandler
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.setEntityResolver
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.getEntityResolver
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.setErrorHandler
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.getErrorHandler
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.setFeature
# polyglot-covers: python.xml.sax.xmlreader.XMLReader.getFeature
# polyglot-covers: python.xml.sax.SAXNotRecognizedException
# polyglot-covers: python.xml.sax.SAXNotSupportedException
# polyglot-covers: python.xml.sax.xmlreader.IncrementalParser.feed
# polyglot-covers: python.xml.sax.xmlreader.IncrementalParser.close
# polyglot-covers: python.xml.sax.xmlreader.IncrementalParser.reset

import xml.sax
from xml.sax import handler

import pytest


class RootCollector(handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.roots = []

    def startElement(self, name, attrs):
        if not self.roots or self.roots[-1][1]:
            self.roots.append([name, False])

    def endElement(self, name):
        if self.roots and self.roots[-1][0] == name:
            self.roots[-1][1] = True


def test_reader_setters_and_getters_keep_each_handler_role_separate():
    parser = xml.sax.make_parser()
    content = RootCollector()
    dtd = handler.DTDHandler()
    resolver = handler.EntityResolver()
    errors = handler.ErrorHandler()

    parser.setContentHandler(content)
    parser.setDTDHandler(dtd)
    parser.setEntityResolver(resolver)
    parser.setErrorHandler(errors)

    assert parser.getContentHandler() is content
    assert parser.getDTDHandler() is dtd
    assert parser.getEntityResolver() is resolver
    assert parser.getErrorHandler() is errors


def test_unknown_and_unsupported_features_raise_distinct_sax_exceptions():
    parser = xml.sax.make_parser()

    with pytest.raises(xml.sax.SAXNotRecognizedException):
        parser.getFeature("urn:polyglot:unknown-feature")
    with pytest.raises(xml.sax.SAXNotSupportedException):
        parser.setFeature(handler.feature_validation, True)


def test_incremental_parser_is_reset_before_reuse_for_a_second_document():
    parser = xml.sax.make_parser()
    collector = RootCollector()
    parser.setContentHandler(collector)

    parser.feed("<first>")
    parser.feed("value")
    parser.feed("</first>")
    parser.close()
    parser.reset()
    parser.feed("<second/>")
    parser.close()

    assert [name for name, complete in collector.roots if complete] == [
        "first",
        "second",
    ]
