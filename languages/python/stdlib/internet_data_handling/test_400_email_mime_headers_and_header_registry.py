"""400｜结构化 MIME header 与 HeaderRegistry 类型映射扩展。

Content-Type/Disposition/Transfer-Encoding/MIME-Version 在现代 policy 下具有专门属性，不应靠
split(';') 解析带引号参数。HeaderRegistry 按字段名选择 mixin；未知字段使用 UnstructuredHeader，
map_to_type 可为私有字段注册语义类。Unique mixin 的 max_count=1 会参与程序化赋值校验。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.headerregistry.ContentTypeHeader
# polyglot-covers: python.email.headerregistry.ContentDispositionHeader
# polyglot-covers: python.email.headerregistry.ContentTransferEncodingHeader
# polyglot-covers: python.email.headerregistry.MIMEVersionHeader
# polyglot-covers: python.email.mime-header-params
# polyglot-covers: python.email.headerregistry.HeaderRegistry
# polyglot-covers: python.email.headerregistry.HeaderRegistry.__getitem__
# polyglot-covers: python.email.headerregistry.HeaderRegistry.__call__
# polyglot-covers: python.email.headerregistry.HeaderRegistry.map_to_type
# polyglot-covers: python.email.headerregistry.UnstructuredHeader
# polyglot-covers: python.email.headerregistry.UniqueUnstructuredHeader
# polyglot-covers: python.email.headerregistry.header-max-count
# polyglot-covers: python.email.headerregistry.BaseHeader.name
# polyglot-covers: python.email.headerregistry.BaseHeader.defects
# polyglot-covers: python.email.headerregistry.BaseHeader.fold
# polyglot-covers: python.email.headerregistry.MIMEVersionHeader.major
# polyglot-covers: python.email.headerregistry.MIMEVersionHeader.minor

from email import policy
from email.headerregistry import (
    BaseHeader,
    HeaderRegistry,
    UniqueUnstructuredHeader,
)
from email.message import EmailMessage


def test_mime_headers_expose_normalized_values_and_parameter_mappings():
    message = EmailMessage()
    message["Content-Type"] = "Text/Plain; Charset=UTF-8; format=flowed"
    message["Content-Disposition"] = 'attachment; filename="report.txt"'
    message["Content-Transfer-Encoding"] = "BASE64"
    message["MIME-Version"] = "1.0"

    content_type = message["Content-Type"]
    assert content_type.content_type == "text/plain"
    assert content_type.maintype == "text"
    assert content_type.subtype == "plain"
    assert content_type.params["charset"].lower() == "utf-8"
    assert content_type.params["format"] == "flowed"
    assert message["Content-Disposition"].content_disposition == "attachment"
    assert message["Content-Disposition"].params["filename"] == "report.txt"
    assert message["Content-Transfer-Encoding"].cte == "base64"
    assert message["MIME-Version"].version == "1.0"
    assert message["MIME-Version"].major == 1
    assert message["MIME-Version"].minor == 0


def test_header_registry_selects_default_and_custom_unique_header_mixins():
    registry = HeaderRegistry()
    subject_class = registry["Subject"]
    assert subject_class.max_count == 1

    ordinary = registry("X-Free", "value")
    assert isinstance(ordinary, BaseHeader)
    assert ordinary.name == "X-Free"
    assert ordinary.max_count is None
    assert ordinary.defects == ()
    assert ordinary.fold(policy=policy.default) == "X-Free: value\n"

    registry.map_to_type("X-Once", UniqueUnstructuredHeader)
    unique = registry("X-Once", "one")
    assert isinstance(unique, BaseHeader)
    assert unique.name == "X-Once"
    assert unique.max_count == 1
