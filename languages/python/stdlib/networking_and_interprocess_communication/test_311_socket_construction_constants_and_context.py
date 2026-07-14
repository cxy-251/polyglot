"""311｜socket 构造参数、IntEnum 常量、原子 flags 与资源上下文。

family/type/proto 决定地址表示和传输语义；AF_* 与 SOCK_* 是 IntEnum，仍可传给 C 风格 API。
新 socket 默认 blocking、不可继承。Linux 可把 SOCK_NONBLOCK/SOCK_CLOEXEC 原子并入 type，
但 Python 的 socket.type 会清除这两个 flag，只保留基本 kind，不能用它判断当前 blocking 状态。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket
# polyglot-covers: python.socket.socket-family-type-proto
# polyglot-covers: python.socket.socket.family
# polyglot-covers: python.socket.socket.type
# polyglot-covers: python.socket.socket.proto
# polyglot-covers: python.socket.AddressFamily
# polyglot-covers: python.socket.SocketKind
# polyglot-covers: python.socket.SocketType
# polyglot-covers: python.socket.AF_UNIX
# polyglot-covers: python.socket.SOCK_STREAM
# polyglot-covers: python.socket.SOCK_DGRAM
# polyglot-covers: python.socket.SOCK_NONBLOCK
# polyglot-covers: python.socket.SOCK_CLOEXEC
# polyglot-covers: python.socket.atomic-socket-flags-cleared-from-type
# polyglot-covers: python.socket.new-socket-blocking-default
# polyglot-covers: python.socket.new-socket-non-inheritable
# polyglot-covers: python.socket.socket-context-manager-close
# polyglot-covers: python.socket.socketpair
# polyglot-covers: python.socket.socketpair-connected

import enum
import socket


def test_constructor_attributes_are_int_enums_and_context_manager_closes():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        assert isinstance(sock.family, socket.AddressFamily)
        assert isinstance(sock.family, enum.IntEnum)
        assert isinstance(sock.type, socket.SocketKind)
        assert sock.family == socket.AF_UNIX
        assert sock.type == socket.SOCK_STREAM
        assert sock.proto == 0
        assert isinstance(sock, socket.SocketType)
        assert sock.getblocking() is True
        assert sock.get_inheritable() is False
        descriptor = sock.fileno()
        assert descriptor >= 0

    assert sock.fileno() == -1


def test_socketpair_returns_connected_non_inheritable_endpoints():
    left, right = socket.socketpair()
    try:
        assert left.family == right.family
        assert left.type == right.type == socket.SOCK_STREAM
        assert left.get_inheritable() is False
        assert right.get_inheritable() is False
        assert left.send(b"x") == 1
        assert right.recv(1) == b"x"
    finally:
        left.close()
        right.close()


def test_atomic_nonblocking_flag_changes_mode_but_not_type_attribute():
    kind = socket.SOCK_STREAM | socket.SOCK_NONBLOCK | socket.SOCK_CLOEXEC
    sock = socket.socket(socket.AF_UNIX, kind)
    try:
        assert sock.type == socket.SOCK_STREAM
        assert sock.getblocking() is False
        assert sock.get_inheritable() is False
    finally:
        sock.close()
