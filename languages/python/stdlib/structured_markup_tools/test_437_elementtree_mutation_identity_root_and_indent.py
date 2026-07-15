"""437｜ElementTree 节点移除、根替换与 ``indent()`` 的可变语义。

``Element.remove()`` 按对象身份寻找子节点，不会按 tag、属性或序列化内容做值比较。遍历时
直接改变 children 会令遍历结果未定义，稳妥做法是先保存快照。``_setroot()`` 会整体替换树根；
``indent()`` 通过改写 ``text``/``tail`` 加入空白，适合输出副本，不是无副作用的格式化视图。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.Element.remove
# polyglot-covers: python.xml.etree.ElementTree.remove-compares-child-identity
# polyglot-covers: python.xml.etree.ElementTree.remove-missing-valueerror
# polyglot-covers: python.xml.etree.ElementTree.mutation-during-iteration-undefined
# polyglot-covers: python.xml.etree.ElementTree.snapshot-before-child-removal
# polyglot-covers: python.xml.etree.ElementTree.ElementTree._setroot
# polyglot-covers: python.xml.etree.ElementTree.indent
# polyglot-covers: python.xml.etree.ElementTree.indent-mutates-text-and-tail

from xml.etree import ElementTree as ET

import pytest


def test_remove_matches_the_exact_child_object_not_an_equal_looking_node():
    root = ET.Element("root")
    first = ET.SubElement(root, "item", id="same")
    second = ET.SubElement(root, "item", id="same")

    root.remove(second)

    assert list(root) == [first]
    with pytest.raises(ValueError):
        root.remove(ET.Element("item", {"id": "same"}))


def test_filtering_children_uses_a_snapshot_before_mutating_the_tree():
    root = ET.fromstring(
        "<root><item keep='yes'/><item/><item keep='yes'/><item/></root>"
    )

    # Element.iter() 期间改变树结构的结果没有定义；list(root) 固定本轮候选集合。
    for child in list(root):
        if child.get("keep") != "yes":
            root.remove(child)

    assert [child.get("keep") for child in root] == ["yes", "yes"]


def test_setroot_replaces_the_entire_document_root():
    old_root = ET.fromstring("<old><child/></old>")
    tree = ET.ElementTree(old_root)
    new_root = ET.Element("new")

    tree._setroot(new_root)

    assert tree.getroot() is new_root
    assert tree.getroot() is not old_root
    assert len(tree.getroot()) == 0


def test_indent_pretty_prints_by_mutating_text_and_tail_whitespace():
    root = ET.fromstring("<root><first/><second/></root>")

    ET.indent(root, space="  ")

    assert root.text == "\n  "
    assert root[0].tail == "\n  "
    assert root[1].tail == "\n"
    assert ET.tostring(root, encoding="unicode") == (
        "<root>\n  <first />\n  <second />\n</root>"
    )
