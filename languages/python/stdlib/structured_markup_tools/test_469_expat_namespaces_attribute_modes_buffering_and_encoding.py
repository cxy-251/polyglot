"""469｜Expat namespace 展开、属性报告模式、文本缓冲与 encoding 覆盖。

ParserCreate 的单字符 separator 开启 namespace，把名字报告为 ``URI + separator + local``。
``ordered_attributes`` 改用扁平 name/value 列表保留源顺序；``specified_attributes`` 排除 DTD
默认属性。``buffer_text`` 可减少字符回调次数但不能赋予 chunk 语义。显式 encoding 会覆盖声明。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.parsers.expat.ParserCreate.encoding
# polyglot-covers: python.xml.parsers.expat.ParserCreate.namespace_separator
# polyglot-covers: python.xml.parsers.expat.namespace-expanded-name
# polyglot-covers: python.xml.parsers.expat.namespace-separator-one-character
# polyglot-covers: python.xml.parsers.expat.xmlparser.ordered_attributes
# polyglot-covers: python.xml.parsers.expat.xmlparser.specified_attributes
# polyglot-covers: python.xml.parsers.expat.xmlparser.buffer_text
# polyglot-covers: python.xml.parsers.expat.xmlparser.buffer_size
# polyglot-covers: python.xml.parsers.expat.xmlparser.buffer_used

from xml.parsers import expat

import pytest


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
