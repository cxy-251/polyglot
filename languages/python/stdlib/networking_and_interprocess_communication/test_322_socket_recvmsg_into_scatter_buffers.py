"""322｜recvmsg_into 把普通数据 scatter 到多个 writable buffer。

它返回 (nbytes, ancdata, msg_flags, address)，并按 buffers 迭代顺序依次填充；memoryview slice
只暴露选中区域，外侧内容保留。系统对 iovec 数量有 SC_IOV_MAX 限制，不能把任意长列表直接
交给底层。只读取 nbytes 覆盖的前缀，最后一个 buffer 的其余空间仍是旧值。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.recvmsg_into
# polyglot-covers: python.socket.recvmsg-into-scatter-buffers
# polyglot-covers: python.socket.recvmsg-into-memoryview-slice
# polyglot-covers: python.socket.recvmsg-into-return-four-tuple
# polyglot-covers: python.socket.recvmsg-into-nbytes-valid-prefix
# polyglot-covers: python.socket.recvmsg-into-iovec-platform-limit

import socket


def test_recvmsg_into_scatter_writes_across_selected_buffers():
    left, right = socket.socketpair()
    first = bytearray(b"----")
    middle = bytearray(b"0123456789")
    last = bytearray(b"--------------")
    try:
        left.sendall(b"Mary had a little lamb")
        nbytes, ancillary, flags, address = right.recvmsg_into(
            [first, memoryview(middle)[2:9], last]
        )

        assert nbytes == 22
        assert ancillary == []
        assert flags == 0
        assert address in (None, "")
        assert first == bytearray(b"Mary")
        assert middle == bytearray(b"01 had a 9")
        assert last == bytearray(b"little lamb---")
    finally:
        left.close()
        right.close()
