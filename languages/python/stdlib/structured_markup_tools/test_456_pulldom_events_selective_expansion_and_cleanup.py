"""456｜pulldom 事件拉取、选择性子树展开、文件输入与一次性 stream。

pulldom 由调用方主动拉 START/END/CHARACTERS 等事件；START_ELEMENT 节点起初没有已构建的
children，只有需要随机访问的目标节点才调用 ``expandNode()``。这能避免无条件保留完整 DOM，
但底层仍是 SAX，不能安全处理恶意 XML。``reset()`` 用于释放一次性流，不表示回到输入开头。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

from xml.dom import Node
from xml.dom import pulldom


XML_TEXT = '<root><item id="one">alpha</item><item id="two">beta</item></root>'


def test_getevent_exposes_document_start_then_flat_element_and_text_events():
    stream = pulldom.parseString(XML_TEXT)

    event, document = stream.getEvent()
    remaining = list(stream)

    assert event == pulldom.START_DOCUMENT
    assert document.nodeType == Node.DOCUMENT_NODE
    event_names = {event for event, _ in remaining}
    assert {
        pulldom.START_ELEMENT,
        pulldom.END_ELEMENT,
        pulldom.CHARACTERS,
        pulldom.END_DOCUMENT,
    } <= event_names


def test_expandnode_builds_only_the_selected_subtree_and_consumes_its_events():
    stream = pulldom.parseString(XML_TEXT)
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
    path.write_text(XML_TEXT, encoding="utf-8")
    stream = pulldom.parse(str(path), bufsize=3)

    start_tags = [
        node.tagName
        for event, node in stream
        if event == pulldom.START_ELEMENT
    ]

    assert start_tags == ["root", "item", "item"]
    assert pulldom.default_bufsize > 0
    assert stream.reset() is None
