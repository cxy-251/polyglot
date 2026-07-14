"""357｜Linux pidfd_send_signal 使用稳定的进程引用。

传统 pid 可能在目标退出后被系统复用；pidfd 是指向某个进程实例的文件描述符，配合
pidfd_send_signal 可避免“检查后再发送”期间命中另一个进程。signal=0 只做目标与权限校验，不
实际投递信号，适合安全展示该接口；siginfo 在 Python 3.10 必须为 None，flags 必须为 0。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.pidfd_send_signal
# polyglot-covers: python.signal.pidfd-process-identity
# polyglot-covers: python.signal.pidfd-send-signal-zero-validation
# polyglot-covers: python.signal.pidfd-send-signal-siginfo-none
# polyglot-covers: python.signal.pidfd-send-signal-flags-zero

import os
import signal

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "pidfd_send_signal") or not hasattr(os, "pidfd_open"),
    reason="pidfd 需要 Linux 5.1+ 与对应 Python 构建支持",
)


def test_pidfd_signal_zero_validates_this_process_without_delivering_a_signal():
    pidfd = os.pidfd_open(os.getpid())
    try:
        assert os.get_inheritable(pidfd) is False
        assert signal.pidfd_send_signal(pidfd, 0, None, 0) is None

        with pytest.raises(TypeError):
            signal.pidfd_send_signal(pidfd, 0, object(), 0)
        with pytest.raises(OSError):
            signal.pidfd_send_signal(pidfd, 0, None, 1)
    finally:
        os.close(pidfd)
