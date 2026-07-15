"""438｜``tostring``、``tostringlist`` 与 ``ElementTree.write`` 的输出契约。

序列化默认返回字节；只有 ``encoding='unicode'`` 返回 ``str``。XML、HTML、text 三种 method
表达的是不同输出模型，空元素和 XML 声明也可独立控制。``write()`` 不替调用者适配二进制/文本
流：编码为字节时写入 binary stream，编码为 unicode 时写入 text stream，否则在写入处报错。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.tostring
# polyglot-covers: python.xml.etree.ElementTree.tostring.encoding
# polyglot-covers: python.xml.etree.ElementTree.tostring.xml_declaration
# polyglot-covers: python.xml.etree.ElementTree.tostring.short_empty_elements
# polyglot-covers: python.xml.etree.ElementTree.tostring.method-xml-html-text
# polyglot-covers: python.xml.etree.ElementTree.tostringlist
# polyglot-covers: python.xml.etree.ElementTree.tostringlist-chunk-boundaries-unspecified
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.write
# polyglot-covers: python.xml.etree.ElementTree.ElementTree.write-stream-type-matches-encoding

import io
from xml.etree import ElementTree as ET

import pytest


def test_tostring_selects_bytes_or_text_and_controls_xml_surface_syntax():
    root = ET.Element("root", {"label": "中文"})
    ET.SubElement(root, "empty")

    default_wire = ET.tostring(root)
    unicode_wire = ET.tostring(root, encoding="unicode", short_empty_elements=False)
    declared_wire = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    assert isinstance(default_wire, bytes)
    assert isinstance(unicode_wire, str)
    assert unicode_wire == '<root label="中文"><empty></empty></root>'
    assert declared_wire.startswith(b"<?xml version='1.0' encoding='utf-8'?>")


def test_serialization_methods_choose_xml_html_or_only_text_content():
    root = ET.Element("div")
    root.text = "before"
    br = ET.SubElement(root, "br")
    br.tail = "after"

    assert ET.tostring(root, encoding="unicode", method="xml") == (
        "<div>before<br />after</div>"
    )
    assert ET.tostring(root, encoding="unicode", method="html") == (
        "<div>before<br>after</div>"
    )
    assert ET.tostring(root, encoding="unicode", method="text") == "beforeafter"


def test_tostringlist_is_a_chunked_form_whose_join_matches_tostring():
    root = ET.fromstring("<root><item>one</item><item>two</item></root>")

    chunks = ET.tostringlist(root, encoding="utf-8")

    assert all(isinstance(chunk, bytes) for chunk in chunks)
    assert b"".join(chunks) == ET.tostring(root, encoding="utf-8")
    # 文档不保证 chunk 数量和边界；消费者只能依赖拼接后的结果。


def test_write_requires_a_stream_matching_the_selected_encoding():
    tree = ET.ElementTree(ET.fromstring("<root>中文</root>"))
    binary = io.BytesIO()
    text = io.StringIO()

    tree.write(binary, encoding="utf-8", xml_declaration=True)
    tree.write(text, encoding="unicode")

    assert b"\xe4\xb8\xad\xe6\x96\x87" in binary.getvalue()
    assert text.getvalue() == "<root>中文</root>"

    with pytest.raises(TypeError):
        tree.write(io.StringIO(), encoding="utf-8")
    with pytest.raises(TypeError):
        tree.write(io.BytesIO(), encoding="unicode")
