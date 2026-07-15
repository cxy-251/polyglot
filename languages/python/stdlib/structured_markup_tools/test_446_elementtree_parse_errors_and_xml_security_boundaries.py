"""446｜``ParseError`` 诊断信息与 XML 不可信输入的安全边界。

``ParseError`` 附带 Expat 错误码和 ``(line, column)`` 位置，适合向调用者报告结构错误。标准库
XML 解析器不是处理恶意 XML 的安全边界：实体会展开，巨量实体、深层嵌套和大 token 的防护还
依赖当前链接的 Expat 修订版。这里只用一个微小实体说明机制，绝不构造资源耗尽载荷。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.ParseError
# polyglot-covers: python.xml.etree.ElementTree.ParseError.code
# polyglot-covers: python.xml.etree.ElementTree.ParseError.position
# polyglot-covers: python.xml.etree.ElementTree.mismatched-tag-error
# polyglot-covers: python.xml.etree.ElementTree.undefined-entity-error
# polyglot-covers: python.xml-security-untrusted-data-warning
# polyglot-covers: python.xml-security-entity-expansion-mechanism
# polyglot-covers: python.xml-security-expat-patch-level-dependency

from xml.etree import ElementTree as ET

import pytest


def test_parse_error_exposes_machine_readable_code_and_source_position():
    with pytest.raises(ET.ParseError) as caught:
        ET.fromstring("<root>\n  <item>value</root>")

    error = caught.value
    assert isinstance(error.code, int)
    assert error.position[0] == 2
    assert error.position[1] > 0
    assert "mismatched tag" in str(error)


def test_undefined_entity_is_a_parse_error_instead_of_literal_text():
    with pytest.raises(ET.ParseError, match="undefined entity"):
        ET.fromstring("<root>&missing;</root>")


def test_tiny_internal_entity_demonstrates_why_untrusted_xml_needs_limits():
    xml = '<!DOCTYPE root [<!ENTITY word "safe">]><root>&word;</root>'

    root = ET.fromstring(xml)

    assert root.text == "safe"
    # 这里仅证明解析器会做替换；切勿把“能解析”误当作可安全接收恶意 XML。
