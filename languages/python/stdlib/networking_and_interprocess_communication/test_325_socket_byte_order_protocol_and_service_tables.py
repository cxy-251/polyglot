"""325｜host/network 字节序与本机 protocol/service database。

网络字节序是 big-endian；hton* 从 host 转 network，ntoh* 反向，round-trip 与主机端序无关。
getprotobyname/getservbyname/getservbyport 查询 libc 数据库，不建立连接。Python 3.10 对 16-bit
htons/ntohs 新增明确范围检查，越过 unsigned short 不再静默截断。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.htons
# polyglot-covers: python.socket.ntohs
# polyglot-covers: python.socket.htonl
# polyglot-covers: python.socket.ntohl
# polyglot-covers: python.socket.host-network-byte-order-roundtrip
# polyglot-covers: python.socket.unsigned-16-byte-order-overflow-3.10
# polyglot-covers: python.socket.getprotobyname
# polyglot-covers: python.socket.getservbyname
# polyglot-covers: python.socket.getservbyport
# polyglot-covers: python.socket.protocol-service-tables-no-connection

import socket

import pytest


def test_host_and_network_byte_order_functions_are_inverse_pairs():
    short_value = 0x1234
    long_value = 0x12345678
    assert socket.ntohs(socket.htons(short_value)) == short_value
    assert socket.htons(socket.ntohs(short_value)) == short_value
    assert socket.ntohl(socket.htonl(long_value)) == long_value
    assert socket.htonl(socket.ntohl(long_value)) == long_value

    with pytest.raises(OverflowError):
        socket.htons(1 << 16)
    with pytest.raises(OverflowError):
        socket.ntohs(1 << 16)


def test_protocol_and_service_names_map_to_standard_integer_constants():
    assert socket.getprotobyname("tcp") == socket.IPPROTO_TCP
    assert socket.getprotobyname("udp") == socket.IPPROTO_UDP
    assert socket.getservbyname("http", "tcp") == 80
    assert socket.getservbyport(80, "tcp") == "http"
