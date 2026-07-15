"""473｜Expat 外部实体 child parser、base 传递与参数实体/foreign DTD 开关。

Expat 不替应用解析相对 system ID；SetBase 只把 base 传给 external handler。handler 若决定接收
实体，必须用 opaque context 创建 ExternalEntityParser、配置回调、提供受控内容并返回非零。
参数实体和 foreign DTD 另有显式开关；这些都会扩大输入面，案例不读取网络或真实外部文件。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from xml.parsers import expat

import pytest


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
    parser.Parse("<root/>", True)

    with pytest.raises(expat.ExpatError) as caught:
        parser.UseForeignDTD(True)

    assert caught.value.code == expat.errors.codes[
        expat.errors.XML_ERROR_CANT_CHANGE_FEATURE_ONCE_PARSING
    ]
