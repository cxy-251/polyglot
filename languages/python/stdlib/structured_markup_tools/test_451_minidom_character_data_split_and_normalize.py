"""451｜minidom CharacterData 编辑、``splitText()`` 与 ``normalize()``。

Text、CDATASection、Comment 共享 CharacterData 的按偏移编辑 API，越界以 ``IndexSizeErr``
报告。``splitText()`` 不只返回后半段：若原 Text 已挂树，新 Text 会紧邻插入。手工构树可能
产生相邻或空 Text；``normalize()`` 会递归合并相邻同类文本并删除空节点，便于后续读取。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import xml.dom
from xml.dom import Node
from xml.dom import minidom

import pytest


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
