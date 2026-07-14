"""349｜安装、查询、恢复处理器以及 raise_signal。

signal.signal 返回旧处理器，getsignal 返回当前处理器。Python 模拟 BSD 语义：自定义处理器执行后
仍保持安装（SIGCHLD 的具体行为依平台）；临时修改全局处理器必须放在 try/finally 中恢复。
处理器接收信号号与当时主线程的栈帧，不能把它写成无参数回调。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.signal
# polyglot-covers: python.signal.signal-returns-previous-handler
# polyglot-covers: python.signal.getsignal
# polyglot-covers: python.signal.python-handler-two-arguments
# polyglot-covers: python.signal.python-handler-frame
# polyglot-covers: python.signal.handler-remains-installed
# polyglot-covers: python.signal.raise_signal
# polyglot-covers: python.signal.SIG_IGN-behavior
# polyglot-covers: python.signal.restore-global-handler-workflow

import signal

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1"),
    reason="案例使用 Unix 用户自定义信号，避免改变 SIGINT/SIGTERM 语义",
)


def test_custom_handler_receives_signum_and_frame_and_remains_installed():
    received = []

    def handler(signum, frame):
        received.append((signum, frame))

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        assert signal.signal(signal.SIGUSR1, handler) is previous
        assert signal.getsignal(signal.SIGUSR1) is handler

        assert signal.raise_signal(signal.SIGUSR1) is None
        signal.raise_signal(signal.SIGUSR1)
        assert [item[0] for item in received] == [signal.SIGUSR1, signal.SIGUSR1]
        assert all(item[1] is not None for item in received)
        assert signal.getsignal(signal.SIGUSR1) is handler
    finally:
        signal.signal(signal.SIGUSR1, previous)


def test_ignore_action_discards_the_signal_and_signal_returns_custom_handler():
    called = []

    def handler(signum, frame):
        called.append(signum)

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, handler)
        assert signal.signal(signal.SIGUSR1, signal.SIG_IGN) is handler
        signal.raise_signal(signal.SIGUSR1)
        assert called == []
        assert signal.getsignal(signal.SIGUSR1) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGUSR1, previous)
