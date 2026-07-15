"""393｜as_string/as_bytes、UTF-8 表示、policy override 与 flatten 副作用。

as_string 默认生成 7-bit-clean header，非 ASCII 用 encoded-word；str(msg) 临时 clone utf8=True，
用于可读展示而非直接 SMTP 发送。as_bytes/bytes 产生 binary。multipart boundary 可在首次 flatten
时补入并修改原对象，因此“只序列化”并非严格无副作用；需要稳定输出时应提前固定 boundary。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.message.as_string
# polyglot-covers: python.email.message.__str__
# polyglot-covers: python.email.as-string-seven-bit-clean
# polyglot-covers: python.email.str-message-utf8-readable
# polyglot-covers: python.email.message.as_bytes
# polyglot-covers: python.email.message.__bytes__
# polyglot-covers: python.email.serialization-policy-override
# polyglot-covers: python.email.smtp-crlf-lines
# polyglot-covers: python.email.flatten-may-generate-boundary
# polyglot-covers: python.email.flatten-can-mutate-message-trap
# polyglot-covers: python.email.set_unixfrom
# polyglot-covers: python.email.get_unixfrom
# polyglot-covers: python.email.serialize-unixfrom

from email import policy
from email.message import EmailMessage


def test_string_and_bytes_conveniences_use_different_unicode_and_line_policies():
    message = EmailMessage()
    message["From"] = "sender@example.test"
    message["Subject"] = "中文主题"
    message.set_content("正文")

    seven_bit = message.as_string()
    readable = str(message)
    assert "中文主题" not in seven_bit
    assert "=?utf-8?" in seven_bit.lower()
    assert "中文主题" in readable

    default_bytes = message.as_bytes()
    assert bytes(message) == default_bytes
    smtp_bytes = message.as_bytes(policy=policy.SMTP)
    assert b"\r\n" in smtp_bytes
    assert b"\n" not in smtp_bytes.replace(b"\r\n", b"")


def test_first_flatten_generates_and_stores_a_multipart_boundary():
    message = EmailMessage()
    message.set_content("plain")
    message.add_alternative("<p>html</p>", subtype="html")
    assert message.get_boundary() is None

    serialized = message.as_bytes()
    boundary = message.get_boundary()
    assert boundary is not None
    assert boundary.encode("ascii") in serialized
    assert message.as_bytes() == serialized


def test_unixfrom_is_envelope_metadata_outside_the_header_mapping():
    message = EmailMessage()
    message["Subject"] = "stored in mbox"
    message.set_content("body")
    assert message.get_unixfrom() is None
    message.set_unixfrom("From sender@example.test Sat Jan  1 00:00:00 2022")
    assert "unixfrom" not in message
    assert message.as_string(unixfrom=False).startswith("Subject:")
    assert message.as_string(unixfrom=True).startswith("From sender@example.test")
