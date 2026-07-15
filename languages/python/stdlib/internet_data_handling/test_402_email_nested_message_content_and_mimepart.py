"""402｜message/rfc822 的 list payload、is_multipart 与 MIMEPart 差异。

把 EmailMessage 作为内容会建立 message/rfc822，payload 是含一个子消息的 list，因此
is_multipart=True，即使 maintype 不是 multipart；walk/iter_parts 仍会下降。EmailMessage.set_content
补 MIME-Version，而 MIMEPart 用于子 part，不自动加该 header，避免每层重复。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.message.MIMEPart
# polyglot-covers: python.email.mimepart-no-automatic-mime-version
# polyglot-covers: python.email.emailmessage-automatic-mime-version
# polyglot-covers: python.email.set-content-message-rfc822
# polyglot-covers: python.email.get-content-message-returns-message
# polyglot-covers: python.email.message-rfc822-list-payload
# polyglot-covers: python.email.is-multipart-based-on-list-payload
# polyglot-covers: python.email.message-maintype-can-be-multipart-behavior
# polyglot-covers: python.email.message-partial-requires-bytes
# polyglot-covers: python.email.message-rfc822-cte-restrictions

from email.message import EmailMessage, MIMEPart

import pytest


def test_mimepart_omits_top_level_mime_version_header():
    top_level = EmailMessage()
    top_level.set_content("body")
    part = MIMEPart()
    part.set_content("body")
    assert str(top_level["MIME-Version"]) == "1.0"
    assert part["MIME-Version"] is None


def test_nested_message_is_a_container_even_though_maintype_is_message():
    inner = EmailMessage()
    inner["Subject"] = "forwarded"
    inner.set_content("nested body")
    outer = EmailMessage()
    outer.set_content(inner)

    assert outer.get_content_type() == "message/rfc822"
    assert outer.get_content_maintype() == "message"
    assert outer.is_multipart() is True
    assert outer.get_payload() == [inner]
    assert list(outer.iter_parts()) == [inner]
    assert outer.get_content() is inner
    assert [part.get_content_type() for part in outer.walk()] == [
        "message/rfc822",
        "text/plain",
    ]


def test_message_partial_and_rfc822_reject_incompatible_object_cte_options():
    inner = EmailMessage()
    inner.set_content("nested")
    with pytest.raises(TypeError):
        EmailMessage().set_content(inner, subtype="partial")
    with pytest.raises(ValueError):
        EmailMessage().set_content(inner, cte="base64")
