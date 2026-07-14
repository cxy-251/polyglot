"""321｜sendmsg gather write、recvmsg 四元组与 ancillary buffer sizing。

sendmsg 从多个 bytes-like buffer gather 成一个消息；recvmsg 返回 data、ancdata、msg_flags、
address。CMSG_LEN 不含尾部 padding，CMSG_SPACE 包含可移植控制消息所需 padding；接收 ancillary
data 应优先用后者计算 ancbufsize，否则控制消息可能被截断或丢弃。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.sendmsg
# polyglot-covers: python.socket.sendmsg-gather-buffers
# polyglot-covers: python.socket.sendmsg-return-byte-count
# polyglot-covers: python.socket.socket.recvmsg
# polyglot-covers: python.socket.recvmsg-data-ancdata-flags-address
# polyglot-covers: python.socket.recvmsg-ancillary-buffer-zero-default
# polyglot-covers: python.socket.CMSG_LEN
# polyglot-covers: python.socket.CMSG_SPACE
# polyglot-covers: python.socket.cmsg-space-includes-padding
# polyglot-covers: python.socket.cmsg-space-preferred-portability
# polyglot-covers: python.socket.cmsg-length-range-overflow

import socket

import pytest


def test_sendmsg_gathers_buffers_and_recvmsg_returns_four_fields():
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sent = left.sendmsg([b"head", memoryview(b"-body")])
        data, ancillary, flags, address = right.recvmsg(64)

        assert sent == 9
        assert data == b"head-body"
        assert ancillary == []
        assert flags == 0
        assert address in (None, "")
    finally:
        left.close()
        right.close()


def test_cmsg_space_includes_at_least_the_unpadded_control_length():
    payload_size = 4
    assert socket.CMSG_SPACE(payload_size) >= socket.CMSG_LEN(payload_size)
    assert socket.CMSG_LEN(payload_size) >= payload_size

    with pytest.raises(OverflowError):
        socket.CMSG_SPACE(-1)
