"""411｜compat32 Message 的 Unix-From、list payload 与 set_charset。

Message 的 payload 可能是标量，也可能是子 Message 列表；is_multipart 判断的是实际 list 形状，
不只是 Content-Type 文本。attach 从 None 建立 list，get_payload 返回的 list 是活对象。旧式
set_charset 会补 MIME headers 并编码 payload，现代 EmailMessage 则应使用 set_content。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.compat32.Message
# polyglot-covers: python.email.compat32.Message-default-policy
# polyglot-covers: python.email.compat32.set_unixfrom
# polyglot-covers: python.email.compat32.get_unixfrom
# polyglot-covers: python.email.compat32.as_string-unixfrom
# polyglot-covers: python.email.compat32.as_bytes-unixfrom
# polyglot-covers: python.email.compat32.attach-list-payload
# polyglot-covers: python.email.compat32.get_payload-index
# polyglot-covers: python.email.compat32.get-payload-live-list
# polyglot-covers: python.email.compat32.get-payload-scalar-index-typeerror
# polyglot-covers: python.email.compat32.get-payload-decode-multipart-none
# polyglot-covers: python.email.compat32.set_payload
# polyglot-covers: python.email.compat32.set_charset
# polyglot-covers: python.email.compat32.get_charset
# polyglot-covers: python.email.compat32.set-charset-none-removes-param

from email import policy
from email.message import Message

import pytest


def test_unixfrom_is_envelope_metadata_and_only_serializes_when_requested():
    message = Message()
    message["Subject"] = "example"
    message.set_payload("body")
    message.set_unixfrom("From sender@example.test Sat Jan  1 00:00:00 2000")

    assert message.policy is policy.compat32
    assert message.get_unixfrom().startswith("From sender@example.test")
    assert not message.as_string().startswith("From ")
    assert message.as_string(unixfrom=True).startswith("From sender@example.test")
    assert message.as_bytes(unixfrom=True).startswith(b"From sender@example.test")


def test_attach_creates_a_live_list_payload_with_indexed_access():
    container = Message()
    first = Message()
    second = Message()
    container.attach(first)

    assert container.is_multipart() is True
    assert container.get_payload(0) is first
    payload = container.get_payload()
    payload.append(second)
    assert container.get_payload(1) is second
    assert container.get_payload(decode=True) is None

    scalar = Message()
    scalar.set_payload("text")
    with pytest.raises(TypeError):
        scalar.get_payload(0)


def test_set_charset_adds_mime_metadata_encodes_payload_and_can_remove_parameter():
    message = Message()
    message.set_payload("café")
    message.set_charset("utf-8")

    assert message.get_charset().input_charset == "utf-8"
    assert message["MIME-Version"] == "1.0"
    assert message.get_content_type() == "text/plain"
    assert message.get_content_charset() == "utf-8"
    assert message.get_payload(decode=True) == "café".encode()

    message.set_charset(None)
    assert message.get_charset() is None
    assert message.get_content_charset() is None
