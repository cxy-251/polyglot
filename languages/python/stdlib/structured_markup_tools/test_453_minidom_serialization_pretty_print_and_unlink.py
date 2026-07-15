"""453｜minidom ``writexml``/``toxml``/``toprettyxml`` 与显式 unlink 生命周期。

``toxml()`` 无 encoding 返回 str，显式 encoding 返回 bytes；standalone 会写入声明。3.8 起
序列化保留用户属性顺序。pretty print 会保留树里已有的空白 Text，再叠加缩进，不能用来规范化
语义。大型 DOM 可 ``unlink()`` 提前断开循环引用，Document 上下文管理器会在退出时自动调用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.dom.minidom.Node.writexml
# polyglot-covers: python.xml.dom.minidom.Node.toxml
# polyglot-covers: python.xml.dom.minidom.Node.toprettyxml
# polyglot-covers: python.xml.dom.minidom.serialization-encoding-return-type
# polyglot-covers: python.xml.dom.minidom.serialization-standalone-3.9
# polyglot-covers: python.xml.dom.minidom.serialization-attribute-order-3.8
# polyglot-covers: python.xml.dom.minidom.pretty-print-whitespace-trap
# polyglot-covers: python.xml.dom.minidom.Node.unlink
# polyglot-covers: python.xml.dom.minidom.Node-context-manager

import io
from xml.dom import minidom


def build_document():
    document = minidom.parseString("<root><item>value</item></root>")
    root = document.documentElement
    root.setAttribute("first", "1")
    root.setAttribute("second", '2 & "quoted"')
    return document


def test_toxml_selects_str_or_bytes_and_preserves_attribute_order():
    document = build_document()

    text_wire = document.toxml()
    byte_wire = document.toxml(encoding="utf-8", standalone=True)

    assert isinstance(text_wire, str)
    assert isinstance(byte_wire, bytes)
    assert text_wire.index('first="1"') < text_wire.index("second=")
    assert 'second="2 &amp; &quot;quoted&quot;"' in text_wire
    assert b'encoding="utf-8"' in byte_wire
    assert b'standalone="yes"' in byte_wire


def test_writexml_uses_a_text_writer_and_toprettyxml_controls_indent_and_newline():
    document = build_document()
    writer = io.StringIO()

    result = document.writexml(writer, addindent="  ", newl="\n")
    pretty = document.toprettyxml(indent="--", newl="\r\n")

    assert result is None
    assert writer.getvalue().startswith('<?xml version="1.0" ?>\n')
    assert "\n<root" in writer.getvalue()
    assert "\n  <item>value</item>" in writer.getvalue()
    assert isinstance(pretty, str)
    assert "\r\n<root" in pretty
    assert "\r\n--<item>value</item>" in pretty
    # 若输入树本来含仅空白 Text，pretty printer 会保留它们并再添加缩进。


def test_context_manager_unlinks_the_document_and_descendants_on_exit():
    with minidom.parseString("<root><item/></root>") as document:
        root = document.documentElement
        item = root.firstChild
        assert item.ownerDocument is document

    assert document.childNodes.length == 0
    assert root.ownerDocument is None
    assert root.childNodes.length == 0
    assert item.ownerDocument is None
