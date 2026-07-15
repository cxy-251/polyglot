"""435｜ElementTree 的 find/findall/iterfind/findtext、深度遍历与 namespace。

find("tag") 只看直接 child，``.//tag`` 才递归；findall 返回列表，iterfind 延迟产生匹配项。
findtext 区分“未找到”与“找到了空元素”。XML namespace 在内存中是 ``{uri}local``，XPath 可用
prefix 映射或 3.8 起的 namespace wildcard；默认 namespace 也必须显式绑定一个查询前缀。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.Element.find
# polyglot-covers: python.xml.etree.ElementTree.Element.findall
# polyglot-covers: python.xml.etree.ElementTree.Element.iterfind
# polyglot-covers: python.xml.etree.ElementTree.Element.findtext
# polyglot-covers: python.xml.etree.ElementTree.Element.iter
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.find
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.findall
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.iterfind
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.findtext
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.iter
# polyglot-covers: python.xml.etree.ElementTree.xpath-direct-child-versus-descendant
# polyglot-covers: python.xml.etree.ElementTree.findtext-missing-versus-empty
# polyglot-covers: python.xml.etree.ElementTree.namespace-expanded-name
# polyglot-covers: python.xml.etree.ElementTree.namespace-prefix-map
# polyglot-covers: python.xml.etree.ElementTree.namespace-wildcards-3.8

from xml.etree import ElementTree as ET


XML_TEXT = """\
<catalog xmlns="urn:catalog" xmlns:m="urn:meta">
  <item id="a"><name>Alpha</name><m:rank>1</m:rank></item>
  <group><item id="b"><name /></item></group>
</catalog>
"""


def test_find_paths_distinguish_direct_children_descendants_and_empty_text():
    root = ET.fromstring("<root><item>A</item><group><item /></group></root>")
    tree = ET.ElementTree(root)

    assert root.find("item").text == "A"
    assert len(root.findall("item")) == 1
    assert len(root.findall(".//item")) == 2
    assert list(root.iterfind(".//item")) == root.findall(".//item")
    assert [node.tag for node in root.iter()] == ["root", "item", "group", "item"]
    assert root.findtext("item") == "A"
    assert root.findtext("group/item") == ""
    assert root.findtext("missing", "fallback") == "fallback"

    assert tree.find("item") is root[0]
    assert tree.findall(".//item") == root.findall(".//item")
    assert list(tree.iterfind(".//item")) == root.findall(".//item")
    assert tree.findtext("item") == "A"
    assert list(tree.iter()) == list(root.iter())


def test_namespace_queries_use_expanded_names_prefix_maps_and_wildcards():
    root = ET.fromstring(XML_TEXT)
    ns = {"c": "urn:catalog", "m": "urn:meta"}

    assert root.tag == "{urn:catalog}catalog"
    assert [node.get("id") for node in root.findall(".//c:item", ns)] == ["a", "b"]
    assert root.findtext("c:item/c:name", namespaces=ns) == "Alpha"
    assert root.find(".//m:rank", ns).text == "1"
    assert [node.tag for node in root.findall(".//{*}rank")] == ["{urn:meta}rank"]
    assert len(root.findall(".//{urn:catalog}*")) == 5
