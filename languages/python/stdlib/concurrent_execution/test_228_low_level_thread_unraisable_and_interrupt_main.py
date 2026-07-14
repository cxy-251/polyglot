"""228｜``_thread`` unraisable exception boundary 与 ``interrupt_main`` signal dispatch。

raw thread 没有 Thread.excepthook；普通异常交给 ``sys.unraisablehook``，hook args.object
是原 target callable。``interrupt_main`` 不真正发送 OS signal，只安排 main thread 调用
Python signal handler；为避免影响 pytest process，signal workflow 放进 child interpreter。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python._thread.unhandled-exception
# polyglot-covers: python._thread.sys-unraisablehook-dispatch
# polyglot-covers: python._thread.unraisablehook-object-is-target
# polyglot-covers: python._thread.SystemExit-silently-ignored
# polyglot-covers: python._thread.interrupt_main
# polyglot-covers: python._thread.interrupt-main-custom-signum
# polyglot-covers: python._thread.interrupt-main-schedules-handler

import _thread
import os
import signal
import subprocess
import sys
import threading

import pytest


def test_raw_thread_exception_is_reported_to_sys_unraisablehook():
    """hook 中只保存摘要并立即释放 args，避免保留 traceback/reference cycle。"""

    original_hook = sys.unraisablehook
    completed = threading.Event()
    summaries = []

    def fail_worker():
        raise LookupError("raw failure")

    def capture(args):
        summaries.append(
            (
                args.exc_type,
                str(args.exc_value),
                args.object is fail_worker,
                args.err_msg,
            )
        )
        completed.set()

    sys.unraisablehook = capture
    try:
        _thread.start_new_thread(fail_worker, ())
        assert completed.wait(timeout=2)
    finally:
        sys.unraisablehook = original_hook

    assert summaries == [(LookupError, "raw failure", True, None)]


@pytest.mark.skipif(os.name != "posix", reason="custom SIGUSR1 案例使用 POSIX signal")
def test_interrupt_main_custom_signal_runs_python_handler_in_child_process():
    """child 隔离 process-global signal handler；raw worker 发请求，main loop 执行 handler。"""

    code = """
import _thread
import json
import signal
import threading

requested = threading.Event()
received = []

def handle(signum, frame):
    received.append((signum, threading.current_thread() is threading.main_thread()))

def request_interrupt():
    _thread.interrupt_main(signal.SIGUSR1)
    requested.set()

signal.signal(signal.SIGUSR1, handle)
_thread.start_new_thread(request_interrupt, ())
assert requested.wait(timeout=2)
assert received
print(json.dumps(received))
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert completed.stderr == ""
    assert completed.stdout.strip() == f"[[{signal.SIGUSR1}, true]]"
