"""314｜recv_into 把数据直接写入 caller-owned writable buffer。

recv 创建新 bytes；recv_into 改写 bytearray/memoryview 并返回写入计数，适合复用缓冲区。nbytes
省略或为 0 时最多填满传入 view；只应读取计数覆盖的区域，未写入部分保留旧内容。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.recv_into
# polyglot-covers: python.socket.recv-into-writable-buffer
# polyglot-covers: python.socket.recv-into-memoryview-slice
# polyglot-covers: python.socket.recv-into-return-count
# polyglot-covers: python.socket.recv-into-zero-means-buffer-size
# polyglot-covers: python.socket.recv-into-unwritten-region-preserved

import socket


def test_recv_into_writes_only_the_selected_memoryview_slice():
    left, right = socket.socketpair()
    buffer = bytearray(b"..........")
    try:
        left.sendall(b"data")
        count = right.recv_into(memoryview(buffer)[3:7])

        assert count == 4
        assert buffer == bytearray(b"...data...")
    finally:
        left.close()
        right.close()


def test_zero_nbytes_uses_the_destination_buffer_length():
    left, right = socket.socketpair()
    buffer = bytearray(b"------")
    try:
        left.sendall(b"abc")
        left.shutdown(socket.SHUT_WR)
        count = right.recv_into(buffer, 0)

        assert count == 3
        assert buffer == bytearray(b"abc---")
    finally:
        left.close()
        right.close()
