"""316｜Unix stream server 的 socket-bind-listen-accept 与 client connect/connect_ex。

监听 socket 只负责 accept；数据必须在 accept 返回的新 conn 上收发。connect_ex 把 C connect
的 errno 改为返回值，成功为 0，适合非阻塞状态机；名称解析等前置错误仍可能抛异常。accept
产生的新 socket 默认不可继承，且在默认 timeout 为 None 时由 blocking listener 接受为 blocking。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.server-socket-bind-listen-accept-sequence
# polyglot-covers: python.socket.socket.listen
# polyglot-covers: python.socket.listen-default-backlog
# polyglot-covers: python.socket.socket.connect
# polyglot-covers: python.socket.socket.connect_ex
# polyglot-covers: python.socket.connect-ex-zero-success
# polyglot-covers: python.socket.socket.accept
# polyglot-covers: python.socket.accept-connection-address-pair
# polyglot-covers: python.socket.accept-data-on-connection-not-listener
# polyglot-covers: python.socket.accepted-socket-non-inheritable
# polyglot-covers: python.socket.accepted-socket-blocking-normalization
# polyglot-covers: python.socket.accepted-socket-inherits-global-default-timeout
# polyglot-covers: python.socket.socket.getsockname
# polyglot-covers: python.socket.socket.getpeername

import socket


def test_listener_accepts_a_distinct_connected_socket_and_echoes(tmp_path):
    path = tmp_path / "server.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    accepted = None
    try:
        listener.bind(str(path))
        listener.listen()
        assert listener.getsockname() == str(path)

        assert client.connect_ex(str(path)) == 0
        accepted, peer_address = listener.accept()
        assert peer_address == ""
        assert accepted is not listener
        assert accepted.get_inheritable() is False
        assert accepted.getblocking() is True
        assert accepted.getpeername() == ""

        client.sendall(b"hello")
        assert accepted.recv(64) == b"hello"
        accepted.sendall(b"HELLO")
        assert client.recv(64) == b"HELLO"
    finally:
        if accepted is not None:
            accepted.close()
        client.close()
        listener.close()


def test_connect_and_accept_use_global_default_timeout_for_new_sockets(tmp_path):
    previous = socket.getdefaulttimeout()
    listener = None
    client = None
    accepted = None
    try:
        socket.setdefaulttimeout(0.5)
        path = tmp_path / "timeout-server.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path))
        listener.listen()

        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        assert client.connect(str(path)) is None
        accepted, _ = listener.accept()
        assert client.gettimeout() == 0.5
        assert accepted.gettimeout() == 0.5
    finally:
        socket.setdefaulttimeout(previous)
        if accepted is not None:
            accepted.close()
        if client is not None:
            client.close()
        if listener is not None:
            listener.close()
