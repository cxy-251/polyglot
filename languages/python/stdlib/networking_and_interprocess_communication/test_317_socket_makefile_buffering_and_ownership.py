"""317｜socket.makefile 的 buffering、文本 newline 与共享关闭所有权。

makefile 把 stream socket 包成 file object，参数大体遵循 open。它要求 blocking socket；timeout
期间失败可能让内部 buffer 不一致。关闭 file 不会单独关闭原 socket；反过来 socket.close 后，
只要 makefile wrapper 仍存活，底层 fd 也暂缓关闭，直到所有 wrapper 一起关闭。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.makefile
# polyglot-covers: python.socket.makefile-open-like-mode-buffering
# polyglot-covers: python.socket.makefile-requires-blocking-socket
# polyglot-covers: python.socket.makefile-timeout-buffer-inconsistency-trap
# polyglot-covers: python.socket.makefile-text-encoding
# polyglot-covers: python.socket.makefile-universal-newlines
# polyglot-covers: python.socket.makefile-close-does-not-close-socket-alone
# polyglot-covers: python.socket.socket-close-deferred-by-makefile

import socket


def test_text_makefile_decodes_and_normalizes_newlines():
    left, right = socket.socketpair()
    reader = left.makefile("r", encoding="utf-8", newline=None)
    try:
        right.sendall("第一行\r\n第二行\n".encode())
        right.shutdown(socket.SHUT_WR)
        assert reader.readlines() == ["第一行\n", "第二行\n"]

        reader.close()
        assert left.fileno() >= 0
        left.sendall(b"socket still owns its descriptor")
        assert right.recv(64) == b"socket still owns its descriptor"
    finally:
        reader.close()
        left.close()
        right.close()


def test_open_makefile_keeps_descriptor_alive_after_socket_object_closes():
    left, right = socket.socketpair()
    binary_reader = left.makefile("rb", buffering=0)
    left.close()
    try:
        assert left.fileno() == -1
        right.sendall(b"data")
        assert binary_reader.read(4) == b"data"
    finally:
        binary_reader.close()
        right.close()
