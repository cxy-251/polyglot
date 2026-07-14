"""313｜stream socket 的 send/recv、sendall、peek、half-close 与 EOF。

stream 没有消息边界：recv(bufsize) 最多返回 bufsize，调用者必须循环组帧。send 返回实际写入
数量，可能小于输入；sendall 负责循环但成功只返回 None，失败也无法报告已发送量。SHUT_WR
发送 EOF 同时保留读取方向；对端把 recv 返回 b"" 解释为有序 EOF，而不是一条空消息。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.send
# polyglot-covers: python.socket.send-may-be-partial
# polyglot-covers: python.socket.send-caller-retries-remainder
# polyglot-covers: python.socket.socket.sendall
# polyglot-covers: python.socket.sendall-none-on-success
# polyglot-covers: python.socket.sendall-error-progress-unknown
# polyglot-covers: python.socket.socket.recv
# polyglot-covers: python.socket.recv-up-to-bufsize
# polyglot-covers: python.socket.stream-has-no-message-boundaries
# polyglot-covers: python.socket.MSG_PEEK
# polyglot-covers: python.socket.recv-peek-does-not-consume
# polyglot-covers: python.socket.socket.shutdown
# polyglot-covers: python.socket.SHUT_WR
# polyglot-covers: python.socket.stream-half-close
# polyglot-covers: python.socket.recv-empty-bytes-is-eof
# polyglot-covers: python.socket.socket-has-no-read-write-methods

import socket


def test_sendall_and_recv_require_application_level_framing():
    left, right = socket.socketpair()
    try:
        assert left.sendall(b"abcdef") is None
        assert right.recv(2, socket.MSG_PEEK) == b"ab"
        assert right.recv(2) == b"ab"
        assert right.recv(4) == b"cdef"

        # 小 payload 通常一次 send 完成，但正确代码仍使用返回值切掉已发送前缀。
        payload = memoryview(b"reply")
        while payload:
            sent = right.send(payload)
            payload = payload[sent:]
        assert left.recv(16) == b"reply"
    finally:
        left.close()
        right.close()


def test_shutdown_write_delivers_eof_without_disabling_receive_direction():
    left, right = socket.socketpair()
    try:
        left.sendall(b"last")
        left.shutdown(socket.SHUT_WR)
        assert right.recv(16) == b"last"
        assert right.recv(16) == b""

        right.sendall(b"reverse still works")
        assert left.recv(64) == b"reverse still works"
        assert not hasattr(left, "read")
        assert not hasattr(left, "write")
    finally:
        left.close()
        right.close()
