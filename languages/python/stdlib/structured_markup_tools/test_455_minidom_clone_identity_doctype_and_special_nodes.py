"""455｜DOM 节点 clone 的浅/深差异、身份判断与 DocumentType/特殊节点数据。

``cloneNode(False)`` 会复制 Element 自身和属性，但不复制 children；deep=True 递归创建新节点，
仍归同一 ownerDocument，且 clone 初始没有 parent。``isSameNode()`` 判断 DOM 节点身份。DOCTYPE、
Comment、Text 和 ProcessingInstruction 的 ``nodeName``/``nodeValue`` 各有不同含义。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from xml.dom import minidom


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
