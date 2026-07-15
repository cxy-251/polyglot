"""464｜SAX EntityResolver、ErrorHandler 与外部实体显式启用边界。

默认外部通用实体关闭。确需支持时，必须显式开启 feature，并用 EntityResolver 将 system ID
映射到受控 InputSource；返回原 URL 会把 I/O 决策交还 parser。ErrorHandler 决定 warning/error/
fatalError 是否抛出；不可恢复错误通常记录后重新抛出传入 SAXParseException。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.handler.EntityResolver
# polyglot-covers: python.xml.sax.handler.EntityResolver.resolveEntity
# polyglot-covers: python.xml.sax.handler.ErrorHandler
# polyglot-covers: python.xml.sax.handler.ErrorHandler.warning
# polyglot-covers: python.xml.sax.handler.ErrorHandler.error
# polyglot-covers: python.xml.sax.handler.ErrorHandler.fatalError
# polyglot-covers: python.xml.sax.handler.feature_external_ges
# polyglot-covers: python.xml.sax.external-entity-explicit-opt-in
# polyglot-covers: python.xml.sax.controlled-inputsource-from-resolver

import io
import xml.sax
from xml.sax import handler
from xml.sax import xmlreader

import pytest


class ControlledResolver(handler.EntityResolver):
    def __init__(self):
        super().__init__()
        self.requests = []

    def resolveEntity(self, public_id, system_id):
        self.requests.append((public_id, system_id))
        source = xmlreader.InputSource(system_id)
        source.setCharacterStream(io.StringIO("resolved text"))
        return source


class TextRecorder(handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.parts = []

    def characters(self, content):
        self.parts.append(content)


class RaisingErrorRecorder(handler.ErrorHandler):
    def __init__(self):
        super().__init__()
        self.fatal = []

    def fatalError(self, exception):
        self.fatal.append(exception)
        raise exception


def test_external_entity_is_resolved_only_after_explicit_feature_opt_in():
    parser = xml.sax.make_parser()
    parser.setFeature(handler.feature_external_ges, True)
    resolver = ControlledResolver()
    content = TextRecorder()
    parser.setEntityResolver(resolver)
    parser.setContentHandler(content)
    source = xmlreader.InputSource()
    source.setCharacterStream(
        io.StringIO(
            '<!DOCTYPE root [<!ENTITY ext SYSTEM "urn:polyglot:entity">]>'
            "<root>&ext;</root>"
        )
    )

    parser.parse(source)

    assert resolver.requests == [(None, "urn:polyglot:entity")]
    assert "".join(content.parts) == "resolved text"


def test_custom_error_handler_can_record_then_propagate_fatal_parse_error():
    parser = xml.sax.make_parser()
    errors = RaisingErrorRecorder()
    parser.setErrorHandler(errors)
    source = xmlreader.InputSource()
    source.setCharacterStream(io.StringIO("<root><item></root>"))

    with pytest.raises(xml.sax.SAXParseException) as caught:
        parser.parse(source)

    assert errors.fatal == [caught.value]
