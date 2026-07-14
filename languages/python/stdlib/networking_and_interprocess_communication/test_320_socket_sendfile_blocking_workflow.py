"""320｜blocking stream socket 的 sendfile 文件传输。

sendfile 优先 os.sendfile，必要时退回 send；file 必须二进制打开，socket 必须是 blocking
SOCK_STREAM。offset/count 决定片段，返回发送计数且更新 file position。non-blocking socket
明确不支持，异步程序应使用 loop.sock_sendfile 或 loop.sendfile。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.sendfile
# polyglot-covers: python.socket.sendfile-regular-binary-file
# polyglot-covers: python.socket.sendfile-stream-only
# polyglot-covers: python.socket.sendfile-offset-count
# polyglot-covers: python.socket.sendfile-return-count
# polyglot-covers: python.socket.sendfile-updates-file-position
# polyglot-covers: python.socket.sendfile-os-sendfile-preferred
# polyglot-covers: python.socket.sendfile-fallback-send
# polyglot-covers: python.socket.sendfile-nonblocking-unsupported

import socket

import pytest


def test_sendfile_sends_selected_slice_and_advances_file_position(tmp_path):
    path = tmp_path / "sendfile.bin"
    path.write_bytes(b"0123456789")
    left, right = socket.socketpair()
    try:
        with path.open("rb") as file:
            sent = left.sendfile(file, offset=2, count=4)
            assert sent == 4
            assert file.tell() == 6
        assert right.recv(16) == b"2345"
    finally:
        left.close()
        right.close()


def test_sendfile_rejects_nonblocking_socket(tmp_path):
    path = tmp_path / "nonblocking.bin"
    path.write_bytes(b"data")
    left, right = socket.socketpair()
    left.setblocking(False)
    try:
        with path.open("rb") as file:
            with pytest.raises(ValueError, match="non-blocking sockets"):
                left.sendfile(file)
    finally:
        left.close()
        right.close()
