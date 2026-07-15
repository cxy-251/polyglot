"""443｜ElementTree 的 C14N 2.0 规范化输出与 ``C14NWriterTarget``。

``canonicalize()`` 生成文本而非字节，统一属性顺序、命名空间声明和空元素形式，适合签名或
逐字节比较前的稳定表示；它不是普通 pretty printer。输入可来自字符串或文件，输出可返回
``str`` 或写入 text stream。``C14NWriterTarget`` 则把解析事件直接流式写成相同规范形式。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.etree.ElementTree.canonicalize
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-text-output
# polyglot-covers: python.xml.etree.ElementTree.canonicalize.xml_data
# polyglot-covers: python.xml.etree.ElementTree.canonicalize.from_file
# polyglot-covers: python.xml.etree.ElementTree.canonicalize.out-text-stream
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-attribute-order
# polyglot-covers: python.xml.etree.ElementTree.canonicalize-expands-empty-elements
# polyglot-covers: python.xml.etree.ElementTree.C14NWriterTarget

import io
from xml.etree import ElementTree as ET


XML_TEXT = '<root z="2" a="1"><empty/><!--note--></root>'


def test_canonicalize_returns_stable_text_and_omits_comments_by_default():
    canonical = ET.canonicalize(XML_TEXT)

    assert isinstance(canonical, str)
    assert canonical == '<root a="1" z="2"><empty></empty></root>'


def test_canonicalize_accepts_a_file_and_writes_to_a_text_stream(tmp_path):
    source = tmp_path / "source.xml"
    source.write_text(XML_TEXT, encoding="utf-8")
    output = io.StringIO()

    result = ET.canonicalize(from_file=source, out=output, with_comments=True)

    assert result is None
    assert output.getvalue() == (
        '<root a="1" z="2"><empty></empty><!--note--></root>'
    )


def test_c14n_writer_target_streams_canonical_text_from_parser_events():
    chunks = []
    target = ET.C14NWriterTarget(chunks.append, with_comments=True)
    parser = ET.XMLParser(target=target)

    parser.feed('<root z="2"')
    parser.feed(' a="1"><empty/><!--note--></root>')
    result = parser.close()

    assert result is None
    assert "".join(chunks) == (
        '<root a="1" z="2"><empty></empty><!--note--></root>'
    )
