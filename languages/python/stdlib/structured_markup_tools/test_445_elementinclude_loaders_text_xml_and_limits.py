"""445｜``ElementInclude`` 的 XML/text 替换、自定义 loader 与递归限制。

``include()`` 就地替换 XInclude 节点：parse=xml 要求 loader 返回 Element，parse=text 返回 str，
并把原 include 的 tail 正确接回树。默认 loader 会访问文件系统；可复现测试和受控资源通常应
传自定义 loader。``base_url`` 负责解析相对 href，``max_depth`` 与循环检测限制递归包含。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementInclude.include
# polyglot-covers: python.xml.etree.ElementInclude.default_loader
# polyglot-covers: python.xml.etree.ElementInclude.custom-loader-protocol
# polyglot-covers: python.xml.etree.ElementInclude.parse-xml-replacement
# polyglot-covers: python.xml.etree.ElementInclude.parse-text-merge
# polyglot-covers: python.xml.etree.ElementInclude.include-preserves-tail
# polyglot-covers: python.xml.etree.ElementInclude.include.base_url
# polyglot-covers: python.xml.etree.ElementInclude.include.max_depth
# polyglot-covers: python.xml.etree.ElementInclude.LimitedRecursiveIncludeError
# polyglot-covers: python.xml.etree.ElementInclude.FatalIncludeError

from xml.etree import ElementInclude
from xml.etree import ElementTree as ET

import pytest


XI = "http://www.w3.org/2001/XInclude"


def test_custom_loader_replaces_xml_and_preserves_the_include_tail():
    root = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="part.xml"/>after</root>'
    )
    calls = []

    def loader(href, parse, encoding=None):
        calls.append((href, parse, encoding))
        return ET.fromstring("<part><value>42</value></part>")

    result = ElementInclude.include(root, loader=loader)

    assert result is None
    assert calls == [("part.xml", "xml", None)]
    assert root[0].tag == "part"
    assert root[0].findtext("value") == "42"
    assert root[0].tail == "after"


def test_text_include_merges_content_into_parent_text_or_previous_tail():
    first = ET.fromstring(
        f'<root xmlns:xi="{XI}">before<xi:include href="note.txt"/>after</root>'
    )
    second = ET.fromstring(
        f'<root xmlns:xi="{XI}"><lead/>before<xi:include href="note.txt"/>'
        "after</root>"
    )

    def text_loader(href, parse, encoding=None):
        assert (href, parse, encoding) == ("note.txt", "text", "utf-8")
        return "INCLUDED"

    first[0].set("parse", "text")
    first[0].set("encoding", "utf-8")
    second[1].set("parse", "text")
    second[1].set("encoding", "utf-8")
    ElementInclude.include(first, loader=text_loader)
    ElementInclude.include(second, loader=text_loader)

    assert first.text == "beforeINCLUDEDafter"
    assert len(first) == 0
    assert second[0].tail == "beforeINCLUDEDafter"
    assert len(second) == 1


def test_default_loader_reads_controlled_temp_files_and_base_url_resolves_href(
    tmp_path,
):
    pieces = tmp_path / "pieces"
    pieces.mkdir()
    xml_path = pieces / "part.xml"
    text_path = pieces / "note.txt"
    xml_path.write_text("<part>value</part>", encoding="utf-8")
    text_path.write_text("中文", encoding="utf-8")

    assert ElementInclude.default_loader(str(xml_path), "xml").tag == "part"
    assert ElementInclude.default_loader(str(text_path), "text", "utf-8") == "中文"

    root = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="pieces/part.xml"/></root>'
    )
    ElementInclude.include(root, base_url=str(tmp_path / "document.xml"))
    assert root[0].tag == "part"


def test_depth_limit_and_circular_href_detection_stop_recursive_includes():
    def nested_loader(href, parse, encoding=None):
        if href == "a.xml":
            return ET.fromstring(
                f'<a xmlns:xi="{XI}"><xi:include href="b.xml"/></a>'
            )
        return ET.Element("b")

    limited = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="a.xml"/></root>'
    )
    with pytest.raises(ElementInclude.LimitedRecursiveIncludeError):
        ElementInclude.include(limited, loader=nested_loader, max_depth=1)

    def circular_loader(href, parse, encoding=None):
        return ET.fromstring(
            f'<part xmlns:xi="{XI}"><xi:include href="same.xml"/></part>'
        )

    circular = ET.fromstring(
        f'<root xmlns:xi="{XI}"><xi:include href="same.xml"/></root>'
    )
    with pytest.raises(ElementInclude.FatalIncludeError, match="recursive include"):
        ElementInclude.include(circular, loader=circular_loader)
