"""114｜SAX ``make_parser``、文件/字符串便捷入口与 SAXParseException。

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
from xml.sax import saxutils

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


# SAX ContentHandler 回调顺序、Locator 有效期与字符分块陷阱。
#
# 事件顺序映射源文档顺序，``setDocumentLocator`` 若提供必先于其他内容事件。Locator 只保证在
# 回调期间位置准确，需立即复制行列。``characters()`` 的 chunk 边界没有语义保证，同一连续文本
# 可能被拆成多次回调；消费方应累积后在 endElement 处解释，不能把一次回调当作完整字段。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# SAX namespace 模式、prefix scope 与 AttributesNS。
#
# 开启 ``feature_namespaces`` 后，元素/属性名用 ``(URI, localName)`` 报告，源 qname 允许为 None。
# 普通无前缀属性不继承默认命名空间。prefix mapping 事件包围对应元素，但多个 mapping 的相对
# 嵌套顺序不保证；若 QName 出现在文本或属性值中，应用需利用 scope 事件自行解释。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# XMLReader handler 配置、feature/property 错误与 IncrementalParser 生命周期。
#
# XMLReader 分别持有 content、DTD、entity resolver 和 error handler。feature 必须在解析前设置，
# 未知名称与实现不支持的值由两种 SAX 异常区分。增量 reader 可 ``feed`` 分块并以 ``close`` 检查
# 文档结尾；close 后若要解析下一份文档必须先 ``reset``，直接复用的结果没有定义。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# SAX InputSource 标识符、byte/character stream 优先级与输入准备。
#
# InputSource 可同时保存 public/system ID、encoding、byte stream 和 character stream。若 character
# stream 存在，解析器会忽略 byte stream、其 encoding 以及自行打开 system ID；这是注入已解码
# 受控输入、避免意外 I/O 的关键。``prepare_input_source`` 统一包装字符串、file-like 或已有对象。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.sax.xmlreader.InputSource
# polyglot-covers: python.xml.sax.xmlreader.InputSource.publicId
# polyglot-covers: python.xml.sax.xmlreader.InputSource.systemId
# polyglot-covers: python.xml.sax.xmlreader.InputSource.encoding
# polyglot-covers: python.xml.sax.xmlreader.InputSource.byteStream
# polyglot-covers: python.xml.sax.xmlreader.InputSource.characterStream
# polyglot-covers: python.xml.sax.InputSource-character-stream-precedence
# polyglot-covers: python.xml.sax.saxutils.prepare_input_source



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


# SAX Attributes/AttributesNS 的 DOM 风格查询与 Python mapping 协议。
#
# 非 namespace 属性以字符串键保存；namespace 版本用 ``(URI, localName)`` 键并另存源 qname。
# 两者都实现 copy/get/contains/items/keys/values，以及 getLength/getNames/getType/getValue。属性对象
# 可能被 parser 复用，因此需要长期保存时复制普通 dict，而不是持有回调参数本身。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.sax.xmlreader.AttributesImpl
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getLength
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getNames
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getType
# polyglot-covers: python.xml.sax.xmlreader.Attributes.getValue
# polyglot-covers: python.xml.sax.xmlreader.Attributes-mapping-protocol
# polyglot-covers: python.xml.sax.xmlreader.AttributesNSImpl
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getValueByQName
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getNameByQName
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getQNameByName
# polyglot-covers: python.xml.sax.xmlreader.AttributesNS.getQNames



def test_attributes_impl_supports_sax_queries_and_mapping_operations():
    attrs = xmlreader.AttributesImpl({"id": "one", "empty": ""})

    assert attrs.getLength() == len(attrs) == 2
    assert set(attrs.getNames()) == {"id", "empty"}
    assert attrs.getType("id") == "CDATA"
    assert attrs.getValue("id") == attrs["id"] == "one"
    assert "empty" in attrs
    assert attrs.get("missing", "fallback") == "fallback"
    assert attrs.copy() == {"id": "one", "empty": ""}
    assert dict(attrs.items()) == {"id": "one", "empty": ""}


def test_attributes_ns_maps_expanded_names_to_original_qualified_names():
    state = ("urn:state", "mode")
    plain = (None, "plain")
    attrs = xmlreader.AttributesNSImpl(
        {state: "ready", plain: "value"},
        {state: "s:mode", plain: "plain"},
    )

    assert attrs.getValue(state) == "ready"
    assert attrs.getValueByQName("s:mode") == "ready"
    assert attrs.getNameByQName("s:mode") == state
    assert attrs.getQNameByName(state) == "s:mode"
    assert set(attrs.getQNames()) == {"s:mode", "plain"}
    assert set(attrs.getNames()) == {state, plain}


# SAX DTDHandler 与可选 LexicalHandler 的低频结构事件。
#
# ContentHandler 不报告 comment、CDATA 边界或 DTD 边界；需要这些词法信息时，把 LexicalHandler
# 作为 ``property_lexical_handler`` 注册。DTDHandler 只处理 notation 和未解析实体声明。CDATA
# 内容仍走 characters，词法回调只标记边界。案例只解析内部声明，不访问外部 system ID。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# SAX EntityResolver、ErrorHandler 与外部实体显式启用边界。
#
# 默认外部通用实体关闭。确需支持时，必须显式开启 feature，并用 EntityResolver 将 system ID
# 映射到受控 InputSource；返回原 URL 会把 I/O 决策交还 parser。ErrorHandler 决定 warning/error/
# fatalError 是否抛出；不可恢复错误通常记录后重新抛出传入 SAXParseException。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.sax.handler.EntityResolver
# polyglot-covers: python.xml.sax.handler.EntityResolver.resolveEntity
# polyglot-covers: python.xml.sax.handler.ErrorHandler
# polyglot-covers: python.xml.sax.handler.ErrorHandler.warning
# polyglot-covers: python.xml.sax.handler.ErrorHandler.error
# polyglot-covers: python.xml.sax.handler.ErrorHandler.fatalError
# polyglot-covers: python.xml.sax.handler.feature_external_ges
# polyglot-covers: python.xml.sax.external-entity-explicit-opt-in
# polyglot-covers: python.xml.sax.controlled-inputsource-from-resolver




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


# saxutils 文本转义、反转义与可直接拼入标签的属性引用。
#
# ``escape`` 始终处理 ``&<>``，附加 entities 只扩充规则，不能覆盖核心 XML 转义。``unescape``
# 只认识 ``&amp;``/``&lt;``/``&gt;`` 和调用方规则，不是通用实体解析器。``quoteattr`` 连外层引号
# 一起返回，并选择能减少转义的引号；双/单引号同时出现时使用双引号并转义其中的双引号。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.sax.saxutils.escape
# polyglot-covers: python.xml.sax.saxutils.escape.entities
# polyglot-covers: python.xml.sax.saxutils.unescape
# polyglot-covers: python.xml.sax.saxutils.unescape.entities
# polyglot-covers: python.xml.sax.saxutils.quoteattr
# polyglot-covers: python.xml.sax.saxutils.quoteattr-selects-delimiter
# polyglot-covers: python.xml.sax.saxutils-not-general-translation



def test_escape_always_handles_xml_metacharacters_and_then_custom_entities():
    escaped = saxutils.escape(
        "5 < 6 & 7 > 3 ©",
        {"©": "&copy;"},
    )

    assert escaped == "5 &lt; 6 &amp; 7 &gt; 3 &copy;"


def test_unescape_handles_only_the_builtin_and_explicit_entity_spellings():
    unescaped = saxutils.unescape(
        "&lt;tag&gt;&amp;&copy;&unknown;",
        {"&copy;": "©"},
    )

    assert unescaped == "<tag>&©&unknown;"
    # 单轮顺序不会递归解码：&amp;lt; 先留下 &lt;，不会在同次调用中再变成 '<'。
    assert saxutils.unescape("&amp;lt;") == "&lt;"


def test_quoteattr_returns_delimiters_and_chooses_the_less_costly_quote_style():
    assert saxutils.quoteattr("plain") == '"plain"'
    assert saxutils.quoteattr('has "double"') == "'has \"double\"'"
    assert saxutils.quoteattr("has 'single'") == '"has \'single\'"'
    assert saxutils.quoteattr("both ' and \"") == '"both \' and &quot;"'


# XMLGenerator 从 SAX 事件生成 XML、命名空间声明与空元素样式。
#
# XMLGenerator 是 ContentHandler，可接在 parser 或 filter 后把事件重新写成 XML。它负责转义
# 文本/属性并输出 encoding 声明；``short_empty_elements`` 只改变无内容元素的表层写法。namespace
# 模式要先提供 prefix mapping，AttributesNS 同时携带扩展名与用于输出的 qname。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# XMLFilterBase 在 XMLReader 与下游 handler 之间转换事件。
#
# filter 的配置请求向上转发给 parent reader，parent 产生的事件再经 filter 向下游转发。基类默认
# 透明透传；子类只覆盖关心的回调即可实现重命名、内容清洗或审计。filter 仍是流式模型，不能在
# startElement 中向后查看尚未出现的内容；需要随机访问时应改用 DOM/ElementTree。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase.parse
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase-handler-forwarding
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase-feature-forwarding
# polyglot-covers: python.xml.sax.saxutils.XMLFilterBase-transform-event-stream



class RenamingUppercaseFilter(saxutils.XMLFilterBase):
    def startElement(self, name, attrs):
        renamed = "entry" if name == "item" else name
        super().startElement(renamed, attrs)

    def endElement(self, name):
        renamed = "entry" if name == "item" else name
        super().endElement(renamed)

    def characters(self, content):
        super().characters(content.upper())


def test_filter_forwards_configuration_and_transforms_events_before_generation():
    reader = xml.sax.make_parser()
    filter_ = RenamingUppercaseFilter(reader)
    output = io.StringIO()
    generator = saxutils.XMLGenerator(output, encoding="utf-8")
    filter_.setContentHandler(generator)
    filter_.setFeature(handler.feature_namespaces, False)

    assert filter_.getContentHandler() is generator
    assert not filter_.getFeature(handler.feature_namespaces)

    filter_.parse(io.StringIO("<root><item>value</item></root>"))

    assert "<root><entry>VALUE</entry></root>" in output.getvalue()
