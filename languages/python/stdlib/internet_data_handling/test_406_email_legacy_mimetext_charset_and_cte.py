"""406｜MIMEText 的 charset 推断，以及已有 CTE header 带来的旧 API 陷阱。

纯 ASCII 文本默认 us-ascii，非 ASCII 文本默认 utf-8，并会生成对应传输编码。一个容易忽略的
兼容行为是：已有 Content-Transfer-Encoding 时，set_payload(..., charset=...) 假定 payload
已正确编码而不再转换。若要重新编码，必须先删除旧 CTE header，或改用现代 set_content。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.mime.MIMEText
# polyglot-covers: python.email.mime.MIMEText-default-subtype
# polyglot-covers: python.email.mime.MIMEText-ascii-charset
# polyglot-covers: python.email.mime.MIMEText-unicode-utf8-charset
# polyglot-covers: python.email.mime.MIMEText-content-transfer-encoding
# polyglot-covers: python.email.mime.MIMEText-existing-cte-prevents-reencoding
# polyglot-covers: python.email.mime.MIMEText-delete-cte-before-reencoding

from email.mime.text import MIMEText


def test_mimetext_selects_ascii_or_utf8_and_preserves_decoded_content():
    ascii_part = MIMEText("plain text")
    unicode_part = MIMEText("中文")

    assert ascii_part.get_content_type() == "text/plain"
    assert ascii_part.get_content_charset() == "us-ascii"
    assert ascii_part["Content-Transfer-Encoding"] == "7bit"
    assert unicode_part.get_content_charset() == "utf-8"
    assert unicode_part.get_payload(decode=True) == "中文".encode()


def test_existing_transfer_encoding_must_be_removed_before_set_payload_reencodes():
    part = MIMEText("first", _charset="utf-8")
    assert part["Content-Transfer-Encoding"] == "base64"

    # 旧 CTE 仍在时，新字符串被原样放入 payload；header 与实际内容已经不一致。
    part.set_payload("second", charset="utf-8")
    assert part.get_payload() == "second"

    del part["Content-Transfer-Encoding"]
    part.set_payload("second", charset="utf-8")
    assert part["Content-Transfer-Encoding"] == "base64"
    assert part.get_payload() != "second"
    assert part.get_payload(decode=True) == b"second"
