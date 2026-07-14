"""286｜asyncio shell quoting 与 POSIX Process signal control。

create_subprocess_shell 明确启用 shell，调用者必须用 shlex.quote 保护不可信字符串；exec
形式更适合普通 argv。Process 的 send_signal/terminate/kill 是同步发请求，随后 await wait
观察退出。POSIX 信号退出码仍为负 signal number。child 以 Event 阻塞，不使用 sleep。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.create_subprocess_shell
# polyglot-covers: python.asyncio.subprocess-shell-quoting
# polyglot-covers: python.asyncio.subprocess-shell-injection-responsibility
# polyglot-covers: python.asyncio.subprocess.Process.send_signal
# polyglot-covers: python.asyncio.subprocess.Process.terminate
# polyglot-covers: python.asyncio.subprocess.Process.kill
# polyglot-covers: python.asyncio.subprocess-signal-negative-returncode

import asyncio
import os
import shlex
import signal
import sys

import pytest


pytestmark = pytest.mark.skipif(os.name != "posix", reason="案例使用 POSIX shell 与 signal")


async def _blocking_process():
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import sys, threading; print('ready', flush=True); threading.Event().wait()",
        stdout=asyncio.subprocess.PIPE,
    )
    line = await asyncio.wait_for(process.stdout.readline(), timeout=2)
    if line != b"ready\n":
        process.kill()
        await process.wait()
        raise AssertionError(f"invalid child readiness record: {line!r}")
    return process


def test_shell_command_uses_explicit_quoting_for_data_with_metacharacters():
    async def scenario():
        value = "literal; $(not-executed)"
        command = f"printf '%s' {shlex.quote(value)}"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        assert process.returncode == 0
        assert stdout.decode() == value
        assert stderr == b""

    asyncio.run(scenario())

def test_send_signal_terminate_and_kill_set_negative_posix_returncodes():
    async def scenario():
        signalled = await _blocking_process()
        signalled.send_signal(signal.SIGTERM)
        assert await signalled.wait() == -signal.SIGTERM

        terminated = await _blocking_process()
        terminated.terminate()
        assert await terminated.wait() == -signal.SIGTERM

        killed = await _blocking_process()
        killed.kill()
        assert await killed.wait() == -signal.SIGKILL

    asyncio.run(scenario())
