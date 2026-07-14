"""318｜socket fd 的 dup、fromfd、detach、fileno= 与显式 close 所有权。

dup/fromfd 复制 descriptor，两个 wrapper 可独立 close；detach 则把同一个 descriptor 的所有权
移出原对象，原 socket 立即进入 closed 状态。socket.socket(fileno=fd) 接管同一 fd，不再复制；
若仍由其他代码 close 会产生 double-close 风险。socket.close(fd) 是跨平台关闭 socket fd 的入口。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.fileno
# polyglot-covers: python.socket.socket.dup
# polyglot-covers: python.socket.dup-new-non-inheritable-descriptor
# polyglot-covers: python.socket.fromfd
# polyglot-covers: python.socket.fromfd-duplicates-descriptor
# polyglot-covers: python.socket.socket.detach
# polyglot-covers: python.socket.detach-original-wrapper-closed
# polyglot-covers: python.socket.socket-fileno-constructor
# polyglot-covers: python.socket.fileno-constructor-same-descriptor-ownership
# polyglot-covers: python.socket.fileno-constructor-auto-detect
# polyglot-covers: python.socket.close-fd
# polyglot-covers: python.socket.socket.set_inheritable
# polyglot-covers: python.socket.socket.get_inheritable

import os
import socket

import pytest


def test_dup_and_fromfd_create_independently_closable_descriptors():
    left, right = socket.socketpair()
    duplicate = left.dup()
    from_fd = socket.fromfd(left.fileno(), left.family, left.type, left.proto)
    original_fd = left.fileno()
    try:
        assert duplicate.fileno() != original_fd
        assert from_fd.fileno() not in (original_fd, duplicate.fileno())
        assert duplicate.get_inheritable() is False
        assert from_fd.get_inheritable() is False

        left.close()
        duplicate.sendall(b"dup")
        assert right.recv(3) == b"dup"
        from_fd.sendall(b"fromfd")
        assert right.recv(6) == b"fromfd"
    finally:
        left.close()
        duplicate.close()
        from_fd.close()
        right.close()


def test_detach_and_fileno_constructor_transfer_the_same_descriptor():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    descriptor = sock.detach()
    assert sock.fileno() == -1

    adopted = socket.socket(fileno=descriptor)
    try:
        assert adopted.fileno() == descriptor
        assert adopted.family == socket.AF_UNIX
        assert adopted.type == socket.SOCK_STREAM
        adopted.set_inheritable(True)
        assert adopted.get_inheritable() is True
        adopted.set_inheritable(False)
        assert adopted.get_inheritable() is False
    finally:
        adopted.close()

    with pytest.raises(OSError):
        os.fstat(descriptor)


def test_module_close_releases_a_detached_socket_descriptor():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    descriptor = sock.detach()
    socket.close(descriptor)

    with pytest.raises(OSError):
        os.fstat(descriptor)
