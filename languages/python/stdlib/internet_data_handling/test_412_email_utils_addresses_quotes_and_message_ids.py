"""412｜email.utils 的 Message-ID、地址拆装与引号转义。

make_msgid 在显式 domain 下仍为每次调用生成唯一值。quote/unquote 只处理邮件语法引号，不是
任意转义器。parseaddr/getaddresses 是 compat32 字符串解析器；3.10.15 起默认 strict=True，
会拒绝畸形输入。结构化 headerregistry.Address 是新代码更可靠的选择。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.utils.make_msgid
# polyglot-covers: python.email.utils.make-msgid-domain
# polyglot-covers: python.email.utils.make-msgid-idstring
# polyglot-covers: python.email.utils.make-msgid-uniqueness
# polyglot-covers: python.email.utils.quote
# polyglot-covers: python.email.utils.unquote
# polyglot-covers: python.email.utils.parseaddr
# polyglot-covers: python.email.utils.parseaddr-strict-3.10.15
# polyglot-covers: python.email.utils.formataddr
# polyglot-covers: python.email.utils.formataddr-international-name
# polyglot-covers: python.email.utils.getaddresses

from email.header import decode_header, make_header
from email.utils import formataddr, getaddresses, make_msgid, parseaddr, quote, unquote
import sys


def test_message_ids_use_requested_components_but_remain_unique():
    first = make_msgid(idstring="worker", domain="example.test")
    second = make_msgid(idstring="worker", domain="example.test")

    assert first.startswith("<") and first.endswith(".worker@example.test>")
    assert second.startswith("<") and second.endswith(".worker@example.test>")
    assert first != second


def test_quote_unquote_and_address_formatting_are_email_specific_operations():
    escaped = quote('path\\name "label"')
    assert escaped == 'path\\\\name \\"label\\"'
    assert unquote(f'"{escaped}"') == 'path\\name "label"'
    assert unquote("<user@example.test>") == "user@example.test"

    rendered = formataddr(("张三", "zhang@example.test"), charset="utf-8")
    encoded_name, address = parseaddr(rendered)
    assert address == "zhang@example.test"
    assert str(make_header(decode_header(encoded_name))) == "张三"


def test_parseaddr_and_getaddresses_handle_single_and_multiple_header_values():
    assert parseaddr("Alice <alice@example.test>") == (
        "Alice",
        "alice@example.test",
    )
    assert getaddresses(
        ["Alice <alice@example.test>, bob@example.test", "Carol <c@example.test>"]
    ) == [
        ("Alice", "alice@example.test"),
        ("", "bob@example.test"),
        ("Carol", "c@example.test"),
    ]

    if sys.version_info >= (3, 10, 15):
        malformed = "alice@example.test <bob@example.test>"
        assert parseaddr(malformed) == ("", "")
        assert parseaddr(malformed, strict=False) != ("", "")
