"""468｜Expat ParserCreate、基础回调、分块 Parse、ParseFile 与单文档生命周期。

``xml.parsers.expat`` 是 pyexpat 的推荐入口；直接导入 ``pyexpat`` 已弃用。ParserCreate 返回的
stateful parser 通过属性安装回调，``Parse(data, isfinal)`` 可拼接同一文档的输入块，最后一块
必须标 final。一个 parser 只能解析一份 XML；完成后应新建实例，不能把第二份文档继续喂入。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.parsers.expat.ParserCreate
# polyglot-covers: python.xml.parsers.expat.XMLParserType
# polyglot-covers: python.xml.parsers.expat.xmlparser.Parse
# polyglot-covers: python.xml.parsers.expat.xmlparser.ParseFile
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartElementHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndElementHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.CharacterDataHandler
# polyglot-covers: python.xml.parsers.expat.Parse-isfinal
# polyglot-covers: python.xml.parsers.expat-parser-single-document
# polyglot-covers: python.pyexpat-direct-import-deprecated

import io
from xml.parsers import expat

import pytest


def test_parser_callbacks_receive_ordered_structure_from_fragmented_input():
    parser = expat.ParserCreate()
    events = []
    parser.StartElementHandler = lambda name, attrs: events.append(
        ("start", name, attrs)
    )
    parser.EndElementHandler = lambda name: events.append(("end", name))
    parser.CharacterDataHandler = lambda data: events.append(("text", data))

    assert isinstance(parser, expat.XMLParserType)
    parser.Parse("<root id='one'><item>", False)
    parser.Parse("value", False)
    parser.Parse("</item></root>", True)

    structural = [event for event in events if event[0] != "text"]
    assert structural == [
        ("start", "root", {"id": "one"}),
        ("start", "item", {}),
        ("end", "item"),
        ("end", "root"),
    ]
    assert "".join(event[1] for event in events if event[0] == "text") == "value"


def test_parsefile_only_requires_a_binary_read_method():
    parser = expat.ParserCreate()
    names = []
    parser.StartElementHandler = lambda name, attrs: names.append(name)

    parser.ParseFile(io.BytesIO(b"<root><item/></root>"))

    assert names == ["root", "item"]


def test_finished_parser_rejects_a_second_document():
    parser = expat.ParserCreate()
    parser.Parse("<first/>", True)

    with pytest.raises(expat.ExpatError) as caught:
        parser.Parse("<second/>", True)

    assert caught.value.code == expat.errors.codes[expat.errors.XML_ERROR_FINISHED]
