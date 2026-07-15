"""415｜email.iterators 的 body 行、MIME 类型筛选与结构调试输出。

body_line_iterator 深度遍历后只展开 str payload，跳过 header 和 bytes payload；
typed_subpart_iterator 按 maintype/subtype 过滤 walk 结果。_structure 很适合人工诊断 MIME 树，
但官方明确把它标为不受支持的私有调试接口，业务逻辑不能依赖其文本格式。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.iterators.body_line_iterator
# polyglot-covers: python.email.iterators.body-line-iterator-skips-headers
# polyglot-covers: python.email.iterators.body-line-iterator-skips-bytes-payload
# polyglot-covers: python.email.iterators.body-line-iterator-line-boundaries
# polyglot-covers: python.email.iterators.typed_subpart_iterator
# polyglot-covers: python.email.iterators.typed-subpart-maintype-default
# polyglot-covers: python.email.iterators.typed-subpart-subtype-filter
# polyglot-covers: python.email.iterators._structure
# polyglot-covers: python.email.iterators.structure-private-debug-interface

from email.iterators import _structure, body_line_iterator, typed_subpart_iterator
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import StringIO


def build_message_tree():
    root = MIMEMultipart()
    root.attach(MIMEText("plain one\nplain two", _subtype="plain"))
    root.attach(MIMEText("<p>html</p>", _subtype="html"))
    binary = Message()
    binary["Content-Type"] = "application/octet-stream"
    binary.set_payload(b"\x00\xff")
    root.attach(binary)
    return root


def test_body_line_iterator_yields_string_payload_lines_not_headers_or_bytes():
    lines = list(body_line_iterator(build_message_tree()))
    assert lines == ["plain one\n", "plain two", "<p>html</p>"]


def test_typed_iterator_filters_by_main_type_and_optional_subtype():
    root = build_message_tree()
    text_parts = list(typed_subpart_iterator(root))
    html_parts = list(typed_subpart_iterator(root, subtype="html"))

    assert [part.get_content_subtype() for part in text_parts] == ["plain", "html"]
    assert html_parts == [text_parts[1]]


def test_structure_prints_an_indented_debug_view_to_a_supplied_stream():
    output = StringIO()
    _structure(build_message_tree(), fp=output)

    assert output.getvalue().splitlines() == [
        "multipart/mixed",
        "    text/plain",
        "    text/html",
        "    application/octet-stream",
    ]
