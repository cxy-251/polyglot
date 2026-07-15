"""440｜``iterparse()`` 的事件流、命名空间事件与增量清理工作流。

``iterparse()`` 增量构树但会执行阻塞读取；需要完全非阻塞输入时应选 ``XMLPullParser``。start
事件只保证已读完 ``>``，属性可用，但 text、tail 和 children 尚无完成保证；读取完整节点应处理
end 事件。迭代器耗尽后 ``root`` 才是完整根节点，大文件可在消费 end 事件后 ``clear()``。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.iterparse
# polyglot-covers: python.xml.etree.ElementTree.iterparse-default-end-event
# polyglot-covers: python.xml.etree.ElementTree.iterparse-start-end-events
# polyglot-covers: python.xml.etree.ElementTree.iterparse-comment-pi-events-3.8
# polyglot-covers: python.xml.etree.ElementTree.iterparse-start-ns-end-ns-events
# polyglot-covers: python.xml.etree.ElementTree.iterparse.root-after-exhaustion
# polyglot-covers: python.xml.etree.ElementTree.iterparse-start-event-incomplete-node
# polyglot-covers: python.xml.etree.ElementTree.iterparse-blocking-read
# polyglot-covers: python.xml.etree.ElementTree.iterparse-clear-after-end-memory-workflow

import io
from xml.etree import ElementTree as ET


XML_BYTES = b"""\
<root xmlns:p="urn:parts">
  <!--note--><?build fast?>
  <p:item id="one">alpha</p:item>
  <p:item id="two">beta</p:item>
</root>
"""


def test_default_iterparse_yields_only_end_events_and_exposes_root_at_exhaustion():
    iterator = ET.iterparse(io.BytesIO(XML_BYTES))
    events = list(iterator)

    assert {event for event, _ in events} == {"end"}
    assert [node.tag for _, node in events] == [
        "{urn:parts}item",
        "{urn:parts}item",
        "root",
    ]
    assert iterator.root.tag == "root"


def test_iterparse_reports_markup_and_namespace_events_without_inserting_them():
    requested = ("start", "end", "comment", "pi", "start-ns", "end-ns")
    iterator = ET.iterparse(io.BytesIO(XML_BYTES), events=requested)
    events = list(iterator)

    assert ("start-ns", ("p", "urn:parts")) in events
    assert any(event == "end-ns" and value is None for event, value in events)
    assert any(event == "comment" and node.text == "note" for event, node in events)
    assert any(event == "pi" and node.text == "build fast" for event, node in events)
    # comment/pi 事件可观察这些节点，但默认 TreeBuilder 不把它们插入结果树。
    assert [child.tag for child in iterator.root] == [
        "{urn:parts}item",
        "{urn:parts}item",
    ]


def test_large_document_workflow_reads_complete_end_nodes_then_clears_them():
    iterator = ET.iterparse(io.BytesIO(XML_BYTES), events=("start", "end"))
    rows = []

    for event, node in iterator:
        if event == "end" and node.tag == "{urn:parts}item":
            rows.append((node.get("id"), node.text))
            node.clear()

    assert rows == [("one", "alpha"), ("two", "beta")]
    assert all(child.attrib == {} and child.text is None for child in iterator.root)
