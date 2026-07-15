"""450｜minidom 普通/命名空间属性、Attr 所有权与 NamedNodeMap。

``getAttribute()`` 对不存在和显式空值都返回空字符串，必须配合 ``hasAttribute()`` 区分。
namespace API 以 ``(namespaceURI, localName)`` 定位，却在 set 时接收完整 qname。Attr 节点一次
只能归一个 Element；NamedNodeMap 是属性字典的活视图，其 mapping 扩展不属于核心 DOM 保证。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.dom.Element.hasAttribute
# polyglot-covers: python.xml.dom.Element.getAttribute
# polyglot-covers: python.xml.dom.Element.setAttribute
# polyglot-covers: python.xml.dom.Element.removeAttribute
# polyglot-covers: python.xml.dom.Element.getAttributeNode
# polyglot-covers: python.xml.dom.Element.setAttributeNode
# polyglot-covers: python.xml.dom.Element.removeAttributeNode
# polyglot-covers: python.xml.dom.Element.hasAttributeNS
# polyglot-covers: python.xml.dom.Element.getAttributeNS
# polyglot-covers: python.xml.dom.Element.setAttributeNS
# polyglot-covers: python.xml.dom.Element.getAttributeNodeNS
# polyglot-covers: python.xml.dom.Attr.ownerElement
# polyglot-covers: python.xml.dom.NamedNodeMap.length
# polyglot-covers: python.xml.dom.NamedNodeMap.item
# polyglot-covers: python.xml.dom.NamedNodeMap-mapping-extensions
# polyglot-covers: python.xml.dom.InuseAttributeErr

import xml.dom
from xml.dom import minidom

import pytest


def test_missing_and_explicit_empty_attributes_need_hasattribute_to_distinguish():
    root = minidom.parseString('<root empty=""/>').documentElement

    assert root.getAttribute("missing") == root.getAttribute("empty") == ""
    assert not root.hasAttribute("missing")
    assert root.hasAttribute("empty")

    root.setAttribute("plain", "value")
    assert root.getAttributeNode("plain").value == "value"
    root.removeAttribute("plain")
    assert not root.hasAttribute("plain")


def test_namespaced_attributes_keep_uri_local_name_prefix_and_qname_separate():
    document = minidom.parseString("<root/>")
    root = document.documentElement

    root.setAttributeNS("urn:state", "s:mode", "ready")
    attribute = root.getAttributeNodeNS("urn:state", "mode")

    assert root.hasAttributeNS("urn:state", "mode")
    assert root.getAttributeNS("urn:state", "mode") == "ready"
    assert attribute.name == "s:mode"
    assert attribute.namespaceURI == "urn:state"
    assert attribute.localName == "mode"
    assert attribute.prefix == "s"
    assert attribute.ownerElement is root


def test_attribute_node_replacement_returns_old_node_and_enforces_single_owner():
    document = minidom.parseString('<root plain="old"><other/></root>')
    root = document.documentElement
    other = root.firstChild
    replacement = document.createAttribute("plain")
    replacement.value = "new"

    old = root.setAttributeNode(replacement)

    assert old.value == "old"
    assert root.getAttribute("plain") == "new"
    with pytest.raises(xml.dom.InuseAttributeErr):
        other.setAttributeNode(replacement)

    assert root.removeAttributeNode(replacement) is replacement
    assert not root.hasAttribute("plain")


def test_namednodemap_is_a_live_attribute_view_with_dom_and_mapping_access():
    root = minidom.parseString('<root first="1" second="2"/>').documentElement
    attributes = root.attributes

    assert attributes.length == len(attributes) == 2
    assert attributes.item(0) is not None
    assert attributes.getNamedItem("first").value == "1"
    assert attributes["second"].value == "2"
    assert dict(attributes.items()) == {"first": "1", "second": "2"}

    removed = attributes.removeNamedItem("first")
    assert removed.ownerElement is None
    assert not root.hasAttribute("first")
