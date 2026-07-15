"""470｜Expat XML 声明、DOCTYPE、元素 content model、属性与实体声明回调。

Expat 是 non-validating parser，但会读取声明并以专用 handler 报告。ElementDecl 的 model 是
``(type, quantifier, name, children)`` 递归元组，常量来自 ``expat.model``；Attlist 区分默认值
与 required。内部、外部和 NDATA 实体在 EntityDecl 的参数组合不同，不能只看 entityName。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.parsers.expat.xmlparser.XmlDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.StartDoctypeDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EndDoctypeDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.ElementDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.AttlistDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.EntityDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.NotationDeclHandler
# polyglot-covers: python.xml.parsers.expat.xmlparser.UnparsedEntityDeclHandler
# polyglot-covers: python.xml.parsers.expat-content-model-tuple
# polyglot-covers: python.xml.parsers.expat.model.XML_CTYPE_SEQ
# polyglot-covers: python.xml.parsers.expat.model.XML_CTYPE_NAME
# polyglot-covers: python.xml.parsers.expat.model.XML_CQUANT_PLUS

from xml.parsers import expat


XML_TEXT = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE root [
  <!ELEMENT root (item+)>
  <!ELEMENT item (#PCDATA)>
  <!ATTLIST item id ID #REQUIRED>
  <!ENTITY word "hello">
  <!NOTATION png SYSTEM "image/png">
  <!ENTITY logo SYSTEM "logo.png" NDATA png>
]>
<root><item id="one">&word;</item></root>
"""


def test_declaration_handlers_receive_typed_dtd_information():
    parser = expat.ParserCreate()
    declarations = {
        "xml": [],
        "doctype": [],
        "models": {},
        "attributes": [],
        "entities": [],
        "notations": [],
        "unparsed": [],
    }
    parser.XmlDeclHandler = lambda *args: declarations["xml"].append(args)
    parser.StartDoctypeDeclHandler = lambda *args: declarations["doctype"].append(
        ("start", *args)
    )
    parser.EndDoctypeDeclHandler = lambda: declarations["doctype"].append(("end",))
    parser.ElementDeclHandler = lambda name, model_: declarations["models"].update(
        {name: model_}
    )
    parser.AttlistDeclHandler = lambda *args: declarations["attributes"].append(args)
    parser.EntityDeclHandler = lambda *args: declarations["entities"].append(args)
    parser.NotationDeclHandler = lambda *args: declarations["notations"].append(args)
    parser.UnparsedEntityDeclHandler = lambda *args: declarations["unparsed"].append(
        args
    )

    parser.Parse(XML_TEXT, True)

    assert declarations["xml"] == [("1.0", "UTF-8", 1)]
    assert declarations["doctype"] == [
        ("start", "root", None, None, 1),
        ("end",),
    ]

    root_model = declarations["models"]["root"]
    assert root_model[0] == expat.model.XML_CTYPE_SEQ
    assert root_model[3][0][0] == expat.model.XML_CTYPE_NAME
    assert root_model[3][0][1] == expat.model.XML_CQUANT_PLUS
    assert root_model[3][0][2] == "item"

    assert ("item", "id", "ID", None, 1) in declarations["attributes"]
    assert any(event[0] == "word" and event[2] == "hello" for event in declarations["entities"])
    assert any(
        event[0] == "logo" and event[4] == "logo.png" and event[6] == "png"
        for event in declarations["entities"]
    )
    assert declarations["notations"] == [("png", None, "image/png", None)]
    assert declarations["unparsed"] == [
        ("logo", None, "logo.png", None, "png")
    ]
