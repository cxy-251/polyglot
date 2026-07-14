"""257｜run/wait/communicate 的 timeout 语义与可靠清理。

run 超时会 kill 并 wait 后再抛 TimeoutExpired；直接 communicate 超时则不会替调用者杀掉
子进程，规范清理流程是 kill 后再次 communicate。第二次 communicate 不会丢失第一次已读
输出。wait 超时也可安全重试。案例用 Event 或未关闭的 stdin 阻塞，不使用 sleep。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.TimeoutExpired
# polyglot-covers: python.subprocess.TimeoutExpired.cmd
# polyglot-covers: python.subprocess.TimeoutExpired.timeout
# polyglot-covers: python.subprocess.TimeoutExpired.output
# polyglot-covers: python.subprocess.TimeoutExpired.stdout
# polyglot-covers: python.subprocess.TimeoutExpired.stderr
# polyglot-covers: python.subprocess.run-timeout-kill-wait
# polyglot-covers: python.subprocess.Popen.wait-timeout-retry
# polyglot-covers: python.subprocess.Popen.communicate-timeout
# polyglot-covers: python.subprocess.communicate-timeout-output-preserved
# polyglot-covers: python.subprocess.communicate-timeout-manual-cleanup

import subprocess
import sys

import pytest


def _python_command(source):
    return [sys.executable, "-c", source]


def test_run_timeout_kills_and_waits_before_reraising():
    command = _python_command(
        "import sys, threading; "
        "sys.stdout.write('ready'); sys.stdout.flush(); threading.Event().wait()"
    )

    with pytest.raises(subprocess.TimeoutExpired) as raised:
        subprocess.run(command, capture_output=True, text=True, timeout=1)

    error = raised.value
    assert error.cmd == command
    assert error.timeout == 1
    # 即便 text=True，TimeoutExpired 中已捕获的部分输出在 3.10 仍规定为 bytes。
    assert error.output == error.stdout == b"ready"
    assert error.stderr is None


def test_wait_timeout_leaves_process_alive_and_can_be_retried():
    process = subprocess.Popen(
        _python_command("import sys; sys.stdin.buffer.read()"),
        stdin=subprocess.PIPE,
    )
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=0)
        assert process.returncode is None

        process.stdin.close()
        assert process.wait(timeout=2) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_communicate_timeout_requires_kill_then_preserves_partial_output():
    process = subprocess.Popen(
        _python_command(
            "import sys, threading; "
            "sys.stdout.buffer.write(b'before-timeout'); sys.stdout.buffer.flush(); "
            "threading.Event().wait()"
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        with pytest.raises(subprocess.TimeoutExpired) as raised:
            process.communicate(timeout=1)

        assert raised.value.output == b"before-timeout"
        assert process.poll() is None
        process.kill()
        stdout, stderr = process.communicate()
        assert stdout == b"before-timeout"
        assert stderr == b""
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
