"""327｜hostname/FQDN 与 network interface index 的环境读取。

gethostname 返回本机短名但不保证 FQDN；getfqdn 会按 reverse lookup/alias 选择带点名称，仍可能
退回原输入。if_nameindex 列出 (index,name)，另外两个函数可双向转换。接口集合属于运行环境，
案例只验证内部一致性，不把 Docker 中的具体名称或 index 写死。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.gethostname
# polyglot-covers: python.socket.gethostname-not-necessarily-fqdn
# polyglot-covers: python.socket.getfqdn
# polyglot-covers: python.socket.getfqdn-fallback
# polyglot-covers: python.socket.if_nameindex
# polyglot-covers: python.socket.if_nametoindex
# polyglot-covers: python.socket.if_indextoname
# polyglot-covers: python.socket.interface-index-name-roundtrip
# polyglot-covers: python.socket.interface-list-environment-dependent
# polyglot-covers: python.socket.has_ipv6
# polyglot-covers: python.socket.has_dualstack_ipv6

import socket

import pytest


def test_hostname_is_a_nonempty_local_machine_label():
    hostname = socket.gethostname()
    assert isinstance(hostname, str) and hostname


def test_getfqdn_selects_a_dotted_primary_name_or_alias_without_network(monkeypatch):
    monkeypatch.setattr(
        socket,
        "gethostbyaddr",
        lambda _: ("short", ["alias", "host.example.test"], ["192.0.2.1"]),
    )
    assert socket.getfqdn("input") == "host.example.test"

    def unavailable(_):
        raise OSError("no resolver data")

    monkeypatch.setattr(socket, "gethostbyaddr", unavailable)
    assert socket.getfqdn("unchanged.example") == "unchanged.example"


def test_each_reported_interface_round_trips_between_name_and_index():
    interfaces = socket.if_nameindex()
    assert interfaces
    for index, name in interfaces:
        assert isinstance(index, int) and index > 0
        assert isinstance(name, str) and name
        assert socket.if_nametoindex(name) == index
        assert socket.if_indextoname(index) == name

    with pytest.raises(OSError):
        socket.if_nametoindex("polyglot-interface-does-not-exist")


def test_ip_capability_probes_return_booleans_not_configuration_guarantees():
    assert isinstance(socket.has_ipv6, bool)
    assert isinstance(socket.has_dualstack_ipv6(), bool)
