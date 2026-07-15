"""404｜legacy MIMEBase、MIMEMultipart 与 MIMENonMultipart。

email.mime 属于 compat32 API：MIMEBase 自动补 Content-Type 和 MIME-Version；multipart
把子消息保存在 list payload 中，并延迟生成 boundary；non-multipart 则主动禁止 attach。
现代代码通常优先使用 EmailMessage.set_content/add_attachment，但维护旧邮件代码仍需读懂这些类。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.mime.MIMEBase
# polyglot-covers: python.email.mime.MIMEBase-content-type-header
# polyglot-covers: python.email.mime.MIMEBase-mime-version-header
# polyglot-covers: python.email.mime.MIMEBase-params
# polyglot-covers: python.email.mime.MIMEMultipart
# polyglot-covers: python.email.mime.MIMEMultipart-subparts
# polyglot-covers: python.email.mime.MIMEMultipart-delayed-boundary
# polyglot-covers: python.email.mime.MIMEMultipart-attach
# polyglot-covers: python.email.mime.compat32-default-policy
# polyglot-covers: python.email.mime.MIMENonMultipart
# polyglot-covers: python.email.mime.nonmultipart-attach-error

from email import policy
from email.errors import MultipartConversionError
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.text import MIMEText

import pytest


def test_mime_base_adds_required_headers_and_content_type_parameters():
    part = MIMEBase("application", "x-example", name="payload.bin")

    assert part.get_content_type() == "application/x-example"
    assert part.get_param("name") == "payload.bin"
    assert part["MIME-Version"] == "1.0"
    assert part.policy is policy.compat32


def test_multipart_keeps_subparts_and_generates_boundary_only_when_flattened():
    first = MIMEText("first")
    second = MIMEText("second", _subtype="html")
    container = MIMEMultipart(_subtype="alternative", _subparts=(first,))

    assert container.get_boundary() is None
    assert container.get_payload() == [first]
    container.attach(second)
    assert container.get_payload(1) is second

    # boundary 为 None 时不是非法状态；序列化器在真正需要 wire format 时才补上稳定值。
    wire = container.as_string()
    assert container.get_boundary() is not None
    assert container.get_boundary() in wire


def test_nonmultipart_rejects_attach_instead_of_silently_corrupting_payload_shape():
    scalar = MIMENonMultipart("text", "plain")
    with pytest.raises(MultipartConversionError):
        scalar.attach(MIMEText("child"))
