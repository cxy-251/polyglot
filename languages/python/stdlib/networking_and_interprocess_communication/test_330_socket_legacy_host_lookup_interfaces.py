"""330｜legacy host lookup 与 IPv4-only 限制。

gethostbyname 只返回一个 IPv4 string；gethostbyname_ex 返回 primary、aliases、IPv4 list；
gethostbyaddr 可反查 IPv4/IPv6。新代码通常选 getaddrinfo，因为它保留多个 family/type 结果。
案例只查询 numeric loopback；容器的 localhost 来自本机 resolver database，不访问外部服务。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.gethostbyname
# polyglot-covers: python.socket.gethostbyname-ipv4-only
# polyglot-covers: python.socket.gethostbyname-single-address
# polyglot-covers: python.socket.gethostbyname_ex
# polyglot-covers: python.socket.gethostbyname-ex-primary-aliases-addresses
# polyglot-covers: python.socket.gethostbyaddr
# polyglot-covers: python.socket.gethostbyaddr-ipv4-ipv6
# polyglot-covers: python.socket.getaddrinfo-preferred-for-dual-stack

import socket


def test_numeric_ipv4_lookup_avoids_dns_and_exposes_legacy_shapes():
    assert socket.gethostbyname("127.0.0.1") == "127.0.0.1"

    primary, aliases, addresses = socket.gethostbyname_ex("127.0.0.1")
    assert isinstance(primary, str) and primary
    assert isinstance(aliases, list)
    assert "127.0.0.1" in addresses


def test_loopback_reverse_lookup_returns_primary_alias_and_address_lists():
    primary, aliases, addresses = socket.gethostbyaddr("127.0.0.1")
    assert isinstance(primary, str) and primary
    assert isinstance(aliases, list)
    assert "127.0.0.1" in addresses
