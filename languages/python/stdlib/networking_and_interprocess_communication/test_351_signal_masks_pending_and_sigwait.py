"""351｜pthread signal mask、pending 集合与同步 sigwait。

阻塞信号不会丢弃它，而是让它进入当前线程的 pending 集合。sigwait 可同步消费其中一个信号，且
不会调用该信号的 Python handler；这比异步回调更适合专用信号线程。mask 是线程局部状态，测试和
库代码都必须保存旧集合并用 SIG_SETMASK 恢复。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.pthread_sigmask
# polyglot-covers: python.signal.pthread-sigmask-returns-old-mask
# polyglot-covers: python.signal.pthread-sigmask-empty-query
# polyglot-covers: python.signal.blocked-signal-becomes-pending
# polyglot-covers: python.signal.sigpending
# polyglot-covers: python.signal.sigwait
# polyglot-covers: python.signal.sigwait-consumes-pending
# polyglot-covers: python.signal.sigwait-bypasses-handler
# polyglot-covers: python.signal.thread-mask-save-restore-workflow
# polyglot-covers: python.signal.sigkill-sigstop-cannot-be-blocked

import signal

import pytest


REQUIRED = ("pthread_sigmask", "sigpending", "sigwait", "SIGUSR1")
pytestmark = pytest.mark.skipif(
    any(not hasattr(signal, name) for name in REQUIRED),
    reason="POSIX pthread signal mask API 在此平台不可用",
)


def test_blocked_signal_is_pending_until_sigwait_consumes_it_without_handler():
    handled = []
    previous_handler = signal.getsignal(signal.SIGUSR1)
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.signal(signal.SIGUSR1, lambda signum, frame: handled.append(signum))
        returned_old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1})
        assert returned_old == previous_mask
        assert signal.SIGUSR1 in signal.pthread_sigmask(signal.SIG_BLOCK, [])

        signal.raise_signal(signal.SIGUSR1)
        assert signal.SIGUSR1 in signal.sigpending()
        assert handled == []

        accepted = signal.sigwait({signal.SIGUSR1})
        assert accepted == signal.SIGUSR1
        assert signal.SIGUSR1 not in signal.sigpending()
        assert handled == []
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        signal.signal(signal.SIGUSR1, previous_handler)


def test_sigkill_and_sigstop_are_silently_excluded_from_a_requested_mask():
    if not hasattr(signal, "SIGKILL") or not hasattr(signal, "SIGSTOP"):
        pytest.skip("平台没有 POSIX 的不可阻塞信号")

    previous = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGKILL, signal.SIGSTOP})
        current = signal.pthread_sigmask(signal.SIG_BLOCK, [])
        assert signal.SIGKILL not in current
        assert signal.SIGSTOP not in current
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)
