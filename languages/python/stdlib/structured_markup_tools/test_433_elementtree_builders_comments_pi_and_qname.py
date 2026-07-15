"""433｜Element/SubElement、Comment、ProcessingInstruction、QName 与 text/tail。

Element 是 tag、可变 attrib 和有序 children 的节点；SubElement 创建并立即 append，makeelement
只创建同类节点而不挂树。text 位于开始/结束标签之间，tail 位于本元素结束标签之后，二者不能
互换。Comment/PI 使用特殊 tag 哨兵，QName 用 ``{uri}local`` 形式表达扩展名。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.Element
# polyglot-covers: python.xml.etree.ElementTree.Element.tag
# polyglot-covers: python.xml.etree.ElementTree.Element.attrib
# polyglot-covers: python.xml.etree.ElementTree.SubElement
# polyglot-covers: python.xml.etree.ElementTree.Element.makeelement
# polyglot-covers: python.xml.etree.ElementTree.Element.text
# polyglot-covers: python.xml.etree.ElementTree.Element.tail
# polyglot-covers: python.xml.etree.ElementTree.Comment
# polyglot-covers: python.xml.etree.ElementTree.ProcessingInstruction
# polyglot-covers: python.xml.etree.ElementTree.QName
# polyglot-covers: python.xml.etree.ElementTree-expanded-name-syntax
# polyglot-covers: python.xml.etree.ElementTree.attribute-insertion-order

from xml.etree import ElementTree as ET


def test_element_and_subelement_build_an_ordered_tree_with_text_and_tail():
    root = ET.Element("root", {"first": "1"}, second="2")
    first = ET.SubElement(root, "child", role="first")
    first.text = "inside"
    first.tail = "after-child"
    second = ET.SubElement(root, "child", role="second")

    assert root.tag == "root"
    assert list(root.attrib.items()) == [("first", "1"), ("second", "2")]
    assert list(root) == [first, second]
    assert first.text == "inside"
    assert first.tail == "after-child"


def test_makeelement_returns_a_compatible_unattached_node():
    root = ET.Element("root")
    child = root.makeelement("child", {"id": "one"})

    assert ET.iselement(child)
    assert child.tag == "child"
    assert child.attrib == {"id": "one"}
    assert len(root) == 0


def test_comment_processing_instruction_and_qname_serialize_as_markup_nodes():
    root = ET.Element("root")
    root.append(ET.Comment("note"))
    root.append(ET.ProcessingInstruction("build", "mode='fast'"))
    namespaced = ET.SubElement(root, ET.QName("urn:demo", "item"))
    namespaced.set("kind", ET.QName("urn:demo", "special"))

    assert str(ET.QName("urn:demo", "item")) == "{urn:demo}item"
    wire = ET.tostring(root, encoding="unicode")
    assert "<!--note-->" in wire
    assert "<?build mode='fast'?>" in wire
    assert "urn:demo" in wire
