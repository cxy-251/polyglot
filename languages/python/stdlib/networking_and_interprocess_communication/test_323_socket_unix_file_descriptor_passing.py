"""323｜AF_UNIX SCM_RIGHTS 文件描述符传递。

send_fds/recv_fds 用 ancillary data 在本机进程间传 descriptor；接收方得到新的 fd number，但它
引用同一 open file description，因此 file offset 也共享。收到的 fd 必须逐个显式 close，否则
会泄漏资源。maxfds 限制接收数量；普通 message bytes 与 fd 列表一起返回。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.send_fds
# polyglot-covers: python.socket.recv_fds
# polyglot-covers: python.socket.SCM_RIGHTS
# polyglot-covers: python.socket.file-descriptor-passing-af-unix
# polyglot-covers: python.socket.recv-fds-message-fds-flags-address
# polyglot-covers: python.socket.received-fd-new-number
# polyglot-covers: python.socket.received-fd-shares-open-file-description
# polyglot-covers: python.socket.received-fd-must-be-closed
# polyglot-covers: python.socket.recv-fds-maxfds

import os
import socket


def test_send_fds_transfers_a_readable_descriptor_and_shared_offset(tmp_path):
    path = tmp_path / "shared.txt"
    path.write_bytes(b"abcdef")
    original_fd = os.open(path, os.O_RDONLY)
    left, right = socket.socketpair()
    received_fds = []
    try:
        assert socket.send_fds(left, [b"file"], [original_fd]) == 4
        message, received_fds, flags, address = socket.recv_fds(right, 64, 1)

        assert message == b"file"
        assert len(received_fds) == 1
        assert received_fds[0] != original_fd
        assert flags == 0
        assert address in (None, "")

        assert os.read(received_fds[0], 3) == b"abc"
        # SCM_RIGHTS 复制 fd，但共享 open file description，所以原 fd 的 offset 也前进。
        assert os.read(original_fd, 3) == b"def"
    finally:
        for descriptor in received_fds:
            os.close(descriptor)
        os.close(original_fd)
        left.close()
        right.close()
