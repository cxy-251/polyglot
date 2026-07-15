"""439｜ElementTree 序列化时的前缀注册、默认命名空间与 QName 值。

树内名称保存为 ``{uri}local``，前缀只是序列化选择。``register_namespace()`` 修改进程级映射，
相同前缀或 URI 的旧映射会被移除；测试必须隔离这种全局状态。``default_namespace`` 只能用于
完全限定的名称，混入未限定 tag/属性会报错，不能把它当作自动补命名空间的开关。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.register_namespace
# polyglot-covers: python.xml.etree.ElementTree.register_namespace-global-state
# polyglot-covers: python.xml.etree.ElementTree.register_namespace-replaces-prefix-or-uri
# polyglot-covers: python.xml.etree.ElementTree.tostring.default_namespace
# polyglot-covers: python.xml.etree.ElementTree.default_namespace-requires-qualified-names
# polyglot-covers: python.xml.etree.ElementTree.QName-attribute-value

from xml.etree import ElementTree as ET

import pytest


def test_registered_prefix_controls_serialization_without_changing_expanded_names(
    monkeypatch,
):
    # 公共 API 没有 unregister；替换模块映射副本，让 pytest 在用例结束时恢复原对象。
    monkeypatch.setattr(ET, "_namespace_map", ET._namespace_map.copy())
    ET.register_namespace("demo", "urn:demo")
    root = ET.Element("{urn:demo}root")
    child = ET.SubElement(root, "{urn:demo}item")
    child.set("kind", ET.QName("urn:demo", "special"))

    wire = ET.tostring(root, encoding="unicode")

    assert wire.startswith('<demo:root xmlns:demo="urn:demo">')
    assert '<demo:item kind="demo:special"' in wire
    assert root.tag == "{urn:demo}root"


def test_registering_the_same_prefix_or_uri_replaces_the_previous_mapping(monkeypatch):
    monkeypatch.setattr(ET, "_namespace_map", ET._namespace_map.copy())

    ET.register_namespace("first", "urn:one")
    ET.register_namespace("first", "urn:two")
    old_uri_wire = ET.tostring(ET.Element("{urn:one}item"), encoding="unicode")
    assert "first:item" not in old_uri_wire

    ET.register_namespace("second", "urn:two")
    new_uri_wire = ET.tostring(ET.Element("{urn:two}item"), encoding="unicode")
    assert "second:item" in new_uri_wire
    assert "first:item" not in new_uri_wire


def test_default_namespace_removes_prefix_only_for_fully_qualified_names():
    root = ET.Element("{urn:catalog}catalog")
    ET.SubElement(root, "{urn:catalog}item")

    wire = ET.tostring(root, encoding="unicode", default_namespace="urn:catalog")

    assert wire == '<catalog xmlns="urn:catalog"><item /></catalog>'

    root.set("plain", "not-qualified")
    with pytest.raises(ValueError, match="non-qualified names"):
        ET.tostring(root, encoding="unicode", default_namespace="urn:catalog")
