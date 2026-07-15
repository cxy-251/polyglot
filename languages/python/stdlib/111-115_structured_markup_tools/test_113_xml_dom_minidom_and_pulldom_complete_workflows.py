"""113｜DOM implementation 发现、注册、特性选择与 Document/DOCTYPE 创建。

``getDOMImplementation()`` 把调用方与具体 DOM 实现解耦，可按名字或 feature/version 对选择。
``registerDOMImplementation()`` 修改进程级注册表，因此测试应隔离。实现对象可先创建 doctype，
再一次创建带命名空间根节点的 Document；传入两个 ``None`` 也可创建暂时没有根元素的空文档。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.dom.getDOMImplementation
# polyglot-covers: python.xml.dom.registerDOMImplementation
# polyglot-covers: python.xml.dom.DOMImplementation.hasFeature
# polyglot-covers: python.xml.dom.DOMImplementation.createDocument
# polyglot-covers: python.xml.dom.DOMImplementation.createDocumentType
# polyglot-covers: python.xml.dom.Document.documentElement
# polyglot-covers: python.xml.dom.Document.doctype
# polyglot-covers: python.xml.dom.EMPTY_NAMESPACE
# polyglot-covers: python.xml.dom.XML_NAMESPACE
# polyglot-covers: python.xml.dom.XMLNS_NAMESPACE
# polyglot-covers: python.xml.dom.XHTML_NAMESPACE



import xml.dom.domreg as domreg
from xml.dom import EMPTY_NAMESPACE
from xml.dom import XHTML_NAMESPACE
from xml.dom import XMLNS_NAMESPACE
from xml.dom import XML_NAMESPACE
from xml.dom import getDOMImplementation
from xml.dom import registerDOMImplementation
from xml.dom import Node
from xml.dom import minidom
import xml.dom
import pytest
import io
from xml.sax import handler
from xml.sax import make_parser
from xml.dom import pulldom

def test_default_implementation_can_be_selected_by_supported_features():
    implementation = getDOMImplementation(features=(("core", "1.0"),))

    assert implementation.hasFeature("core", "1.0")
    assert implementation.hasFeature("xml", "1.0")


def test_named_registration_is_isolated_from_the_process_global_registry(monkeypatch):
    monkeypatch.setattr(domreg, "registered", domreg.registered.copy())
    implementation = getDOMImplementation()

    registerDOMImplementation("polyglot-demo", lambda: implementation)

    assert getDOMImplementation("polyglot-demo") is implementation


def test_implementation_builds_doctype_namespaced_root_and_empty_document():
    implementation = getDOMImplementation()
    doctype = implementation.createDocumentType(
        "c:catalog",
        "-//POLYGLOT//DTD CATALOG 1.0//EN",
        "catalog.dtd",
    )
    document = implementation.createDocument(
        "urn:catalog",
        "c:catalog",
        doctype,
    )

    assert document.documentElement.tagName == "c:catalog"
    assert document.documentElement.namespaceURI == "urn:catalog"
    assert document.documentElement.prefix == "c"
    assert document.documentElement.localName == "catalog"
    assert document.doctype is doctype
    # minidom 的 DocumentType.name 保存 local name；根元素本身仍保留完整 tagName/prefix。
    assert doctype.name == "catalog"
    assert doctype.publicId == "-//POLYGLOT//DTD CATALOG 1.0//EN"
    assert doctype.systemId == "catalog.dtd"

    empty = implementation.createDocument(None, None, None)
    assert empty.documentElement is None


def test_dom_namespace_constants_distinguish_reserved_namespaces():
    assert EMPTY_NAMESPACE is None
    assert XML_NAMESPACE == "http://www.w3.org/XML/1998/namespace"
    assert XMLNS_NAMESPACE == "http://www.w3.org/2000/xmlns/"
    assert XHTML_NAMESPACE == "http://www.w3.org/1999/xhtml"


# minidom 节点类型、父子/兄弟导航以及 Python 化的 NodeList。
#
# DOM 把文本、注释和处理指令都保存为节点，所以 ``childNodes`` 不是“子元素列表”。空白文本也会
# 影响 first/last/previous/next 导航，按元素遍历必须检查 ``nodeType``。NodeList 同时提供 DOM 的
# ``length``/``item()`` 和 Python 的 ``len``、索引、迭代；越界 ``item()`` 返回 None 而非抛错。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.dom.Node.nodeType
# polyglot-covers: python.xml.dom.Node.parentNode
# polyglot-covers: python.xml.dom.Node.attributes
# polyglot-covers: python.xml.dom.Node.previousSibling
# polyglot-covers: python.xml.dom.Node.nextSibling
# polyglot-covers: python.xml.dom.Node.childNodes
# polyglot-covers: python.xml.dom.Node.firstChild
# polyglot-covers: python.xml.dom.Node.lastChild
# polyglot-covers: python.xml.dom.Node.nodeName
# polyglot-covers: python.xml.dom.Node.nodeValue
# polyglot-covers: python.xml.dom.Node.hasAttributes
# polyglot-covers: python.xml.dom.Node.hasChildNodes
# polyglot-covers: python.xml.dom.NodeList.length
# polyglot-covers: python.xml.dom.NodeList.item
# polyglot-covers: python.xml.dom.NodeList-python-sequence



XML_TEXT_448 = (
    '<root plain="yes">left<!--note--><?build fast?><child/>right</root>'
)


def test_dom_preserves_non_element_nodes_and_all_navigation_links():
    document = minidom.parseString(XML_TEXT_448)
    root = document.documentElement
    text, comment, instruction, child, tail = root.childNodes

    assert document.nodeType == Node.DOCUMENT_NODE
    assert root.nodeType == Node.ELEMENT_NODE
    assert text.nodeType == Node.TEXT_NODE
    assert comment.nodeType == Node.COMMENT_NODE
    assert instruction.nodeType == Node.PROCESSING_INSTRUCTION_NODE
    assert child.nodeType == Node.ELEMENT_NODE

    assert root.parentNode is document
    assert root.firstChild is text
    assert root.lastChild is tail
    assert comment.previousSibling is text
    assert comment.nextSibling is instruction
    assert child.nextSibling is tail
    assert text.nodeName == "#text" and text.nodeValue == "left"
    assert root.nodeName == "root" and root.nodeValue is None


def test_attributes_are_nodes_but_attr_parent_is_always_none():
    document = minidom.parseString(XML_TEXT_448)
    root = document.documentElement
    attribute = root.getAttributeNode("plain")

    assert root.hasAttributes()
    assert root.hasChildNodes()
    assert attribute.nodeType == Node.ATTRIBUTE_NODE
    assert attribute.parentNode is None
    assert attribute.ownerElement is root
    assert attribute.name == "plain"
    assert attribute.value == attribute.nodeValue == "yes"


def test_nodelist_supports_dom_and_python_sequence_protocols():
    nodes = minidom.parseString(XML_TEXT_448).documentElement.childNodes

    assert nodes.length == len(nodes) == 5
    assert nodes.item(0) is nodes[0]
    assert nodes.item(999) is None
    assert [node.nodeType for node in nodes] == [
        Node.TEXT_NODE,
        Node.COMMENT_NODE,
        Node.PROCESSING_INSTRUCTION_NODE,
        Node.ELEMENT_NODE,
        Node.TEXT_NODE,
    ]


# minidom 插入、替换、移除、节点搬移与 DocumentFragment 拼接。
#
# 节点只能有一个 parent；把已有节点 append 到新位置会先从旧位置移除，并同步兄弟链接。
# ``DocumentFragment`` 本身不会成为 child，插入时只把其中节点依次拼入目标并清空 fragment。
# 引用节点不属于目标或层级不合法时，minidom 使用带 DOM 错误码的具体异常。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# minidom 普通/命名空间属性、Attr 所有权与 NamedNodeMap。
#
# ``getAttribute()`` 对不存在和显式空值都返回空字符串，必须配合 ``hasAttribute()`` 区分。
# namespace API 以 ``(namespaceURI, localName)`` 定位，却在 set 时接收完整 qname。Attr 节点一次
# 只能归一个 Element；NamedNodeMap 是属性字典的活视图，其 mapping 扩展不属于核心 DOM 保证。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# minidom CharacterData 编辑、``splitText()`` 与 ``normalize()``。
#
# Text、CDATASection、Comment 共享 CharacterData 的按偏移编辑 API，越界以 ``IndexSizeErr``
# 报告。``splitText()`` 不只返回后半段：若原 Text 已挂树，新 Text 会紧邻插入。手工构树可能
# 产生相邻或空 Text；``normalize()`` 会递归合并相邻同类文本并删除空节点，便于后续读取。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.dom.CharacterData.data
# polyglot-covers: python.xml.dom.CharacterData.length
# polyglot-covers: python.xml.dom.CharacterData.substringData
# polyglot-covers: python.xml.dom.CharacterData.appendData
# polyglot-covers: python.xml.dom.CharacterData.insertData
# polyglot-covers: python.xml.dom.CharacterData.deleteData
# polyglot-covers: python.xml.dom.CharacterData.replaceData
# polyglot-covers: python.xml.dom.Text.splitText
# polyglot-covers: python.xml.dom.Node.normalize
# polyglot-covers: python.xml.dom.IndexSizeErr
# polyglot-covers: python.xml.dom.CDATASection




def test_character_data_supports_bounded_substring_and_in_place_edits():
    document = minidom.getDOMImplementation().createDocument(None, None, None)
    text = document.createTextNode("abcdef")

    assert text.length == len(text) == 6
    assert text.substringData(1, 3) == "bcd"

    text.appendData("g")
    text.insertData(1, "X")
    text.deleteData(2, 2)
    text.replaceData(2, 3, "YY")
    assert text.data == text.nodeValue == "aXYYg"

    with pytest.raises(xml.dom.IndexSizeErr) as caught:
        text.substringData(-1, 1)
    assert caught.value.code == xml.dom.INDEX_SIZE_ERR


def test_split_text_updates_data_and_inserts_the_new_sibling_into_the_tree():
    document = minidom.parseString("<root><marker/></root>")
    root = document.documentElement
    marker = root.firstChild
    text = document.createTextNode("alpha")
    root.insertBefore(text, marker)

    remainder = text.splitText(2)

    assert text.data == "al"
    assert remainder.data == "pha"
    assert list(root.childNodes) == [text, remainder, marker]
    assert text.nextSibling is remainder
    assert remainder.previousSibling is text
    assert remainder.nextSibling is marker


def test_normalize_recursively_merges_adjacent_text_and_discards_empty_text():
    document = minidom.parseString("<root><child/></root>")
    root = document.documentElement
    child = root.firstChild
    root.insertBefore(document.createTextNode("a"), child)
    root.insertBefore(document.createTextNode("b"), child)
    root.insertBefore(document.createTextNode(""), child)
    child.appendChild(document.createTextNode("c"))
    child.appendChild(document.createTextNode("d"))

    root.normalize()

    assert root.childNodes.length == 2
    assert root.firstChild.nodeType == Node.TEXT_NODE
    assert root.firstChild.data == "ab"
    assert child.childNodes.length == 1
    assert child.firstChild.data == "cd"


def test_cdata_has_character_data_api_but_a_distinct_node_type():
    document = minidom.getDOMImplementation().createDocument(None, None, None)
    cdata = document.createCDATASection("<literal>&value")

    assert cdata.nodeType == Node.CDATA_SECTION_NODE
    assert cdata.data == "<literal>&value"
    cdata.appendData(";")
    assert cdata.data.endswith(";")


# Document 节点工厂、后代查询、namespace wildcard 与显式 ID 属性。
#
# Document 的 create 系列只创建 detached 节点，调用方负责插入。``getElementsByTagName*`` 搜索
# 所有后代而非直接 children，且支持 ``*``；namespace 版本按 URI/localName 匹配，不看原前缀。
# 没有 DTD 类型信息时普通名为 ``id`` 的属性并非 ID，需 ``setIdAttribute*`` 后才能 getElementById。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# minidom ``writexml``/``toxml``/``toprettyxml`` 与显式 unlink 生命周期。
#
# ``toxml()`` 无 encoding 返回 str，显式 encoding 返回 bytes；standalone 会写入声明。3.8 起
# 序列化保留用户属性顺序。pretty print 会保留树里已有的空白 Text，再叠加缩进，不能用来规范化
# 语义。大型 DOM 可 ``unlink()`` 提前断开循环引用，Document 上下文管理器会在退出时自动调用。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.dom.minidom.Node.writexml
# polyglot-covers: python.xml.dom.minidom.Node.toxml
# polyglot-covers: python.xml.dom.minidom.Node.toprettyxml
# polyglot-covers: python.xml.dom.minidom.serialization-encoding-return-type
# polyglot-covers: python.xml.dom.minidom.serialization-standalone-3.9
# polyglot-covers: python.xml.dom.minidom.serialization-attribute-order-3.8
# polyglot-covers: python.xml.dom.minidom.pretty-print-whitespace-trap
# polyglot-covers: python.xml.dom.minidom.Node.unlink
# polyglot-covers: python.xml.dom.minidom.Node-context-manager



def build_document():
    document = minidom.parseString("<root><item>value</item></root>")
    root = document.documentElement
    root.setAttribute("first", "1")
    root.setAttribute("second", '2 & "quoted"')
    return document


def test_toxml_selects_str_or_bytes_and_preserves_attribute_order():
    document = build_document()

    text_wire = document.toxml()
    byte_wire = document.toxml(encoding="utf-8", standalone=True)

    assert isinstance(text_wire, str)
    assert isinstance(byte_wire, bytes)
    assert text_wire.index('first="1"') < text_wire.index("second=")
    assert 'second="2 &amp; &quot;quoted&quot;"' in text_wire
    assert b'encoding="utf-8"' in byte_wire
    assert b'standalone="yes"' in byte_wire


def test_writexml_uses_a_text_writer_and_toprettyxml_controls_indent_and_newline():
    document = build_document()
    writer = io.StringIO()

    result = document.writexml(writer, addindent="  ", newl="\n")
    pretty = document.toprettyxml(indent="--", newl="\r\n")

    assert result is None
    assert writer.getvalue().startswith('<?xml version="1.0" ?>\n')
    assert "\n<root" in writer.getvalue()
    assert "\n  <item>value</item>" in writer.getvalue()
    assert isinstance(pretty, str)
    assert "\r\n<root" in pretty
    assert "\r\n--<item>value</item>" in pretty
    # 若输入树本来含仅空白 Text，pretty printer 会保留它们并再添加缩进。


def test_context_manager_unlinks_the_document_and_descendants_on_exit():
    with minidom.parseString("<root><item/></root>") as document:
        root = document.documentElement
        item = root.firstChild
        assert item.ownerDocument is document

    assert document.childNodes.length == 0
    assert root.ownerDocument is None
    assert root.childNodes.length == 0
    assert item.ownerDocument is None


# minidom 文件/字符串输入、调用方配置的 SAX parser 与安全边界。
#
# ``parse()`` 接文件名或 file-like，``parseString()`` 接 str/bytes；两者都会在返回前完成整棵 DOM。
# 传入 SAX2 parser 时，minidom 会替换其 content handler 并开启 namespace，但 entity resolver 等
# 策略必须由调用方预先配置。minidom 不能作为恶意 XML 的安全层，测试只使用受控小输入。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.dom.minidom.parse
# polyglot-covers: python.xml.dom.minidom.parse.filename
# polyglot-covers: python.xml.dom.minidom.parse.file-like
# polyglot-covers: python.xml.dom.minidom.parse.bufsize
# polyglot-covers: python.xml.dom.minidom.parseString
# polyglot-covers: python.xml.dom.minidom.parseString.str-and-bytes
# polyglot-covers: python.xml.dom.minidom.parse-custom-sax2-parser
# polyglot-covers: python.xml.dom.minidom.parse-enables-namespaces
# polyglot-covers: python.xml.dom.minidom-untrusted-xml-warning



XML_TEXT_454 = '<p:root xmlns:p="urn:parts"><p:item>value</p:item></p:root>'


def test_parse_accepts_a_filename_or_file_like_and_bufsize_is_chunk_size(tmp_path):
    path = tmp_path / "document.xml"
    path.write_text(XML_TEXT_454, encoding="utf-8")

    from_name = minidom.parse(str(path), bufsize=3)
    from_file = minidom.parse(io.StringIO(XML_TEXT_454), bufsize=2)

    assert from_name.documentElement.namespaceURI == "urn:parts"
    item = from_file.getElementsByTagNameNS("urn:parts", "item")[0]
    # 小 bufsize 可能把连续字符拆成相邻 Text 节点；DOM 使用方不能只读 firstChild。
    assert "".join(
        child.data for child in item.childNodes if child.nodeType == Node.TEXT_NODE
    ) == "value"


def test_parse_string_accepts_text_or_encoded_xml_bytes():
    from_text = minidom.parseString(XML_TEXT_454)
    from_bytes = minidom.parseString(XML_TEXT_454.encode("utf-8"))

    assert from_text.documentElement.toxml() == from_bytes.documentElement.toxml()


def test_custom_sax_parser_is_reconfigured_for_namespace_aware_dom_building():
    parser = make_parser()
    parser.setFeature(handler.feature_namespaces, False)

    document = minidom.parseString(XML_TEXT_454, parser=parser)

    assert parser.getFeature(handler.feature_namespaces)
    assert document.documentElement.namespaceURI == "urn:parts"
    # 自定义 resolver、外部实体开关等必须在传给 minidom 前设置；这里不启用外部资源。


# DOM 节点 clone 的浅/深差异、身份判断与 DocumentType/特殊节点数据。
#
# ``cloneNode(False)`` 会复制 Element 自身和属性，但不复制 children；deep=True 递归创建新节点，
# 仍归同一 ownerDocument，且 clone 初始没有 parent。``isSameNode()`` 判断 DOM 节点身份。DOCTYPE、
# Comment、Text 和 ProcessingInstruction 的 ``nodeName``/``nodeValue`` 各有不同含义。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.dom.Node.cloneNode
# polyglot-covers: python.xml.dom.Node.isSameNode
# polyglot-covers: python.xml.dom.Node.clone-shallow-versus-deep
# polyglot-covers: python.xml.dom.DocumentType.name
# polyglot-covers: python.xml.dom.DocumentType.publicId
# polyglot-covers: python.xml.dom.DocumentType.systemId
# polyglot-covers: python.xml.dom.DocumentType.entities
# polyglot-covers: python.xml.dom.DocumentType.notations
# polyglot-covers: python.xml.dom.Comment.data
# polyglot-covers: python.xml.dom.Text.data
# polyglot-covers: python.xml.dom.ProcessingInstruction.target
# polyglot-covers: python.xml.dom.ProcessingInstruction.data



def test_element_clone_copies_attributes_and_optionally_descendants():
    document = minidom.parseString('<root state="ready"><item>value</item></root>')
    root = document.documentElement

    shallow = root.cloneNode(False)
    deep = root.cloneNode(True)

    assert shallow.getAttribute("state") == "ready"
    assert shallow.childNodes.length == 0
    assert shallow.parentNode is None
    assert shallow.ownerDocument is document

    assert deep.childNodes.length == 1
    assert deep.firstChild is not root.firstChild
    assert deep.firstChild.firstChild.data == "value"
    assert not root.isSameNode(deep)
    assert root.isSameNode(root)


def test_doctype_exposes_identifiers_and_named_maps_even_when_they_are_empty():
    implementation = minidom.getDOMImplementation()
    doctype = implementation.createDocumentType(
        "root",
        "-//POLYGLOT//DTD ROOT 1.0//EN",
        "root.dtd",
    )
    document = implementation.createDocument(None, "root", doctype)

    assert document.doctype.name == "root"
    assert document.doctype.publicId == "-//POLYGLOT//DTD ROOT 1.0//EN"
    assert document.doctype.systemId == "root.dtd"
    assert document.doctype.entities.length == 0
    assert document.doctype.notations.length == 0


def test_special_nodes_expose_type_specific_name_and_value_aliases():
    document = minidom.getDOMImplementation().createDocument(None, None, None)
    text = document.createTextNode("value")
    comment = document.createComment("note")
    instruction = document.createProcessingInstruction("build", "fast")

    assert text.nodeName == "#text" and text.nodeValue == text.data == "value"
    assert comment.nodeName == "#comment" and comment.nodeValue == "note"
    assert instruction.nodeName == instruction.target == "build"
    assert instruction.nodeValue == instruction.data == "fast"


# pulldom 事件拉取、选择性子树展开、文件输入与一次性 stream。
#
# pulldom 由调用方主动拉 START/END/CHARACTERS 等事件；START_ELEMENT 节点起初没有已构建的
# children，只有需要随机访问的目标节点才调用 ``expandNode()``。这能避免无条件保留完整 DOM，
# 但底层仍是 SAX，不能安全处理恶意 XML。``reset()`` 用于释放一次性流，不表示回到输入开头。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xml.dom.pulldom.parse
# polyglot-covers: python.xml.dom.pulldom.parseString
# polyglot-covers: python.xml.dom.pulldom.default_bufsize
# polyglot-covers: python.xml.dom.pulldom.DOMEventStream
# polyglot-covers: python.xml.dom.pulldom.DOMEventStream.getEvent
# polyglot-covers: python.xml.dom.pulldom.DOMEventStream.expandNode
# polyglot-covers: python.xml.dom.pulldom.DOMEventStream.reset
# polyglot-covers: python.xml.dom.pulldom-selective-dom-workflow
# polyglot-covers: python.xml.dom.pulldom-event-constants
# polyglot-covers: python.xml.dom.pulldom-sequence-protocol-deprecated-3.8
# polyglot-covers: python.xml.dom.pulldom-untrusted-xml-warning



XML_TEXT_456 = '<root><item id="one">alpha</item><item id="two">beta</item></root>'


def test_getevent_exposes_document_start_then_flat_element_and_text_events():
    stream = pulldom.parseString(XML_TEXT_456)

    event, document = stream.getEvent()
    remaining = list(stream)

    assert event == pulldom.START_DOCUMENT
    assert document.nodeType == Node.DOCUMENT_NODE
    event_names = {event for event, _ in remaining}
    assert {
        pulldom.START_ELEMENT,
        pulldom.END_ELEMENT,
        pulldom.CHARACTERS,
    } <= event_names
    # Python 3.10 pulldom 以迭代耗尽表示文档结束，不产生 END_DOCUMENT 事件。
    assert pulldom.END_DOCUMENT not in event_names


def test_expandnode_builds_only_the_selected_subtree_and_consumes_its_events():
    stream = pulldom.parseString(XML_TEXT_456)
    selected = None

    for event, node in stream:
        if event == pulldom.START_ELEMENT and node.getAttribute("id") == "one":
            selected = node
            assert selected.childNodes.length == 0
            stream.expandNode(selected)
            break

    assert selected.toxml() == '<item id="one">alpha</item>'
    remaining_start_ids = [
        node.getAttribute("id")
        for event, node in stream
        if event == pulldom.START_ELEMENT and node.tagName == "item"
    ]
    assert remaining_start_ids == ["two"]


def test_parse_reads_a_controlled_file_and_reset_releases_the_one_shot_stream(
    tmp_path,
):
    path = tmp_path / "document.xml"
    path.write_text(XML_TEXT_456, encoding="utf-8")
    stream = pulldom.parse(str(path), bufsize=3)

    start_tags = [
        node.tagName
        for event, node in stream
        if event == pulldom.START_ELEMENT
    ]

    assert start_tags == ["root", "item", "item"]
    assert pulldom.default_bufsize > 0
    assert stream.reset() is None
