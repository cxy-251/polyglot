"""341｜select.select 的三类就绪集合与 fileno 协议。

select 不传输数据，只报告哪些对象执行下一次 read、write 或异常处理时不会阻塞。返回列表保留
调用者传入的对象，而不是把它们统一替换成整数 fd；这使带 fileno() 的轻量包装对象也能携带
应用状态。timeout=0 是一次非阻塞轮询，不代表等待到事件出现。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.select.select
# polyglot-covers: python.select.read-ready-list
# polyglot-covers: python.select.write-ready-list
# polyglot-covers: python.select.exception-ready-list
# polyglot-covers: python.select.fileno-protocol
# polyglot-covers: python.select.return-original-file-objects
# polyglot-covers: python.select.timeout-zero-poll
# polyglot-covers: python.select.empty-inputs
# polyglot-covers: python.select.PIPE_BUF

import os
import select
import socket


class FileDescriptorView:
    """只暴露 select 所需的最小协议，并额外保存业务标签。"""

    def __init__(self, fd, label):
        self.fd = fd
        self.label = label

    def fileno(self):
        return self.fd


def test_select_reports_original_objects_through_the_fileno_protocol():
    read_fd, write_fd = os.pipe()
    reader = FileDescriptorView(read_fd, "command-pipe")
    try:
        # 尚无数据时，零超时轮询立即返回三个空集合。
        assert select.select([reader], [], [], 0) == ([], [], [])

        os.write(write_fd, b"x")
        readable, writable, exceptional = select.select([reader], [], [reader], 0)
        assert readable == [reader]
        assert readable[0].label == "command-pipe"
        assert writable == []
        assert exceptional == []
        assert os.read(read_fd, 1) == b"x"
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_read_and_write_sets_are_independent_and_preserve_input_order():
    left, right = socket.socketpair()
    try:
        right.sendall(b"ready")
        # socket buffer 尚有空间，因此 left 可同时出现在 read 与 write 返回列表中。
        readable, writable, exceptional = select.select(
            [left, right], [right, left], [left], 0
        )
        assert readable == [left]
        assert writable == [right, left]
        assert exceptional == []
        assert left.recv(5) == b"ready"
    finally:
        left.close()
        right.close()


def test_empty_poll_and_pipe_buf_portability_contract():
    # Unix 允许空输入配合 timeout=0；非零或 None 在不同平台可能出错或永久等待，不能用它 sleep。
    assert select.select([], [], [], 0) == ([], [], [])

    # POSIX 保证向 pipe 一次写入不超过 PIPE_BUF 的数据不会和其他 writer 的写入交错。
    # 它不是 pipe 总容量，也不保证更大的 write 一定被拆开。
    assert select.PIPE_BUF >= 512
