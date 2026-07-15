"""449｜minidom 插入、替换、移除、节点搬移与 DocumentFragment 拼接。

节点只能有一个 parent；把已有节点 append 到新位置会先从旧位置移除，并同步兄弟链接。
``DocumentFragment`` 本身不会成为 child，插入时只把其中节点依次拼入目标并清空 fragment。
引用节点不属于目标或层级不合法时，minidom 使用带 DOM 错误码的具体异常。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.dom.Node.appendChild
# polyglot-covers: python.xml.dom.Node.insertBefore
# polyglot-covers: python.xml.dom.Node.removeChild
# polyglot-covers: python.xml.dom.Node.replaceChild
# polyglot-covers: python.xml.dom.Node-moving-existing-child
# polyglot-covers: python.xml.dom.Document.createDocumentFragment
# polyglot-covers: python.xml.dom.DocumentFragment-splices-children
# polyglot-covers: python.xml.dom.NotFoundErr
# polyglot-covers: python.xml.dom.HierarchyRequestErr
# polyglot-covers: python.xml.dom.DOMException.code

import xml.dom
from xml.dom import minidom

import pytest


def test_insert_append_and_move_keep_parent_and_sibling_links_consistent():
    document = minidom.parseString("<root/>")
    root = document.documentElement
    first = document.createElement("first")
    second = document.createElement("second")

    assert root.appendChild(second) is second
    assert root.insertBefore(first, second) is first
    assert [node.tagName for node in root.childNodes] == ["first", "second"]
    assert first.nextSibling is second
    assert second.previousSibling is first

    # first 已有 parent；再次 append 表示搬到末尾，不会复制节点。
    root.appendChild(first)
    assert [node.tagName for node in root.childNodes] == ["second", "first"]
    assert first.parentNode is root
    assert first.previousSibling is second


def test_replace_and_remove_return_detached_old_nodes():
    document = minidom.parseString("<root><old/><tail/></root>")
    root = document.documentElement
    old = root.firstChild
    replacement = document.createElement("new")

    assert root.replaceChild(replacement, old) is old
    assert old.parentNode is None
    assert replacement.nextSibling.tagName == "tail"

    assert root.removeChild(replacement) is replacement
    assert replacement.parentNode is None
    assert [node.tagName for node in root.childNodes] == ["tail"]


def test_document_fragment_splices_its_children_and_becomes_empty():
    document = minidom.parseString("<root/>")
    root = document.documentElement
    fragment = document.createDocumentFragment()
    fragment.appendChild(document.createElement("one"))
    fragment.appendChild(document.createTextNode("between"))
    fragment.appendChild(document.createElement("two"))

    assert root.appendChild(fragment) is fragment
    assert fragment.childNodes.length == 0
    assert [node.nodeName for node in root.childNodes] == [
        "one",
        "#text",
        "two",
    ]
    assert all(node.parentNode is root for node in root.childNodes)


def test_invalid_reference_and_child_type_raise_specific_dom_exceptions():
    document = minidom.parseString("<root/>")
    root = document.documentElement

    with pytest.raises(xml.dom.NotFoundErr):
        root.removeChild(document.createElement("missing"))

    text = document.createTextNode("leaf")
    with pytest.raises(xml.dom.HierarchyRequestErr) as caught:
        text.appendChild(document.createElement("impossible"))

    assert caught.value.code == xml.dom.HIERARCHY_REQUEST_ERR
