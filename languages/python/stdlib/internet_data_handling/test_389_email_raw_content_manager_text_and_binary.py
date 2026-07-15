"""389｜raw_data_manager 的 text/binary 内容、CTE 与附件元数据。

set_content(str) 建立 text/*、charset 与合适的 Content-Transfer-Encoding，get_content 自动解码为
Unicode；bytes 必须显式给 maintype/subtype，默认 base64，get_content 返回原 bytes。filename 会
隐式创建 attachment disposition。clear_content 只移除 payload 与 Content-*，clear 才清空全部。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.contentmanager.raw_data_manager
# polyglot-covers: python.email.message.set_content
# polyglot-covers: python.email.message.get_content
# polyglot-covers: python.email.set-content-str-text-plain
# polyglot-covers: python.email.set-content-text-charset
# polyglot-covers: python.email.set-content-text-cte
# polyglot-covers: python.email.set-content-bytes-requires-mimetype
# polyglot-covers: python.email.set-content-bytes-default-base64
# polyglot-covers: python.email.set-content-filename-implies-attachment
# polyglot-covers: python.email.set-content-cid-params-headers
# polyglot-covers: python.email.get_content_type
# polyglot-covers: python.email.get_content_maintype
# polyglot-covers: python.email.get_content_subtype
# polyglot-covers: python.email.get_content_charset
# polyglot-covers: python.email.get_charsets
# polyglot-covers: python.email.get_content_disposition
# polyglot-covers: python.email.is_attachment
# polyglot-covers: python.email.clear_content
# polyglot-covers: python.email.clear
# polyglot-covers: python.email.clear-content-keeps-non-content-headers

from email.message import EmailMessage

import pytest


def test_text_content_is_encoded_for_transport_and_decoded_for_application_use():
    message = EmailMessage()
    message["Subject"] = "text"
    message.set_content("你好", charset="utf-8", cte="quoted-printable")

    assert message.get_content_type() == "text/plain"
    assert message.get_content_maintype() == "text"
    assert message.get_content_subtype() == "plain"
    assert message.get_content_charset() == "utf-8"
    assert message.get_charsets() == ["utf-8"]
    assert str(message["Content-Transfer-Encoding"]) == "quoted-printable"
    assert message.get_content() == "你好\n"
    assert message.get_payload(decode=True) == "你好\n".encode("utf-8")

    with pytest.raises(ValueError):
        EmailMessage().set_content("你好", cte="7bit")


def test_binary_content_requires_type_and_carries_attachment_metadata():
    payload = b"\0\xffbinary"
    message = EmailMessage()
    message["X-Owner"] = "polyglot"
    with pytest.raises(TypeError):
        message.set_content(payload)

    message.set_content(
        payload,
        maintype="application",
        subtype="octet-stream",
        filename="数据.bin",
        cid="<blob@example.test>",
        params={"x-format": "demo"},
        headers=["X-Part: one"],
    )
    assert message.get_content() == payload
    assert str(message["Content-Transfer-Encoding"]) == "base64"
    assert message.get_content_disposition() == "attachment"
    assert message.is_attachment() is True
    assert message.get_filename() == "数据.bin"
    assert str(message["Content-ID"]) == "<blob@example.test>"
    assert message["Content-Type"].params["x-format"] == "demo"
    assert str(message["X-Part"]) == "one"

    message.clear_content()
    assert message.get_payload() is None
    assert "Content-Type" not in message
    assert "Content-Disposition" not in message
    assert "X-Owner" in message
    assert "MIME-Version" in message
    message.clear()
    assert len(message) == 0
