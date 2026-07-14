"""352｜sigwaitinfo 的发送者元数据与 sigtimedwait 的零超时轮询。

sigwaitinfo 与 sigtimedwait 同步接收已阻塞信号并返回 siginfo_t 视图；前者等待，后者可用
timeout=0 只检查当前 pending 集合。要先 block 再产生信号，否则默认动作或异步 handler 可能先
执行，这是采用同步信号模型时最关键的顺序。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.sigwaitinfo
# polyglot-covers: python.signal.sigwaitinfo.si_signo
# polyglot-covers: python.signal.sigwaitinfo.si_pid
# polyglot-covers: python.signal.sigwaitinfo.si_uid
# polyglot-covers: python.signal.sigwaitinfo.si_code
# polyglot-covers: python.signal.sigtimedwait
# polyglot-covers: python.signal.sigtimedwait-timeout-zero-poll
# polyglot-covers: python.signal.sigtimedwait-timeout-none-result
# polyglot-covers: python.signal.block-before-synchronous-wait-workflow

import os
import signal

import pytest


REQUIRED = ("pthread_sigmask", "sigwaitinfo", "sigtimedwait", "SIGUSR2")
pytestmark = pytest.mark.skipif(
    any(not hasattr(signal, name) for name in REQUIRED),
    reason="POSIX siginfo 同步等待 API 在此平台不可用",
)


def test_pending_signal_produces_sender_information_and_is_consumed():
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR2})
        signal.raise_signal(signal.SIGUSR2)

        info = signal.sigwaitinfo({signal.SIGUSR2})
        assert info.si_signo == signal.SIGUSR2
        assert info.si_pid == os.getpid()
        assert info.si_uid == os.getuid()
        assert isinstance(info.si_code, int)

        # 第一次 wait 已消费 pending 信号，零超时不会等待未来事件。
        assert signal.sigtimedwait({signal.SIGUSR2}, 0) is None
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def test_timed_wait_with_zero_timeout_still_consumes_an_already_pending_signal():
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR2})
        signal.raise_signal(signal.SIGUSR2)
        info = signal.sigtimedwait({signal.SIGUSR2}, 0)
        assert info is not None
        assert info.si_signo == signal.SIGUSR2
        assert signal.sigtimedwait({signal.SIGUSR2}, 0) is None
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
