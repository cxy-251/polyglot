"""432｜ElementTree 从字符串、片段列表、文件解析，以及 XMLID/dump/iselement。

fromstring/XML 返回根 Element，parse 返回持有根的 ElementTree；ElementTree.parse 会替换当前
tree 的根并返回该 Element。fromstringlist 适合已经分块但完整的 XML。XMLID 额外收集普通
``id`` 属性。iselement 只检查 Element 协议而非严格类型，dump 只用于调试输出。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.fromstring
# polyglot-covers: python.xml.etree.ElementTree.XML
# polyglot-covers: python.xml.etree.ElementTree.fromstringlist
# polyglot-covers: python.xml.etree.ElementTree.parse
# polyglot-covers: python.xml.etree.ElementTree.ElementTree
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.parse
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.getroot
# polyglot-covers: python.xml.etree.ElementTree.XMLID
# polyglot-covers: python.xml.etree.ElementTree.iselement
# polyglot-covers: python.xml.etree.ElementTree.iselement-protocol-not-type-check
# polyglot-covers: python.xml.etree.ElementTree.dump

from xml.etree import ElementTree as ET


XML_TEXT = "<catalog><item id='a'>Alpha</item><item id='b'>Beta</item></catalog>"


def test_string_and_fragment_parsers_return_the_document_element():
    from_string = ET.fromstring(XML_TEXT)
    from_alias = ET.XML(XML_TEXT.encode())
    from_fragments = ET.fromstringlist(
        ["<catalog>", "<item id='a'>Alpha</item>", "</catalog>"]
    )

    assert from_string.tag == from_alias.tag == from_fragments.tag == "catalog"
    assert [item.text for item in from_string] == ["Alpha", "Beta"]
    assert from_fragments[0].attrib == {"id": "a"}


def test_module_and_tree_parse_have_different_return_shapes(tmp_path):
    path = tmp_path / "catalog.xml"
    path.write_text(XML_TEXT, encoding="utf-8")

    parsed_tree = ET.parse(path)
    reusable_tree = ET.ElementTree()
    returned_root = reusable_tree.parse(path)

    assert isinstance(parsed_tree, ET.ElementTree)
    assert parsed_tree.getroot().tag == "catalog"
    assert returned_root is reusable_tree.getroot()
    assert returned_root[1].text == "Beta"


def test_xmlid_collects_id_attributes_while_iselement_is_a_protocol_check():
    root, by_id = ET.XMLID(XML_TEXT)
    assert by_id == {"a": root[0], "b": root[1]}

    class ElementLike:
        tag = "duck"

    assert ET.iselement(root) is True
    assert ET.iselement(ElementLike()) is True
    assert ET.iselement(object()) is False


def test_dump_writes_a_debug_serialization_to_standard_output(capsys):
    root = ET.fromstring("<root><child /></root>")
    assert ET.dump(root) is None
    assert capsys.readouterr().out == "<root><child /></root>\n"
