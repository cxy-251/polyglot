"""353｜set_wakeup_fd 把异步信号桥接到 I/O 事件循环。

收到信号时，运行时向非阻塞 wakeup fd 写入一个值为信号号低 8 位的字节，使 select/selector
立即醒来；Python handler 仍按正常规则在主线程执行。应用必须主动排空 fd，并根据用途决定缓冲区
满时是否警告。set_wakeup_fd 返回旧 fd，因此嵌入式库要保存并恢复它。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.set_wakeup_fd
# polyglot-covers: python.signal.set-wakeup-fd-returns-old-fd
# polyglot-covers: python.signal.set-wakeup-fd-minus-one-disables
# polyglot-covers: python.signal.wakeup-fd-must-be-nonblocking
# polyglot-covers: python.signal.wakeup-fd-writes-signum-byte
# polyglot-covers: python.signal.wakeup-fd-must-be-drained
# polyglot-covers: python.signal.wakeup-fd-warn-on-full-buffer
# polyglot-covers: python.signal.wakeup-fd-save-restore-workflow

import os
import signal

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1"),
    reason="案例使用 Unix 用户自定义信号，避免干扰进程控制信号",
)


def test_signal_writes_one_byte_to_a_nonblocking_wakeup_pipe():
    read_fd, write_fd = os.pipe()
    os.set_blocking(read_fd, False)
    os.set_blocking(write_fd, False)
    handled = []
    previous_handler = signal.getsignal(signal.SIGUSR1)
    previous_wakeup_fd = signal.set_wakeup_fd(-1)
    try:
        signal.signal(signal.SIGUSR1, lambda signum, frame: handled.append(signum))
        assert signal.set_wakeup_fd(write_fd, warn_on_full_buffer=False) == -1

        signal.raise_signal(signal.SIGUSR1)
        assert handled == [signal.SIGUSR1]
        assert os.read(read_fd, 1) == bytes([int(signal.SIGUSR1) & 0xFF])
        with pytest.raises(BlockingIOError):
            os.read(read_fd, 1)

        assert signal.set_wakeup_fd(-1) == write_fd
    finally:
        signal.set_wakeup_fd(previous_wakeup_fd)
        signal.signal(signal.SIGUSR1, previous_handler)
        os.close(read_fd)
        os.close(write_fd)


def test_blocking_descriptor_is_rejected_before_it_can_be_installed():
    read_fd, write_fd = os.pipe()
    previous_wakeup_fd = signal.set_wakeup_fd(-1)
    try:
        assert os.get_blocking(write_fd) is True
        with pytest.raises(ValueError, match="non-blocking"):
            signal.set_wakeup_fd(write_fd, warn_on_full_buffer=True)
    finally:
        signal.set_wakeup_fd(previous_wakeup_fd)
        os.close(read_fd)
        os.close(write_fd)
