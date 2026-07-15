"""442｜``XMLParser`` target 协议与 ``TreeBuilder`` 的注释、PI 插入选项。

``XMLParser`` 把 start/end/data 事件交给 target，并把 ``target.close()`` 的值作为解析结果，
所以 target 不一定构造 Element。默认 ``TreeBuilder`` 会跳过源文档中的注释和处理指令；显式
开启 ``insert_comments``/``insert_pis`` 才把它们作为特殊节点保留，factory 可定制节点创建。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.XMLParser
# polyglot-covers: python.xml.etree.ElementTree.XMLParser.feed
# polyglot-covers: python.xml.etree.ElementTree.XMLParser.close
# polyglot-covers: python.xml.etree.ElementTree.XMLParser-custom-target-protocol
# polyglot-covers: python.xml.etree.ElementTree.XMLParser-target-close-result
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.insert_comments
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.insert_pis
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.element_factory
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.comment_factory
# polyglot-covers: python.xml.etree.ElementTree.TreeBuilder.pi_factory

from xml.etree import ElementTree as ET


class EventTarget:
    def __init__(self):
        self.events = []

    def start(self, tag, attrs):
        self.events.append(("start", tag, dict(attrs)))

    def end(self, tag):
        self.events.append(("end", tag))

    def data(self, text):
        if text.strip():
            self.events.append(("data", text))

    def close(self):
        return tuple(self.events)


def test_custom_target_receives_parser_events_and_controls_close_result():
    target = EventTarget()
    parser = ET.XMLParser(target=target)

    parser.feed("<root id='one'>")
    parser.feed("value<child/></root>")
    result = parser.close()

    assert result == (
        ("start", "root", {"id": "one"}),
        ("data", "value"),
        ("start", "child", {}),
        ("end", "child"),
        ("end", "root"),
    )


def test_treebuilder_must_opt_in_to_retain_parsed_comments_and_pis():
    xml = "<root><!--note--><?build fast?><child/></root>"
    default_root = ET.fromstring(xml)
    parser = ET.XMLParser(
        target=ET.TreeBuilder(insert_comments=True, insert_pis=True)
    )
    retained_root = ET.fromstring(xml, parser=parser)

    assert [child.tag for child in default_root] == ["child"]
    assert [child.tag for child in retained_root] == [
        ET.Comment,
        ET.ProcessingInstruction,
        "child",
    ]
    assert retained_root[0].text == "note"
    assert retained_root[1].text == "build fast"


def test_treebuilder_factories_customize_created_elements_comments_and_pis():
    calls = []

    class MarkerElement(ET.Element):
        pass

    def element_factory(tag, attrs):
        calls.append(("element", tag))
        # factory 返回的节点仍须保留原 tag，否则 TreeBuilder 无法匹配对应的结束标签。
        return MarkerElement(tag, attrs)

    def comment_factory(text):
        calls.append(("comment", text))
        return ET.Comment(text.upper())

    def pi_factory(target, text):
        calls.append(("pi", target, text))
        return ET.ProcessingInstruction(target.upper(), text)

    builder = ET.TreeBuilder(
        element_factory=element_factory,
        comment_factory=comment_factory,
        pi_factory=pi_factory,
        insert_comments=True,
        insert_pis=True,
    )
    parser = ET.XMLParser(target=builder)
    root = ET.fromstring("<root><!--note--><?build fast?></root>", parser=parser)

    assert isinstance(root, MarkerElement)
    assert root.tag == "root"
    assert root[0].text == "NOTE"
    assert root[1].text == "BUILD fast"
    assert calls == [
        ("element", "root"),
        ("comment", "note"),
        ("pi", "build", "fast"),
    ]
