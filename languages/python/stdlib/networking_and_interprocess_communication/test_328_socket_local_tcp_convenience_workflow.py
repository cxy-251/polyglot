"""328｜create_server/create_connection 的本地 TCP convenience workflow。

create_server 完成 socket/bind/listen，create_connection 会依次尝试 getaddrinfo 结果，并可在连接前
设置 timeout/source_address。案例只连 127.0.0.1 的随机端口，数据不会离开当前容器网络空间。
server 返回的监听 socket 与 accept 返回的连接 socket 仍需分别关闭。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.create_server
# polyglot-covers: python.socket.create-server-bind-listen-convenience
# polyglot-covers: python.socket.create-server-random-port-zero
# polyglot-covers: python.socket.create-server-posix-reuseaddr
# polyglot-covers: python.socket.create_connection
# polyglot-covers: python.socket.create-connection-address-attempts
# polyglot-covers: python.socket.create-connection-timeout-before-connect
# polyglot-covers: python.socket.create-connection-source-address
# polyglot-covers: python.socket.local-loopback-no-external-network
# polyglot-covers: python.socket.dualstack-ipv6-requires-af-inet6

import socket

import pytest


def test_convenience_server_and_client_exchange_over_container_loopback():
    server = socket.create_server(
        ("127.0.0.1", 0),
        family=socket.AF_INET,
        backlog=1,
    )
    client = None
    accepted = None
    try:
        address = server.getsockname()
        assert address[0] == "127.0.0.1"
        assert address[1] > 0
        assert server.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 1

        client = socket.create_connection(
            address,
            timeout=1.0,
            source_address=("127.0.0.1", 0),
        )
        accepted, _ = server.accept()
        assert client.gettimeout() == 1.0
        assert client.getsockname()[0] == "127.0.0.1"

        client.sendall(b"local")
        assert accepted.recv(16) == b"local"
    finally:
        if accepted is not None:
            accepted.close()
        if client is not None:
            client.close()
        server.close()


def test_dualstack_flag_is_invalid_for_ipv4_server_family():
    with pytest.raises(ValueError):
        socket.create_server(
            ("127.0.0.1", 0),
            family=socket.AF_INET,
            dualstack_ipv6=True,
        )
