"""459｜SAX namespace 模式、prefix scope 与 AttributesNS。

开启 ``feature_namespaces`` 后，元素/属性名用 ``(URI, localName)`` 报告，源 qname 允许为 None。
普通无前缀属性不继承默认命名空间。prefix mapping 事件包围对应元素，但多个 mapping 的相对
嵌套顺序不保证；若 QName 出现在文本或属性值中，应用需利用 scope 事件自行解释。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.handler.feature_namespaces
# polyglot-covers: python.xml.sax.handler.feature_namespace_prefixes
# polyglot-covers: python.xml.sax.handler.ContentHandler.startPrefixMapping
# polyglot-covers: python.xml.sax.handler.ContentHandler.endPrefixMapping
# polyglot-covers: python.xml.sax.handler.ContentHandler.startElementNS
# polyglot-covers: python.xml.sax.handler.ContentHandler.endElementNS
# polyglot-covers: python.xml.sax.namespace-name-uri-local-tuple
# polyglot-covers: python.xml.sax.namespace-qname-may-be-none
# polyglot-covers: python.xml.sax.default-namespace-does-not-apply-to-attributes
# polyglot-covers: python.xml.sax.prefix-mapping-order-not-guaranteed

import io
import xml.sax
from xml.sax import handler
from xml.sax import xmlreader


class NamespaceRecorder(handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.mappings_started = []
        self.mappings_ended = []
        self.started = []
        self.ended = []

    def startPrefixMapping(self, prefix, uri):
        self.mappings_started.append((prefix, uri))

    def endPrefixMapping(self, prefix):
        self.mappings_ended.append(prefix)

    def startElementNS(self, name, qname, attrs):
        self.started.append((name, qname, attrs.copy()))

    def endElementNS(self, name, qname):
        self.ended.append((name, qname))


def test_namespace_mode_expands_names_and_reports_prefix_scope_separately():
    parser = xml.sax.make_parser()
    parser.setFeature(handler.feature_namespaces, True)
    recorder = NamespaceRecorder()
    parser.setContentHandler(recorder)
    source = xmlreader.InputSource()
    source.setCharacterStream(
        io.StringIO(
            '<root xmlns="urn:root" xmlns:p="urn:parts" '
            'p:state="ready" plain="x"><p:item/></root>'
        )
    )

    parser.parse(source)

    assert set(recorder.mappings_started) == {
        (None, "urn:root"),
        ("p", "urn:parts"),
    }
    assert set(recorder.mappings_ended) == {None, "p"}
    root_name, root_qname, root_attrs = recorder.started[0]
    assert root_name == ("urn:root", "root")
    assert root_qname is None
    assert root_attrs[("urn:parts", "state")] == "ready"
    assert root_attrs[(None, "plain")] == "x"
    assert recorder.started[1][0] == ("urn:parts", "item")
    assert recorder.ended[-1][0] == ("urn:root", "root")
