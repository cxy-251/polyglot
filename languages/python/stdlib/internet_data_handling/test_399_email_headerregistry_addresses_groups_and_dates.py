"""399｜headerregistry 的 Address/Group、结构化 address header 与 DateHeader。

policy.default 返回 str 子类 header，不必手拆引号、逗号和 encoded-word。Address 保存无引号的
display_name/username/domain，并生成合法 addr_spec；Group 保留收件人组边界，而 ``addresses``
提供扁平视图。Date header 接受 aware datetime 并能无损取回时区信息。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.headerregistry.BaseHeader
# polyglot-covers: python.email.headerregistry.Address
# polyglot-covers: python.email.headerregistry.Address.display_name
# polyglot-covers: python.email.headerregistry.Address.username
# polyglot-covers: python.email.headerregistry.Address.domain
# polyglot-covers: python.email.headerregistry.Address.addr_spec
# polyglot-covers: python.email.headerregistry.Group
# polyglot-covers: python.email.headerregistry.AddressHeader.addresses
# polyglot-covers: python.email.headerregistry.AddressHeader.groups
# polyglot-covers: python.email.headerregistry.SingleAddressHeader.address
# polyglot-covers: python.email.headerregistry.DateHeader.datetime
# polyglot-covers: python.email.structured-header-defects
# polyglot-covers: python.email.invalid-addr-spec-valueerror
# polyglot-covers: python.email.headerregistry.Address.__str__
# polyglot-covers: python.email.headerregistry.Group.display_name
# polyglot-covers: python.email.headerregistry.Group.addresses
# polyglot-covers: python.email.headerregistry.Group.__str__

from datetime import datetime, timedelta, timezone
from email.headerregistry import Address, BaseHeader, Group
from email.message import EmailMessage

import pytest


def test_address_headers_preserve_groups_and_offer_a_flat_address_view():
    sender = Address(display_name="发送者", username="sender", domain="example.test")
    direct = Address(addr_spec='"quoted local"@example.test')
    team_member = Address(display_name="Member", username="member", domain="example.test")
    team = Group(display_name="Team", addresses=(team_member,))

    message = EmailMessage()
    message["From"] = sender
    message["To"] = (direct, team)
    from_header = message["From"]
    to_header = message["To"]

    assert isinstance(from_header, BaseHeader)
    assert from_header.address == sender
    assert from_header.address.display_name == "发送者"
    assert from_header.address.username == "sender"
    assert from_header.address.domain == "example.test"
    assert direct.addr_spec == '"quoted local"@example.test'
    assert str(team_member) == "Member <member@example.test>"
    assert team.display_name == "Team"
    assert team.addresses == (team_member,)
    assert str(team) == "Team: Member <member@example.test>;"
    assert to_header.addresses == (direct, team_member)
    # 解析器会构造新的 Group 值对象；比起依赖对象相等的实现细节，直接检查结构更能说明协议。
    assert to_header.groups[1].display_name == "Team"
    assert to_header.groups[1].addresses == (team_member,)
    assert to_header.defects == ()


def test_date_header_keeps_an_aware_datetime_value():
    instant = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=8)))
    message = EmailMessage()
    message["Date"] = instant
    assert message["Date"].datetime == instant
    assert "+0800" in str(message["Date"])


def test_address_rejects_an_addr_spec_that_cannot_be_fully_parsed():
    with pytest.raises(ValueError):
        Address(addr_spec="bad@@example.test")
