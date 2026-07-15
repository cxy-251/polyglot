"""448｜minidom 节点类型、父子/兄弟导航以及 Python 化的 NodeList。

DOM 把文本、注释和处理指令都保存为节点，所以 ``childNodes`` 不是“子元素列表”。空白文本也会
影响 first/last/previous/next 导航，按元素遍历必须检查 ``nodeType``。NodeList 同时提供 DOM 的
``length``/``item()`` 和 Python 的 ``len``、索引、迭代；越界 ``item()`` 返回 None 而非抛错。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from xml.dom import Node
from xml.dom import minidom


XML_TEXT = (
    '<root plain="yes">left<!--note--><?build fast?><child/>right</root>'
)


def test_dom_preserves_non_element_nodes_and_all_navigation_links():
    document = minidom.parseString(XML_TEXT)
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
    document = minidom.parseString(XML_TEXT)
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
    nodes = minidom.parseString(XML_TEXT).documentElement.childNodes

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
