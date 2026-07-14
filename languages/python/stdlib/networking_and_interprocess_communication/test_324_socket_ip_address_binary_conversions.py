"""324｜IPv4/IPv6 文本地址与 network binary 表示转换。

inet_aton/ntoa 是 IPv4-only 传统接口，aton 还可能按 libc 接受缩写形式，跨平台代码不要依赖。
inet_pton/ntop 显式 family，适合双栈；IPv6 文本可能有多种等价写法，ntop 返回规范压缩形式。
这只是纯转换，不做 DNS 查询，也不验证地址是否可路由。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.inet_aton
# polyglot-covers: python.socket.inet_aton-ipv4-only
# polyglot-covers: python.socket.inet_aton-abbreviated-platform-dependent
# polyglot-covers: python.socket.inet_ntoa
# polyglot-covers: python.socket.inet_ntoa-four-byte-input
# polyglot-covers: python.socket.inet_pton
# polyglot-covers: python.socket.inet_pton-explicit-family
# polyglot-covers: python.socket.inet_pton-ipv4-ipv6
# polyglot-covers: python.socket.inet_ntop
# polyglot-covers: python.socket.inet_ntop-family-specific-length
# polyglot-covers: python.socket.ip-conversion-no-dns

import socket

import pytest


def test_legacy_ipv4_conversion_round_trips_exactly_four_bytes():
    packed = socket.inet_aton("192.0.2.1")
    assert packed == b"\xc0\x00\x02\x01"
    assert socket.inet_ntoa(memoryview(packed)) == "192.0.2.1"

    with pytest.raises(OSError):
        socket.inet_ntoa(b"too short")


def test_family_explicit_conversion_supports_ipv4_and_ipv6():
    ipv4 = socket.inet_pton(socket.AF_INET, "198.51.100.7")
    ipv6 = socket.inet_pton(socket.AF_INET6, "2001:db8:0:0::1")

    assert len(ipv4) == 4
    assert len(ipv6) == 16
    assert socket.inet_ntop(socket.AF_INET, ipv4) == "198.51.100.7"
    assert socket.inet_ntop(socket.AF_INET6, ipv6) == "2001:db8::1"

    with pytest.raises(OSError):
        socket.inet_pton(socket.AF_INET, "2001:db8::1")
    with pytest.raises(ValueError):
        socket.inet_ntop(socket.AF_INET6, b"four")
