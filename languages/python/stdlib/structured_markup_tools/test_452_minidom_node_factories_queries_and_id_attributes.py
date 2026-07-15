"""452｜Document 节点工厂、后代查询、namespace wildcard 与显式 ID 属性。

Document 的 create 系列只创建 detached 节点，调用方负责插入。``getElementsByTagName*`` 搜索
所有后代而非直接 children，且支持 ``*``；namespace 版本按 URI/localName 匹配，不看原前缀。
没有 DTD 类型信息时普通名为 ``id`` 的属性并非 ID，需 ``setIdAttribute*`` 后才能 getElementById。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.dom.Document.createElement
# polyglot-covers: python.xml.dom.Document.createElementNS
# polyglot-covers: python.xml.dom.Document.createTextNode
# polyglot-covers: python.xml.dom.Document.createComment
# polyglot-covers: python.xml.dom.Document.createCDATASection
# polyglot-covers: python.xml.dom.Document.createProcessingInstruction
# polyglot-covers: python.xml.dom.Document.createAttribute
# polyglot-covers: python.xml.dom.Document.createAttributeNS
# polyglot-covers: python.xml.dom.Document.getElementsByTagName
# polyglot-covers: python.xml.dom.Document.getElementsByTagNameNS
# polyglot-covers: python.xml.dom.Element.getElementsByTagName
# polyglot-covers: python.xml.dom.Element.getElementsByTagNameNS
# polyglot-covers: python.xml.dom.Document.getElementById
# polyglot-covers: python.xml.dom.Element.setIdAttribute

from xml.dom import Node
from xml.dom import minidom


def test_document_factories_return_detached_nodes_of_the_requested_kinds():
    document = minidom.getDOMImplementation().createDocument(None, None, None)
    element = document.createElement("item")
    namespaced = document.createElementNS("urn:catalog", "c:item")
    text = document.createTextNode("value")
    comment = document.createComment("note")
    cdata = document.createCDATASection("raw")
    instruction = document.createProcessingInstruction("build", "fast")
    attribute = document.createAttribute("plain")
    ns_attribute = document.createAttributeNS("urn:state", "s:mode")

    assert all(
        node.parentNode is None
        for node in (element, namespaced, text, comment, cdata, instruction)
    )
    assert namespaced.localName == "item" and namespaced.prefix == "c"
    assert instruction.target == "build" and instruction.data == "fast"
    assert comment.nodeType == Node.COMMENT_NODE
    assert cdata.nodeType == Node.CDATA_SECTION_NODE
    assert attribute.name == "plain"
    assert ns_attribute.localName == "mode" and ns_attribute.prefix == "s"


def test_tag_queries_search_descendants_and_namespace_queries_ignore_prefix():
    document = minidom.parseString(
        '<c:catalog xmlns:c="urn:catalog" xmlns:x="urn:catalog">'
        "<c:group><x:item/><c:item/></c:group>"
        "</c:catalog>"
    )
    root = document.documentElement

    assert len(document.getElementsByTagName("c:item")) == 1
    assert len(root.getElementsByTagName("*")) == 3
    assert len(document.getElementsByTagNameNS("urn:catalog", "item")) == 2
    assert len(root.getElementsByTagNameNS("*", "item")) == 2
    # Element 查询只看后代，不把调用它的 root 自身放入结果。
    assert root not in root.getElementsByTagNameNS("urn:catalog", "*")


def test_explicit_id_attribute_enables_lookup_and_value_changes_invalidate_cache():
    document = minidom.parseString('<root><item code="old"/></root>')
    item = document.getElementsByTagName("item")[0]

    assert document.getElementById("old") is None
    item.setIdAttribute("code")
    assert document.getElementById("old") is item

    item.setAttribute("code", "new")
    assert document.getElementById("old") is None
    assert document.getElementById("new") is item
