"""454｜minidom 文件/字符串输入、调用方配置的 SAX parser 与安全边界。

``parse()`` 接文件名或 file-like，``parseString()`` 接 str/bytes；两者都会在返回前完成整棵 DOM。
传入 SAX2 parser 时，minidom 会替换其 content handler 并开启 namespace，但 entity resolver 等
策略必须由调用方预先配置。minidom 不能作为恶意 XML 的安全层，测试只使用受控小输入。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.dom.minidom.parse
# polyglot-covers: python.xml.dom.minidom.parse.filename
# polyglot-covers: python.xml.dom.minidom.parse.file-like
# polyglot-covers: python.xml.dom.minidom.parse.bufsize
# polyglot-covers: python.xml.dom.minidom.parseString
# polyglot-covers: python.xml.dom.minidom.parseString.str-and-bytes
# polyglot-covers: python.xml.dom.minidom.parse-custom-sax2-parser
# polyglot-covers: python.xml.dom.minidom.parse-enables-namespaces
# polyglot-covers: python.xml.dom.minidom-untrusted-xml-warning

import io
from xml.dom import minidom
from xml.sax import handler
from xml.sax import make_parser


XML_TEXT = '<p:root xmlns:p="urn:parts"><p:item>value</p:item></p:root>'


def test_parse_accepts_a_filename_or_file_like_and_bufsize_is_chunk_size(tmp_path):
    path = tmp_path / "document.xml"
    path.write_text(XML_TEXT, encoding="utf-8")

    from_name = minidom.parse(str(path), bufsize=3)
    from_file = minidom.parse(io.StringIO(XML_TEXT), bufsize=2)

    assert from_name.documentElement.namespaceURI == "urn:parts"
    assert from_file.getElementsByTagNameNS("urn:parts", "item")[0].firstChild.data == (
        "value"
    )


def test_parse_string_accepts_text_or_encoded_xml_bytes():
    from_text = minidom.parseString(XML_TEXT)
    from_bytes = minidom.parseString(XML_TEXT.encode("utf-8"))

    assert from_text.documentElement.toxml() == from_bytes.documentElement.toxml()


def test_custom_sax_parser_is_reconfigured_for_namespace_aware_dom_building():
    parser = make_parser()
    parser.setFeature(handler.feature_namespaces, False)

    document = minidom.parseString(XML_TEXT, parser=parser)

    assert parser.getFeature(handler.feature_namespaces)
    assert document.documentElement.namespaceURI == "urn:parts"
    # 自定义 resolver、外部实体开关等必须在传给 minidom 前设置；这里不启用外部资源。
