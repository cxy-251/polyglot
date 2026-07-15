"""441｜``XMLPullParser`` 的 feed/read_events 队列与非阻塞解析模式。

调用者自行取得网络或设备数据，再用 ``feed()`` 投递小块，因此解析器本身不执行阻塞读取。
``read_events()`` 只消费当前已排队事件，同一事件不会在下次调用中重复出现。start 事件仍只
代表开始标签闭合；应在 end 事件读取完整内容。部分 3.10 修订版回移了 ``flush()``，需做能力检测。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.feed
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.read_events
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.close
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser-nonblocking-input-pattern
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser-event-consumed-once
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser-start-node-incomplete
# polyglot-covers: python.xml.etree.ElementTree.XMLPullParser.flush-version-guard
# polyglot-covers: python.xml.etree.ElementTree.flush-reparse-deferral-security-note

from xml.etree import ElementTree as ET


def test_pull_parser_exposes_only_events_available_after_each_feed():
    parser = ET.XMLPullParser(events=("start", "end"))

    parser.feed("<root><item id='one'>")
    first_batch = list(parser.read_events())
    assert [(event, node.tag) for event, node in first_batch] == [
        ("start", "root"),
        ("start", "item"),
    ]
    assert list(parser.read_events()) == []

    parser.feed("value</item><item id='two'/></root>")
    second_batch = list(parser.read_events())
    parser.close()

    assert [(event, node.tag) for event, node in second_batch] == [
        ("end", "item"),
        ("start", "item"),
        ("end", "item"),
        ("end", "root"),
    ]
    assert second_batch[0][1].text == "value"
    assert list(parser.read_events()) == []


def test_pull_parser_reports_namespace_comment_and_pi_events():
    parser = ET.XMLPullParser(
        events=("start-ns", "end-ns", "comment", "pi", "end")
    )
    parser.feed(
        '<root xmlns:p="urn:p"><!--note--><?build fast?><p:item/></root>'
    )
    parser.close()
    events = list(parser.read_events())

    assert ("start-ns", ("p", "urn:p")) in events
    assert any(event == "end-ns" and value is None for event, value in events)
    assert any(event == "comment" and node.text == "note" for event, node in events)
    assert any(event == "pi" and node.text == "build fast" for event, node in events)


def test_flush_is_used_only_when_the_running_310_patch_release_provides_it():
    parser = ET.XMLPullParser(events=("end",))
    parser.feed("<root><item/>")

    flush = getattr(parser, "flush", None)
    if flush is not None:
        # flush 会临时关闭 Expat reparse deferral；不可信输入下要权衡即时性与安全影响。
        flush()

    parser.feed("</root>")
    parser.close()
    assert [node.tag for event, node in parser.read_events() if event == "end"] == [
        "item",
        "root",
    ]
