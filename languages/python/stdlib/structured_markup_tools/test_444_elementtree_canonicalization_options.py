"""444｜C14N 的空白、排除项、前缀重写与 QName 感知选项。

规范化默认保留文本空白；``strip_text`` 会改变字符数据，不能为追求“整齐”随意开启。过滤
tag/属性会改变文档含义，只适合调用方明确排除的元数据。``rewrite_prefixes`` 可消除原前缀选择
差异；若 QName 写在文本或属性值中，必须声明 qname-aware 集合才能同步重写其词法前缀。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.with_comments
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.strip_text
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.rewrite_prefixes
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.qname_aware_tags
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.qname_aware_attrs
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.exclude_attrs
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget.exclude_tags
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-semantic-options-trap

from xml.etree import ElementTree as ET


def test_strip_and_exclude_options_make_explicit_semantic_changes():
    xml = '<root keep="yes" secret="x">  value  <skip>hidden</skip></root>'

    canonical = ET.canonicalize(
        xml,
        strip_text=True,
        exclude_attrs={"secret"},
        exclude_tags={"skip"},
    )

    assert canonical == '<root keep="yes">value</root>'


def test_rewrite_prefixes_also_rewrites_declared_qname_text_and_attributes():
    xml = (
        '<root xmlns:p="urn:parts">'
        '<kind>p:item</kind><node type="p:special"/>'
        "</root>"
    )

    canonical = ET.canonicalize(
        xml,
        rewrite_prefixes=True,
        qname_aware_tags={"kind"},
        qname_aware_attrs={"type"},
    )

    assert "p:item" not in canonical
    assert "p:special" not in canonical
    assert "urn:parts" in canonical
    assert ":item" in canonical
    assert ":special" in canonical


def test_comments_are_retained_only_when_requested():
    xml = "<root><!--audit--><item/></root>"

    assert "<!--audit-->" not in ET.canonicalize(xml)
    assert "<!--audit-->" in ET.canonicalize(xml, with_comments=True)
