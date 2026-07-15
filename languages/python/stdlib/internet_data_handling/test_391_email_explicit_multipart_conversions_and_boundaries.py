"""391｜make_related/make_alternative/make_mixed 的逐层转换与 boundary。

make_* 会把现有 Content-* 与 payload 移进新的第一个子 part，而不是丢弃正文；只允许按
non-multipart → related → alternative → mixed 的兼容方向转换。显式 boundary 便于可重复 fixture，
生产代码通常留空，让 generator 在首次 flatten 时生成唯一值。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.message.make_related
# polyglot-covers: python.email.message.make_alternative
# polyglot-covers: python.email.message.make_mixed
# polyglot-covers: python.email.make-multipart-moves-existing-content-first
# polyglot-covers: python.email.make-multipart-explicit-boundary
# polyglot-covers: python.email.get_boundary
# polyglot-covers: python.email.invalid-multipart-conversion-typeerror
# polyglot-covers: python.email.message.preamble
# polyglot-covers: python.email.message.epilogue
# polyglot-covers: python.email.multipart-preamble-epilogue-outside-boundaries

from email import policy
from email.message import EmailMessage
from email.parser import BytesParser

import pytest


def test_explicit_conversions_keep_the_existing_tree_as_the_first_part():
    message = EmailMessage()
    message.set_content("root body")

    message.make_related(boundary="RELATED-BOUNDARY")
    assert message.get_content_type() == "multipart/related"
    assert message.get_boundary() == "RELATED-BOUNDARY"
    assert list(message.iter_parts())[0].get_content().strip() == "root body"

    message.make_alternative(boundary="ALTERNATIVE-BOUNDARY")
    assert message.get_content_type() == "multipart/alternative"
    assert message.get_boundary() == "ALTERNATIVE-BOUNDARY"
    assert list(message.iter_parts())[0].get_content_type() == "multipart/related"

    message.make_mixed(boundary="MIXED-BOUNDARY")
    assert message.get_content_type() == "multipart/mixed"
    assert message.get_boundary() == "MIXED-BOUNDARY"
    assert list(message.iter_parts())[0].get_content_type() == "multipart/alternative"


def test_mixed_container_cannot_be_converted_back_to_related_or_alternative():
    message = EmailMessage()
    message.make_mixed()
    with pytest.raises(TypeError):
        message.make_related()
    with pytest.raises(TypeError):
        message.make_alternative()


def test_preamble_and_epilogue_round_trip_outside_multipart_boundaries():
    message = EmailMessage()
    message.make_mixed(boundary="BOUNDARY")
    child = EmailMessage()
    child.set_content("inside")
    message.attach(child)
    message.preamble = "text before the first boundary"
    message.epilogue = "text after the closing boundary"

    wire = message.as_bytes(policy=policy.SMTP)
    assert b"text before the first boundary\r\n--BOUNDARY" in wire
    assert b"--BOUNDARY--\r\ntext after the closing boundary" in wire
    parsed = BytesParser(policy=policy.default).parsebytes(wire)
    assert parsed.preamble == "text before the first boundary"
    assert parsed.epilogue == "text after the closing boundary"
