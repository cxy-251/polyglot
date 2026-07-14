"""350｜信号处理器的主线程约束与跨线程投递。

只有主解释器的主线程可以安装处理器或 wakeup fd。信号即使由 worker 线程触发，Python 回调也在
主线程运行；因此 signal 不是线程间通信机制，worker 间协调应使用 Event、Queue 等同步原语。
pthread_kill 的 signalnum=0 只校验线程标识，不实际投递信号。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.only-main-thread-installs-handler
# polyglot-covers: python.signal.signal-worker-thread-valueerror
# polyglot-covers: python.signal.only-main-thread-sets-wakeup-fd
# polyglot-covers: python.signal.set-wakeup-fd-worker-thread-valueerror
# polyglot-covers: python.signal.handler-runs-in-main-thread
# polyglot-covers: python.signal.signal-not-thread-communication
# polyglot-covers: python.signal.pthread_kill
# polyglot-covers: python.signal.pthread-kill-zero-validation
# polyglot-covers: python.signal.raise-signal-from-worker

import queue
import signal
import threading

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1") or not hasattr(signal, "pthread_kill"),
    reason="线程信号 API 只在支持 pthread 的 Unix 平台提供",
)


def test_worker_cannot_install_a_handler_or_change_the_wakeup_fd():
    results = queue.Queue()

    def worker():
        for operation in (
            lambda: signal.signal(signal.SIGUSR1, signal.SIG_IGN),
            lambda: signal.set_wakeup_fd(-1),
        ):
            try:
                operation()
            except Exception as error:  # noqa: BLE001 - 案例需要把线程异常交回主线程
                results.put(error)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    errors = [results.get_nowait(), results.get_nowait()]
    assert all(isinstance(error, ValueError) for error in errors)


def test_signal_raised_by_worker_still_dispatches_handler_in_main_thread():
    main_ident = threading.get_ident()
    handled_in = []

    def handler(signum, frame):
        handled_in.append(threading.get_ident())

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, handler)
        thread = threading.Thread(target=signal.raise_signal, args=(signal.SIGUSR1,))
        thread.start()
        thread.join()
        assert handled_in == [main_ident]
    finally:
        signal.signal(signal.SIGUSR1, previous)


def test_pthread_kill_zero_checks_the_current_thread_without_delivery():
    assert signal.pthread_kill(threading.get_ident(), 0) is None
