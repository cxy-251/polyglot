"""392｜EmailPolicy 不可变 clone、非交换组合与 transport 预设。

policy 控制 parser factory、header 类型、fold、换行、CTE 与 defect 策略。实例不可变，修改必须
clone；``left + right`` 采用 right 的非默认值，因此不满足交换律。default 内部用 LF，SMTP 使用
RFC 要求的 CRLF，SMTPUTF8 还允许 RFC 6532 UTF-8 header；parser 应始终显式指定 policy。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.policy.Policy
# polyglot-covers: python.email.policy.EmailPolicy
# polyglot-covers: python.email.policy.default
# polyglot-covers: python.email.policy.compat32
# polyglot-covers: python.email.policy.SMTP
# polyglot-covers: python.email.policy.SMTPUTF8
# polyglot-covers: python.email.policy.HTTP
# polyglot-covers: python.email.policy.strict
# polyglot-covers: python.email.policy-immutable
# polyglot-covers: python.email.policy.clone
# polyglot-covers: python.email.policy-addition-noncommutative
# polyglot-covers: python.email.policy.linesep
# polyglot-covers: python.email.policy.max_line_length
# polyglot-covers: python.email.policy.cte_type
# polyglot-covers: python.email.policy.raise_on_defect
# polyglot-covers: python.email.policy.mangle_from
# polyglot-covers: python.email.policy.utf8
# polyglot-covers: python.email.policy.message_factory
# polyglot-covers: python.email.policy.header_factory
# polyglot-covers: python.email.policy.content_manager
# polyglot-covers: python.email.policy.header_max_count
# polyglot-covers: python.email.policy.header_source_parse
# polyglot-covers: python.email.policy.header_store_parse
# polyglot-covers: python.email.policy.header_fetch_parse
# polyglot-covers: python.email.policy.fold
# polyglot-covers: python.email.policy.fold_binary
# polyglot-covers: python.email.policy.verify_generated_headers-3.10.15

from email import policy
from email.contentmanager import raw_data_manager
from email.headerregistry import BaseHeader, HeaderRegistry
from email.message import EmailMessage

import pytest


def test_policy_instances_are_immutable_and_clone_carries_explicit_changes():
    assert EmailMessage().policy is policy.default
    assert policy.default.linesep == "\n"
    assert policy.SMTP.linesep == "\r\n"
    assert policy.SMTPUTF8.utf8 is True
    assert policy.HTTP.max_line_length is None
    assert policy.strict.raise_on_defect is True
    assert policy.compat32.mangle_from_ is True

    customized = policy.default.clone(
        linesep="\r\n",
        max_line_length=60,
        cte_type="7bit",
        raise_on_defect=True,
    )
    assert customized is not policy.default
    assert customized.linesep == "\r\n"
    assert customized.max_line_length == 60
    assert customized.cte_type == "7bit"
    assert customized.raise_on_defect is True
    assert policy.default.max_line_length == 78
    with pytest.raises(AttributeError):
        policy.default.linesep = "\r\n"


def test_policy_addition_uses_right_hand_nondefault_values():
    length_100 = policy.compat32.clone(max_line_length=100)
    length_80 = policy.compat32.clone(max_line_length=80)
    assert (length_100 + length_80).max_line_length == 80
    assert (length_80 + length_100).max_line_length == 100


def test_email_policy_composes_factories_parsing_hooks_and_folding_protocols():
    assert isinstance(policy.default.message_factory(), EmailMessage)
    assert isinstance(policy.default.header_factory, HeaderRegistry)
    assert policy.default.content_manager is raw_data_manager
    assert policy.default.header_max_count("Subject") == 1
    assert policy.default.header_max_count("X-Repeatable") is None

    source_name, source_value = policy.default.header_source_parse(
        ["Subject: first line\n", "\tcontinued\n"]
    )
    stored_name, stored_value = policy.default.header_store_parse("Subject", "stored")
    fetched_value = policy.default.header_fetch_parse(source_name, source_value)
    assert source_name == stored_name == "Subject"
    assert isinstance(stored_value, BaseHeader)
    assert isinstance(fetched_value, BaseHeader)
    assert "first line" in str(fetched_value)
    assert "continued" in str(fetched_value)
    assert policy.default.fold(stored_name, stored_value) == "Subject: stored\n"
    assert policy.SMTP.fold_binary(stored_name, stored_value).endswith(b"\r\n")

    # 3.10.15 安全修复新增该开关；低于该补丁版本没有此属性。
    if hasattr(policy.default, "verify_generated_headers"):
        assert policy.default.verify_generated_headers is True
