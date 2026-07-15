"""403｜RFC 2231 filename、Content-Type 参数、boundary、默认类型与手动 attach。

add_header 会把非 ASCII filename 作为 RFC 2231 参数序列化，get_filename 返回解码且去引号值。
set_param(replace=True)、del_param 与 set_boundary 原位重写 header，保留 header 顺序；无
Content-Type 时 set_boundary 抛 HeaderParseError。default type 不是 header，只影响缺失时的解释。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.message.add_header
# polyglot-covers: python.email.rfc2231-nonascii-filename
# polyglot-covers: python.email.get_filename
# polyglot-covers: python.email.get-filename-content-type-name-fallback
# polyglot-covers: python.email.set_param
# polyglot-covers: python.email.del_param
# polyglot-covers: python.email.set-param-replace-preserves-header-position
# polyglot-covers: python.email.set_boundary
# polyglot-covers: python.email.set-boundary-preserves-header-position
# polyglot-covers: python.email.set-boundary-without-content-type-error
# polyglot-covers: python.email.get_default_type
# polyglot-covers: python.email.set_default_type
# polyglot-covers: python.email.default-type-not-stored-as-header
# polyglot-covers: python.email.message.attach
# polyglot-covers: python.email.attach-requires-list-payload
# polyglot-covers: python.email.multipart-get-charsets-walk-order
# polyglot-covers: python.email.message.get_param
# polyglot-covers: python.email.message.get_params
# polyglot-covers: python.email.message.set_type
# polyglot-covers: python.email.set-type-adds-mime-version
# polyglot-covers: python.email.set-type-invalid-valueerror

from email.errors import HeaderParseError
from email.message import EmailMessage

import pytest


def test_nonascii_filename_round_trips_and_serializes_as_rfc2231():
    message = EmailMessage()
    message.set_content(b"PDF", maintype="application", subtype="pdf")
    message.add_header("Content-Disposition", "attachment", filename="résumé.pdf")
    assert message.get_filename() == "résumé.pdf"
    serialized = message.as_bytes()
    assert b"filename*=utf-8''r%C3%A9sum%C3%A9.pdf" in serialized

    fallback = EmailMessage()
    fallback["Content-Type"] = 'application/octet-stream; name="fallback.bin"'
    assert fallback.get_filename() == "fallback.bin"


def test_parameter_and_boundary_updates_preserve_content_type_header_position():
    message = EmailMessage()
    message["X-Before"] = "one"
    message["Content-Type"] = "text/plain; charset=utf-8"
    message["X-After"] = "two"

    message.set_param("format", "flowed", replace=True)
    assert message.keys() == ["X-Before", "Content-Type", "X-After"]
    assert message["Content-Type"].params["format"] == "flowed"
    message.del_param("format")
    assert "format" not in message["Content-Type"].params

    message.set_boundary("boundary with space")
    assert message.get_boundary() == "boundary with space"
    assert message.keys() == ["X-Before", "Content-Type", "X-After"]
    with pytest.raises(HeaderParseError):
        EmailMessage().set_boundary("missing content type")


def test_default_type_is_metadata_and_manual_attach_builds_a_list_payload():
    blank = EmailMessage()
    assert blank.get_default_type() == "text/plain"
    blank.set_default_type("message/rfc822")
    assert blank.get_content_type() == "message/rfc822"
    assert blank["Content-Type"] is None

    container = EmailMessage()
    container.make_mixed()
    text = EmailMessage()
    text.set_content("text", charset="utf-8")
    binary = EmailMessage()
    binary.set_content(b"bin", maintype="application", subtype="octet-stream")
    container.attach(text)
    container.attach(binary)
    assert container.get_charsets() == [None, "utf-8", None]

    scalar = EmailMessage()
    scalar.set_content("already scalar")
    with pytest.raises(TypeError):
        scalar.attach(EmailMessage())


def test_legacy_parameter_access_and_set_type_preserve_structured_mime_metadata():
    message = EmailMessage()
    message["Content-Type"] = 'text/plain; charset="utf-8"; format=flowed'

    assert message.get_param("CHARSET") == "utf-8"
    assert ("format", "flowed") in message.get_params()
    message.set_type("application/json")
    assert message.get_content_type() == "application/json"
    assert message.get_param("charset") == "utf-8"
    assert message["MIME-Version"] == "1.0"
    with pytest.raises(ValueError):
        message.set_type("missing-slash")
