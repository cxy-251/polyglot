"""388｜EmailMessage header 是有序、大小写不敏感、允许重复的“类 mapping”。

header 按原始大小写与插入顺序保存，查找不区分大小写；``msg[name]`` 缺失返回 None 而非
KeyError。普通字段赋值是 append，不是 dict 式覆盖；重复字段必须用 get_all。标准 policy 会限制
Subject 等 unique header，更新它们应使用 replace_header 或先删除再添加。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.message.EmailMessage
# polyglot-covers: python.email.header-mapping-case-insensitive
# polyglot-covers: python.email.header-case-preserved
# polyglot-covers: python.email.header-order-preserved
# polyglot-covers: python.email.header-duplicates-allowed
# polyglot-covers: python.email.header-setitem-appends
# polyglot-covers: python.email.header-getitem-missing-none
# polyglot-covers: python.email.header-get-all
# polyglot-covers: python.email.header-delete-all-occurrences
# polyglot-covers: python.email.header-replace-preserves-position-and-case
# polyglot-covers: python.email.header-replace-missing-keyerror
# polyglot-covers: python.email.unique-header-duplicate-valueerror
# polyglot-covers: python.email.header-newline-injection-valueerror

from email.headerregistry import BaseHeader
from email.message import EmailMessage

import pytest


def test_header_mapping_preserves_order_case_and_duplicate_fields():
    message = EmailMessage()
    message["Received"] = "by first.example"
    message["Subject"] = "status"
    message["received"] = "by second.example"

    assert len(message) == 3
    assert message.keys() == ["Received", "Subject", "received"]
    assert "RECEIVED" in message
    assert message["missing"] is None
    assert message.get("missing", "fallback") == "fallback"
    assert [str(value) for value in message.get_all("RECEIVED")] == [
        "by first.example",
        "by second.example",
    ]
    assert all(isinstance(value, BaseHeader) for value in message.values())

    del message["received"]
    assert "Received" not in message
    assert message.keys() == ["Subject"]
    del message["not-present"]  # 与 dict 不同，删除缺失 header 不抛异常。


def test_replace_header_updates_in_place_while_assignment_appends_or_is_limited():
    message = EmailMessage()
    message["X-Trace"] = "old"
    message["Subject"] = "first"
    message["X-Tail"] = "last"

    message.replace_header("x-trace", "new")
    assert message.keys() == ["X-Trace", "Subject", "X-Tail"]
    assert str(message["X-Trace"]) == "new"
    with pytest.raises(KeyError):
        message.replace_header("X-Missing", "value")

    with pytest.raises(ValueError, match="at most 1"):
        message["Subject"] = "second"
    del message["subject"]
    message["subject"] = "second"
    assert message.keys() == ["X-Trace", "X-Tail", "subject"]


def test_default_policy_rejects_crlf_header_injection():
    message = EmailMessage()
    with pytest.raises(ValueError, match="linefeed|carriage return"):
        message["Subject"] = "safe\nBcc: injected@example.com"
