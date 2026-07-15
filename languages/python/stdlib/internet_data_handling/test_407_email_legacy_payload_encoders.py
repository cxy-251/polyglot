"""407｜email.encoders 的 base64、quoted-printable、7bit/8bit 与 noop。

这些函数原地读取 Message payload、写回传输形式并设置 CTE header；multipart 没有单一 payload，
因此必须对子 part 编码而不能对容器编码。它们属于已弃用的 compat32 API，现代代码应通过
set_content(..., cte=...) 选择编码，但旧消息构造器仍在内部使用相同协议。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.encoders.encode_base64
# polyglot-covers: python.email.encoders.encode_quopri
# polyglot-covers: python.email.encoders.encode-quopri-encodes-whitespace
# polyglot-covers: python.email.encoders.encode_7or8bit
# polyglot-covers: python.email.encoders.encode-7or8bit-ascii
# polyglot-covers: python.email.encoders.encode-7or8bit-nonascii
# polyglot-covers: python.email.encoders.encode_noop
# polyglot-covers: python.email.encoders.multipart-type-error
# polyglot-covers: python.email.encoders.deprecated-modern-cte-alternative

from email.encoders import encode_7or8bit, encode_base64, encode_noop, encode_quopri
from email.message import Message
from email.mime.multipart import MIMEMultipart

import pytest


def message_with_bytes(payload):
    message = Message()
    message.set_payload(payload)
    return message


def test_base64_and_quoted_printable_encoders_round_trip_binary_payloads():
    raw = b"data\x00 with\tspace "
    base64_message = message_with_bytes(raw)
    quoted_message = message_with_bytes(raw)

    encode_base64(base64_message)
    encode_quopri(quoted_message)

    assert base64_message["Content-Transfer-Encoding"] == "base64"
    assert quoted_message["Content-Transfer-Encoding"] == "quoted-printable"
    assert base64_message.get_payload(decode=True) == raw
    assert quoted_message.get_payload(decode=True) == raw
    # legacy quoted-printable encoder 连普通空格和 tab 也编码，不能期待人类可读性完全不变。
    assert "=09" in quoted_message.get_payload()
    assert "=20" in quoted_message.get_payload()


def test_7or8bit_inspects_ascii_decodability_while_noop_changes_nothing():
    ascii_message = message_with_bytes(b"ASCII")
    binary_message = message_with_bytes(b"\xff")
    untouched = message_with_bytes(b"raw")

    encode_7or8bit(ascii_message)
    encode_7or8bit(binary_message)
    encode_noop(untouched)

    assert ascii_message["Content-Transfer-Encoding"] == "7bit"
    assert binary_message["Content-Transfer-Encoding"] == "8bit"
    assert untouched.get_payload() == b"raw"
    assert untouched["Content-Transfer-Encoding"] is None


def test_encoder_must_be_applied_to_leaf_parts_not_a_multipart_container():
    with pytest.raises(TypeError):
        encode_base64(MIMEMultipart())
