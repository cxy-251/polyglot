"""356｜Python 的 SIGPIPE 策略与 BrokenPipeError。

Python 默认忽略 SIGPIPE，让向无 reader 的 pipe/socket 写入以 BrokenPipeError 报告，调用者因此有
机会清理资源并决定退出码。不能为了消除异常把 SIGPIPE 改成 SIG_DFL：任何断开的网络连接都可能
直接终止整个进程。本例显式安装 SIG_IGN，避免依赖测试进程启动时的外部配置。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.SIGPIPE
# polyglot-covers: python.signal.python-ignores-sigpipe-policy
# polyglot-covers: python.signal.broken-pipe-error-instead-of-process-exit
# polyglot-covers: python.signal.sigpipe-default-action-trap

import os
import signal

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGPIPE"),
    reason="SIGPIPE 是 POSIX 信号",
)


def test_ignored_sigpipe_turns_a_write_to_a_closed_pipe_into_an_exception():
    read_fd, write_fd = os.pipe()
    previous = signal.getsignal(signal.SIGPIPE)
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        os.close(read_fd)
        read_fd = -1
        with pytest.raises(BrokenPipeError):
            os.write(write_fd, b"cannot be delivered")
        assert signal.getsignal(signal.SIGPIPE) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGPIPE, previous)
        if read_fd >= 0:
            os.close(read_fd)
        os.close(write_fd)
