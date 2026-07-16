"""115｜Expat ParserCreate、基础回调、分块 Parse、ParseFile 与单文档生命周期。

``xml.parsers.expat`` 是 pyexpat 的推荐入口；直接导入 ``pyexpat`` 已弃用。ParserCreate 返回的
stateful parser 通过属性安装回调，``Parse(data, isfinal)`` 可拼接同一文档的输入块，最后一块
必须标 final。一个 parser 只能解析一份 XML；完成后应新建实例，不能把第二份文档继续喂入。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.xml.parsers.expat.ParserCreate
# polyglot-covers: python.xml.parsers.expat.XMLParserType
# polyglot-covers: python.xml.parsers.expat.xmlparser.Parse
# polyglot-covers: python.xml.parsers.expat.xmlparser.ParseFile
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartElementHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndElementHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.CharacterDataHandler
# polyglot-covers: python.xml.parsers.expat.Parse-isfinal
# polyglot-covers: python.xml.parsers.expat-parser-single-document
# polyglot-covers: python.pyexpat-direct-import-deprecated




import io
from xml.parsers import expat
import pytest

def test_parser_callbacks_receive_ordered_structure_from_fragmented_input():
    parser = expat.ParserCreate()
    events = []
    parser.StartElementHandler = lambda name, attrs: events.append(
        ("start", name, attrs)
    )
    parser.EndElementHandler = lambda name: events.append(("end", name))
    parser.CharacterDataHandler = lambda data: events.append(("text", data))

    assert isinstance(parser, expat.XMLParserType)
    parser.Parse("<root id='one'><item>", False)
    parser.Parse("value", False)
    parser.Parse("</item></root>", True)

    structural = [event for event in events if event[0] != "text"]
    assert structural == [
        ("start", "root", {"id": "one"}),
        ("start", "item", {}),
        ("end", "item"),
        ("end", "root"),
    ]
    assert "".join(event[1] for event in events if event[0] == "text") == "value"


def test_parsefile_only_requires_a_binary_read_method():
    parser = expat.ParserCreate()
    names = []
    parser.StartElementHandler = lambda name, attrs: names.append(name)

    parser.ParseFile(io.BytesIO(b"<root><item/></root>"))

    assert names == ["root", "item"]


def test_finished_parser_rejects_a_second_document():
    parser = expat.ParserCreate()
    parser.Parse("<first/>", True)

    with pytest.raises(expat.ExpatError) as caught:
        parser.Parse("<second/>", True)

    assert caught.value.code == expat.errors.codes[expat.errors.XML_ERROR_FINISHED]


# Expat namespace 展开、属性报告模式、文本缓冲与 encoding 覆盖。
#
# ParserCreate 的单字符 separator 开启 namespace，把名字报告为 ``URI + separator + local``。
# ``ordered_attributes`` 改用扁平 name/value 列表保留源顺序；``specified_attributes`` 排除 DTD
# 默认属性。``buffer_text`` 可减少字符回调次数但不能赋予 chunk 语义。显式 encoding 会覆盖声明。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xml.parsers.expat.ParserCreate.encoding
# polyglot-covers: python.xml.parsers.expat.ParserCreate.namespace_separator
# polyglot-covers: python.xml.parsers.expat.namespace-expanded-name
# polyglot-covers: python.xml.parsers.expat.namespace-separator-one-character
# polyglot-covers: python.xml.parsers.expat.xmlparser.ordered_attributes
# polyglot-covers: python.xml.parsers.expat.xmlparser.specified_attributes
# polyglot-covers: python.xml.parsers.expat.xmlparser.buffer_text
# polyglot-covers: python.xml.parsers.expat.xmlparser.buffer_size
# polyglot-covers: python.xml.parsers.expat.xmlparser.buffer_used




def test_namespace_separator_expands_element_and_attribute_names():
    parser = expat.ParserCreate(namespace_separator="|")
    starts = []
    parser.StartElementHandler = lambda name, attrs: starts.append((name, attrs))

    parser.Parse(
        '<root xmlns="urn:root" xmlns:p="urn:parts" p:state="ready">'
        "<p:item/></root>",
        True,
    )

    assert starts[0] == ("urn:root|root", {"urn:parts|state": "ready"})
    assert starts[1] == ("urn:parts|item", {})

    with pytest.raises(ValueError):
        expat.ParserCreate(namespace_separator="too-long")


def test_ordered_attributes_preserve_source_order_as_flat_name_value_list():
    parser = expat.ParserCreate()
    parser.ordered_attributes = True
    seen = []
    parser.StartElementHandler = lambda name, attrs: seen.append(attrs)

    parser.Parse('<root second="2" first="1"/>', True)

    assert seen == [["second", "2", "first", "1"]]


def parse_attributes(specified_only):
    parser = expat.ParserCreate()
    parser.specified_attributes = specified_only
    seen = []
    parser.StartElementHandler = lambda name, attrs: seen.append(attrs)
    parser.Parse(
        '<!DOCTYPE root [<!ATTLIST root defaulted CDATA "yes">]>'
        '<root explicit="x"/>',
        True,
    )
    return seen[-1]


def test_specified_attributes_can_exclude_values_supplied_only_by_the_dtd():
    assert parse_attributes(False) == {"explicit": "x", "defaulted": "yes"}
    assert parse_attributes(True) == {"explicit": "x"}


def test_buffered_text_is_joined_by_content_not_by_callback_boundaries():
    parser = expat.ParserCreate()
    parser.buffer_text = True
    parser.buffer_size = 64
    parts = []
    parser.CharacterDataHandler = parts.append

    parser.Parse("<root>one\ntwo\nthree</root>", True)

    assert "".join(parts) == "one\ntwo\nthree"
    assert parser.buffer_used == 0


def test_parser_encoding_argument_overrides_the_xml_declaration():
    parser = expat.ParserCreate(encoding="iso-8859-1")
    parts = []
    parser.CharacterDataHandler = parts.append

    parser.Parse(
        b'<?xml version="1.0" encoding="UTF-8"?><root>\xe9</root>',
        True,
    )

    assert "".join(parts) == "é"


# Expat XML 声明、DOCTYPE、元素 content model、属性与实体声明回调。
#
# Expat 是 non-validating parser，但会读取声明并以专用 handler 报告。ElementDecl 的 model 是
# ``(type, quantifier, name, children)`` 递归元组，常量来自 ``expat.model``；Attlist 区分默认值
# 与 required。内部、外部和 NDATA 实体在 EntityDecl 的参数组合不同，不能只看 entityName。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xml.parsers.expat.xmlparser.XmlDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartDoctypeDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndDoctypeDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.ElementDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.AttlistDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EntityDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.NotationDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.UnparsedEntityDeclHandler
# polyglot-covers: python.xml.parsers.expat-content-model-tuple
# polyglot-covers: python.xml.parsers.expat.model.XML_CTYPE_SEQ
# polyglot-covers: python.xml.parsers.expat.model.XML_CTYPE_NAME
# polyglot-covers: python.xml.parsers.expat.model.XML_CQUANT_PLUS



XML_TEXT = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE root [
  <!ELEMENT root (item+)>
  <!ELEMENT item (#PCDATA)>
  <!ATTLIST item id ID #REQUIRED>
  <!ENTITY word "hello">
  <!NOTATION png SYSTEM "image/png">
  <!ENTITY logo SYSTEM "logo.png" NDATA png>
]>
<root><item id="one">&word;</item></root>
"""


def test_declaration_handlers_receive_typed_dtd_information():
    parser = expat.ParserCreate()
    declarations = {
        "xml": [],
        "doctype": [],
        "models": {},
        "attributes": [],
        "entities": [],
        "notations": [],
        "unparsed": [],
    }
    parser.XmlDeclHandler = lambda *args: declarations["xml"].append(args)
    parser.StartDoctypeDeclHandler = lambda *args: declarations["doctype"].append(
        ("start", *args)
    )
    parser.EndDoctypeDeclHandler = lambda: declarations["doctype"].append(("end",))
    parser.ElementDeclHandler = lambda name, model_: declarations["models"].update(
        {name: model_}
    )
    parser.AttlistDeclHandler = lambda *args: declarations["attributes"].append(args)
    parser.EntityDeclHandler = lambda *args: declarations["entities"].append(args)
    parser.NotationDeclHandler = lambda *args: declarations["notations"].append(args)
    parser.UnparsedEntityDeclHandler = lambda *args: declarations["unparsed"].append(
        args
    )

    parser.Parse(XML_TEXT, True)

    assert declarations["xml"] == [("1.0", "UTF-8", 1)]
    assert declarations["doctype"] == [
        ("start", "root", None, None, 1),
        ("end",),
    ]

    root_model = declarations["models"]["root"]
    assert root_model[0] == expat.model.XML_CTYPE_SEQ
    assert root_model[3][0][0] == expat.model.XML_CTYPE_NAME
    assert root_model[3][0][1] == expat.model.XML_CQUANT_PLUS
    assert root_model[3][0][2] == "item"

    assert ("item", "id", "ID", None, 1) in declarations["attributes"]
    assert any(event[0] == "word" and event[2] == "hello" for event in declarations["entities"])
    # 注册专用 UnparsedEntityDeclHandler 后，NDATA 实体走该入口，不会再重复交给通用
    # EntityDeclHandler；普通内部实体 word 仍由通用入口报告。
    assert [event[0] for event in declarations["entities"]] == ["word"]
    assert declarations["notations"] == [("png", None, "image/png", None)]
    assert declarations["unparsed"] == [
        ("logo", None, "logo.png", None, "png")
    ]


# Expat PI/comment/CDATA/namespace 回调、DefaultHandler 差异与输入上下文。
#
# CharacterData 无法区分普通文本和 CDATA，必须结合 start/end CDATA 回调。namespace 声明事件
# 在对应 start element 前、end element 后出现。``DefaultHandler`` 会抑制内部实体展开并看到原
# 引用；``DefaultHandlerExpand`` 允许展开。GetInputContext 和当前位置只应在事件回调内解释。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xml.parsers.expat.xmlparser.ProcessingInstructionHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.CommentHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartCdataSectionHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndCdataSectionHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartNamespaceDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndNamespaceDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.DefaultHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.DefaultHandlerExpand
# polyglot-covers: python.xml.parsers.expat.xmlparser.GetInputContext
# polyglot-covers: python.xml.parsers.expat.xmlparser.CurrentLineNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.CurrentColumnNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.CurrentByteIndex



def test_lexical_and_namespace_callbacks_surround_content_events_in_source_order():
    parser = expat.ParserCreate(namespace_separator="|")
    events = []
    contexts = []

    def start(name, attrs):
        events.append(("start", name))
        contexts.append(
            (
                parser.GetInputContext(),
                parser.CurrentLineNumber,
                parser.CurrentColumnNumber,
                parser.CurrentByteIndex,
            )
        )

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: events.append(("end", name))
    parser.StartNamespaceDeclHandler = lambda prefix, uri: events.append(
        ("start-ns", prefix, uri)
    )
    parser.EndNamespaceDeclHandler = lambda prefix: events.append(("end-ns", prefix))
    parser.ProcessingInstructionHandler = lambda target, data: events.append(
        ("pi", target, data)
    )
    parser.CommentHandler = lambda data: events.append(("comment", data))
    parser.StartCdataSectionHandler = lambda: events.append(("start-cdata",))
    parser.EndCdataSectionHandler = lambda: events.append(("end-cdata",))
    parser.CharacterDataHandler = lambda data: events.append(("text", data))

    parser.Parse(
        '<?build fast?><root xmlns:p="urn:p"><p:item><![CDATA[x<y]]>'
        "<!--note--></p:item></root>",
        True,
    )

    assert events.index(("start-ns", "p", "urn:p")) < events.index(
        ("start", "root")
    )
    assert events.index(("end", "root")) < events.index(("end-ns", "p"))
    assert ("pi", "build", "fast") in events
    assert ("start-cdata",) in events and ("end-cdata",) in events
    assert ("text", "x<y") in events
    assert ("comment", "note") in events
    assert all(context is not None for context, *_ in contexts)
    assert all(line >= 1 and column >= 0 and byte >= 0 for _, line, column, byte in contexts)


def test_default_handler_expand_changes_internal_entity_dispatch():
    xml = '<!DOCTYPE root [<!ENTITY word "VALUE">]><root>&word;</root>'
    raw_tokens = []
    raw_chars = []
    raw = expat.ParserCreate()
    raw.DefaultHandler = raw_tokens.append
    raw.CharacterDataHandler = raw_chars.append
    raw.Parse(xml, True)

    expanded_tokens = []
    expanded_chars = []
    expanded = expat.ParserCreate()
    expanded.DefaultHandlerExpand = expanded_tokens.append
    expanded.CharacterDataHandler = expanded_chars.append
    expanded.Parse(xml, True)

    assert "&word;" in "".join(raw_tokens)
    assert raw_chars == []
    assert "&word;" not in "".join(expanded_tokens)
    assert "".join(expanded_chars) == "VALUE"


# ExpatError 的错误码/行列、parser 错误属性与 errors 双向表。
#
# ExpatError 同时给出 ``code``、1-based ``lineno`` 和 0-based ``offset``。parser 上 ErrorCode/
# ErrorLineNumber/ErrorColumnNumber/ErrorByteIndex 只在 Parse/ParseFile 抛错后有意义。errors 常量
# 的值是消息字符串，不是数字；应经 ``errors.codes[constant]`` 比较，再用 messages/ErrorString 展示。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xml.parsers.expat.ExpatError
# polyglot-covers: python.xml.parsers.expat.error
# polyglot-covers: python.xml.parsers.expat.ExpatError.code
# polyglot-covers: python.xml.parsers.expat.ExpatError.lineno
# polyglot-covers: python.xml.parsers.expat.ExpatError.offset
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorCode
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorLineNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorColumnNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.ErrorByteIndex
# polyglot-covers: python.xml.parsers.expat.ErrorString
# polyglot-covers: python.xml.parsers.expat.errors.codes
# polyglot-covers: python.xml.parsers.expat.errors.messages




def test_parse_error_matches_symbolic_code_and_all_location_views():
    parser = expat.ParserCreate()

    with pytest.raises(expat.ExpatError) as caught:
        parser.Parse("<root>\n<item></root>", True)

    error = caught.value
    expected_code = expat.errors.codes[expat.errors.XML_ERROR_TAG_MISMATCH]
    assert expat.error is expat.ExpatError
    assert error.code == parser.ErrorCode == expected_code
    assert error.lineno == parser.ErrorLineNumber == 2
    assert error.offset == parser.ErrorColumnNumber >= 0
    assert parser.ErrorByteIndex >= 0
    assert expat.ErrorString(error.code) == expat.errors.messages[error.code]
    assert expat.errors.XML_ERROR_TAG_MISMATCH == "mismatched tag"


# Expat 外部实体 child parser、base 传递与参数实体/foreign DTD 开关。
#
# Expat 不替应用解析相对 system ID；SetBase 只把 base 传给 external handler。handler 若决定接收
# 实体，必须用 opaque context 创建 ExternalEntityParser、配置回调、提供受控内容并返回非零。
# 参数实体和 foreign DTD 另有显式开关；这些都会扩大输入面，案例不读取网络或真实外部文件。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xml.parsers.expat.xmlparser.SetBase
# polyglot-covers: python.xml.parsers.expat.xmlparser.GetBase
# polyglot-covers: python.xml.parsers.expat.xmlparser.ExternalEntityRefHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.ExternalEntityParserCreate
# polyglot-covers: python.xml.parsers.expat.external-entity-handler-return-contract
# polyglot-covers: python.xml.parsers.expat.external-system-id-resolution-is-application-owned
# polyglot-covers: python.xml.parsers.expat.xmlparser.SetParamEntityParsing
# polyglot-covers: python.xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER
# polyglot-covers: python.xml.parsers.expat.xmlparser.UseForeignDTD
# polyglot-covers: python.xml.parsers.expat.XML_ERROR_CANT_CHANGE_FEATURE_ONCE_PARSING




def test_external_handler_uses_child_parser_with_controlled_in_memory_content():
    parser = expat.ParserCreate()
    parser.ordered_attributes = True
    parser.specified_attributes = True
    parser.SetBase("urn:polyglot:base")
    requests = []
    text = []

    def external(context, base, system_id, public_id):
        child = parser.ExternalEntityParserCreate(context)
        requests.append(
            (
                base,
                system_id,
                public_id,
                bool(child.ordered_attributes),
                bool(child.specified_attributes),
            )
        )
        child.CharacterDataHandler = text.append
        child.Parse("from controlled child", True)
        return 1

    parser.ExternalEntityRefHandler = external
    parser.Parse(
        '<!DOCTYPE root [<!ENTITY ext SYSTEM "part.xml">]>'
        "<root>&ext;</root>",
        True,
    )

    assert parser.GetBase() == "urn:polyglot:base"
    assert requests == [
        ("urn:polyglot:base", "part.xml", None, True, True)
    ]
    assert "".join(text) == "from controlled child"


def test_parameter_entity_and_foreign_dtd_controls_must_be_set_before_parsing():
    parser = expat.ParserCreate()
    assert parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.UseForeignDTD(False)
    # isfinal=False 保持解析器处于“已经开始但尚未结束”的状态；完整解析结束后的调用在部分
    # Expat 补丁版本中只是 no-op，不能用来验证 once-parsing 限制。
    parser.Parse("<root>", False)

    with pytest.raises(expat.ExpatError) as caught:
        parser.UseForeignDTD(True)

    assert caught.value.code == expat.errors.codes[
        expat.errors.XML_ERROR_CANT_CHANGE_FEATURE_ONCE_PARSING
    ]
    parser.Parse("</root>", True)


# Python 3.10 后期回移的 Expat reparse deferral 与内存放大防护 API。
#
# 3.10.14 回移 reparse deferral，避免大而未完成 token 反复解析造成二次复杂度；关闭它会削弱
# 防护，本例只读取并保持当前值。3.10.20 又加入内存分配阈值和最大放大倍数。跨 3.10 patch
# 运行必须 ``hasattr``，不能因主版本相同就假定 API 存在，也不能用真实攻击载荷验证安全机制。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.xml.parsers.expat.xmlparser.SetReparseDeferralEnabled-3.10.14
# polyglot-covers: python.xml.parsers.expat.xmlparser.GetReparseDeferralEnabled-3.10.14
# polyglot-covers: python.xml.parsers.expat.reparse-deferral-large-token-protection
# polyglot-covers: python.xml.parsers.expat.reparse-deferral-version-guard
# polyglot-covers: python.xml.parsers.expat.xmlparser.SetAllocTrackerActivationThreshold-3.10.20
# polyglot-covers: python.xml.parsers.expat.xmlparser.SetAllocTrackerMaximumAmplification-3.10.20
# polyglot-covers: python.xml.parsers.expat.alloc-tracker-version-guard
# polyglot-covers: python.xml.parsers.expat-untrusted-xml-warning



def test_reparse_deferral_is_capability_checked_and_never_disabled_here():
    parser = expat.ParserCreate()
    getter = getattr(parser, "GetReparseDeferralEnabled", None)
    setter = getattr(parser, "SetReparseDeferralEnabled", None)

    assert (getter is None) == (setter is None)
    if getter is not None:
        enabled = getter()
        setter(enabled)
        assert getter() == enabled

    parser.Parse("<root>small trusted input</root>", True)


def test_allocation_protection_settings_are_guarded_by_patch_level():
    parser = expat.ParserCreate()
    set_threshold = getattr(parser, "SetAllocTrackerActivationThreshold", None)
    set_amplification = getattr(
        parser,
        "SetAllocTrackerMaximumAmplification",
        None,
    )

    assert (set_threshold is None) == (set_amplification is None)
    if set_threshold is not None:
        # 使用文档默认值，不降低防护，也不构造资源耗尽输入。
        assert set_threshold(67_108_864) is None
        assert set_amplification(100.0) is None

    parser.Parse("<root/>", True)
