"""434｜Element 的属性映射、子节点序列、浅复制、itertext 与 clear。

attrib 是活 dict；get/set/keys/items 操作同一对象。Element 同时实现可变序列协议，append/
extend/insert 和索引切片都直接管理 child 对象。copy.copy 复制容器和属性字典但仍共享 child；
clear 会删除 children/attributes 并把 text/tail 置 None。空 Element 在 3.10 中是假值，勿拿它判空缺。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.Element.get
# polyglot-covers: python.xml.etree.ElementTree.Element.set
# polyglot-covers: python.xml.etree.ElementTree.Element.keys
# polyglot-covers: python.xml.etree.ElementTree.Element.items
# polyglot-covers: python.xml.etree.ElementTree.Element.attrib-live-dict
# polyglot-covers: python.xml.etree.ElementTree.Element.append
# polyglot-covers: python.xml.etree.ElementTree.Element.extend
# polyglot-covers: python.xml.etree.ElementTree.Element.insert
# polyglot-covers: python.xml.etree.ElementTree.Element-sequence-protocol
# polyglot-covers: python.xml.etree.ElementTree.Element-shallow-copy-shares-children
# polyglot-covers: python.xml.etree.ElementTree.Element.itertext
# polyglot-covers: python.xml.etree.ElementTree.Element.clear
# polyglot-covers: python.xml.etree.ElementTree.empty-element-false-trap

from copy import copy
from xml.etree import ElementTree as ET


def test_attribute_helpers_and_attrib_reference_mutate_the_same_mapping():
    element = ET.Element("item", {"a": "1"})
    live_attributes = element.attrib
    element.set("b", "2")
    live_attributes["c"] = "3"

    assert element.get("a") == "1"
    assert element.get("missing", "fallback") == "fallback"
    assert element.keys() == ["a", "b", "c"]
    assert element.items() == [("a", "1"), ("b", "2"), ("c", "3")]


def test_children_follow_mutable_sequence_order_and_shallow_copy_shares_nodes():
    root = ET.Element("root")
    one = ET.Element("one")
    two = ET.Element("two")
    zero = ET.Element("zero")
    root.append(one)
    root.extend([two])
    root.insert(0, zero)

    assert [child.tag for child in root] == ["zero", "one", "two"]
    assert root[1] is one
    assert [child.tag for child in root[1:]] == ["one", "two"]

    cloned = copy(root)
    cloned.attrib["copy-only"] = "yes"
    cloned[0].set("shared", "yes")
    assert "copy-only" not in root.attrib
    assert root[0].get("shared") == "yes"


def test_itertext_includes_descendant_text_and_tails_in_document_order():
    root = ET.fromstring("<root>before<a>A<b>B</b>tail-b</a>tail-a</root>")
    assert list(root.itertext()) == ["before", "A", "B", "tail-b", "tail-a"]
    assert "".join(root.itertext()) == "beforeABtail-btail-a"


def test_clear_resets_complete_node_state_and_empty_element_is_false_in_310():
    root = ET.fromstring("<root a='1'>text<child />tail</root>")
    root.clear()

    assert root.tag == "root"
    assert root.attrib == {}
    assert root.text is None
    assert root.tail is None
    assert len(root) == 0
    assert bool(root) is False
    assert root is not None
