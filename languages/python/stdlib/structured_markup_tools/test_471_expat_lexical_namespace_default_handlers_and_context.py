"""471｜Expat PI/comment/CDATA/namespace 回调、DefaultHandler 差异与输入上下文。

CharacterData 无法区分普通文本和 CDATA，必须结合 start/end CDATA 回调。namespace 声明事件
在对应 start element 前、end element 后出现。``DefaultHandler`` 会抑制内部实体展开并看到原
引用；``DefaultHandlerExpand`` 允许展开。GetInputContext 和当前位置只应在事件回调内解释。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.parsers.expat.xmlparser.ProcessingInstructionHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.CommentHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartCdataSectionHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndCdataSectionHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartNamespaceDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndNamespaceDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.DefaultHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.DefaultHandlerExpand
# polyglot-covers: python.xml.parsers.expat.xmlparser.GetInputContext
# polyglot-covers: python.xml.parsers.expat.xmlparser.CurrentLineNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.CurrentColumnNumber
# polyglot-covers: python.xml.parsers.expat.xmlparser.CurrentByteIndex

from xml.parsers import expat


def test_lexical_and_namespace_callbacks_surround_content_events_in_source_order():
    parser = expat.ParserCreate(namespace_separator="|")
    events = []
    contexts = []

    def start(name, attrs):
        events.append(("start", name))
        contexts.append(
            (
                parser.GetInputContext(),
                parser.CurrentLineNumber,
                parser.CurrentColumnNumber,
                parser.CurrentByteIndex,
            )
        )

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: events.append(("end", name))
    parser.StartNamespaceDeclHandler = lambda prefix, uri: events.append(
        ("start-ns", prefix, uri)
    )
    parser.EndNamespaceDeclHandler = lambda prefix: events.append(("end-ns", prefix))
    parser.ProcessingInstructionHandler = lambda target, data: events.append(
        ("pi", target, data)
    )
    parser.CommentHandler = lambda data: events.append(("comment", data))
    parser.StartCdataSectionHandler = lambda: events.append(("start-cdata",))
    parser.EndCdataSectionHandler = lambda: events.append(("end-cdata",))
    parser.CharacterDataHandler = lambda data: events.append(("text", data))

    parser.Parse(
        '<?build fast?><root xmlns:p="urn:p"><p:item><![CDATA[x<y]]>'
        "<!--note--></p:item></root>",
        True,
    )

    assert events.index(("start-ns", "p", "urn:p")) < events.index(
        ("start", "root")
    )
    assert events.index(("end", "root")) < events.index(("end-ns", "p"))
    assert ("pi", "build", "fast") in events
    assert ("start-cdata",) in events and ("end-cdata",) in events
    assert ("text", "x<y") in events
    assert ("comment", "note") in events
    assert all(context is not None for context, *_ in contexts)
    assert all(line >= 1 and column >= 0 and byte >= 0 for _, line, column, byte in contexts)


def test_default_handler_expand_changes_internal_entity_dispatch():
    xml = '<!DOCTYPE root [<!ENTITY word "VALUE">]><root>&word;</root>'
    raw_tokens = []
    raw_chars = []
    raw = expat.ParserCreate()
    raw.DefaultHandler = raw_tokens.append
    raw.CharacterDataHandler = raw_chars.append
    raw.Parse(xml, True)

    expanded_tokens = []
    expanded_chars = []
    expanded = expat.ParserCreate()
    expanded.DefaultHandlerExpand = expanded_tokens.append
    expanded.CharacterDataHandler = expanded_chars.append
    expanded.Parse(xml, True)

    assert "&word;" in "".join(raw_tokens)
    assert raw_chars == []
    assert "&word;" not in "".join(expanded_tokens)
    assert "".join(expanded_chars) == "VALUE"
