"""326｜getaddrinfo/getnameinfo 的五元组与 numeric-only 安全用法。

getaddrinfo 返回可直接喂给 socket constructor/connect 的 (family,type,proto,canonname,sockaddr)。
限制 family/type/flags 可避免得到调用者不会处理的地址。AI_NUMERICHOST/AI_NUMERICSERV 禁止
DNS/service lookup；非 numeric 输入抛 gaierror。getnameinfo 用 NI_* 做逆向的纯数字格式化。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.getaddrinfo
# polyglot-covers: python.socket.getaddrinfo-five-tuple
# polyglot-covers: python.socket.getaddrinfo-family-type-narrowing
# polyglot-covers: python.socket.AI_NUMERICHOST
# polyglot-covers: python.socket.AI_NUMERICSERV
# polyglot-covers: python.socket.getaddrinfo-numeric-no-dns
# polyglot-covers: python.socket.getnameinfo
# polyglot-covers: python.socket.NI_NUMERICHOST
# polyglot-covers: python.socket.NI_NUMERICSERV
# polyglot-covers: python.socket.getnameinfo-numeric-no-reverse-dns
# polyglot-covers: python.socket.gaierror
# polyglot-covers: python.socket.error-alias-OSError
# polyglot-covers: python.socket.herror

import socket

import pytest


def test_numeric_getaddrinfo_returns_constructor_ready_five_tuples():
    results = socket.getaddrinfo(
        "127.0.0.1",
        "443",
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        flags=socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
    )
    assert results

    for family, kind, protocol, canonical_name, address in results:
        assert family == socket.AF_INET
        assert kind == socket.SOCK_STREAM
        assert isinstance(protocol, int)
        assert canonical_name == ""
        assert address == ("127.0.0.1", 443)


def test_numeric_getnameinfo_formats_without_reverse_lookup():
    result = socket.getnameinfo(
        ("127.0.0.1", 443),
        socket.NI_NUMERICHOST | socket.NI_NUMERICSERV,
    )
    assert result == ("127.0.0.1", "443")

    with pytest.raises(socket.gaierror):
        socket.getaddrinfo(
            "not-a-numeric-address",
            80,
            flags=socket.AI_NUMERICHOST,
        )


def test_socket_exception_aliases_follow_the_oserror_hierarchy():
    assert socket.error is OSError
    assert issubclass(socket.gaierror, OSError)
    assert issubclass(socket.herror, OSError)
