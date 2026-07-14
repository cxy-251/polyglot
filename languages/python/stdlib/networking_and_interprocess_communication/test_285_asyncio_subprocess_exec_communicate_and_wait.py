"""285｜``create_subprocess_exec``、Process streams、communicate 与 async wait。

asyncio Process 类似 Popen，但没有 poll，wait/communicate 是 coroutine 且不接受 timeout；
需要用 wait_for 包装。PIPE 对 stdin 生成 StreamWriter，对 stdout/stderr 生成 StreamReader。
使用 PIPE 时 communicate 会并发排空，避免先 wait 造成 pipe capacity deadlock。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.create_subprocess_exec
# polyglot-covers: python.asyncio.subprocess.Process
# polyglot-covers: python.asyncio.subprocess.Process.pid
# polyglot-covers: python.asyncio.subprocess.Process.returncode
# polyglot-covers: python.asyncio.subprocess.Process.stdin
# polyglot-covers: python.asyncio.subprocess.Process.stdout
# polyglot-covers: python.asyncio.subprocess.Process.stderr
# polyglot-covers: python.asyncio.subprocess.Process.wait
# polyglot-covers: python.asyncio.subprocess.Process.communicate
# polyglot-covers: python.asyncio.subprocess.Process-no-poll
# polyglot-covers: python.asyncio.subprocess.Process-no-timeout-parameter
# polyglot-covers: python.asyncio.subprocess.PIPE
# polyglot-covers: python.asyncio.subprocess.STDOUT
# polyglot-covers: python.asyncio.subprocess.DEVNULL
# polyglot-covers: python.asyncio.subprocess.communicate-drains-pipes
# polyglot-covers: python.asyncio.subprocess.communicate-memory-buffering

import asyncio
import sys

import pytest


def test_exec_process_communicate_maps_pipe_stream_types_and_attributes():
    async def scenario():
        source = (
            "import sys; data = sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(data[::-1]); "
            "sys.stderr.write(str(len(data)))"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            source,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=32,
        )

        assert process.pid > 0
        assert process.returncode is None
        assert isinstance(process.stdin, asyncio.StreamWriter)
        assert isinstance(process.stdout, asyncio.StreamReader)
        assert isinstance(process.stderr, asyncio.StreamReader)
        assert hasattr(process, "poll") is False

        stdout, stderr = await process.communicate(b"abcdef")
        assert stdout == b"fedcba"
        assert stderr == b"6"
        assert process.returncode == 0

    asyncio.run(scenario())

def test_stdout_merge_and_devnull_use_same_constants_as_sync_subprocess():
    async def scenario():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import os; os.write(1, b'out|'); os.write(2, b'err')",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, stderr = await process.communicate()

        assert stdout == b"out|err"
        assert stderr is None
        assert process.stdin is None

    asyncio.run(scenario())


def test_process_wait_uses_outer_wait_for_and_can_be_retried_after_timeout():
    async def scenario():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import sys; sys.stdin.buffer.read()",
            stdin=asyncio.subprocess.PIPE,
        )
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=0)
            assert process.returncode is None

            with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
                process.wait(timeout=1)

            process.stdin.close()
            assert await process.wait() == 0
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

    asyncio.run(scenario())


def test_communicate_drains_two_outputs_larger_than_typical_pipe_capacity():
    async def scenario():
        amount = 100_000
        source = (
            f"import os; os.write(1, b'o' * {amount}); "
            f"os.write(2, b'e' * {amount})"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            source,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        assert process.returncode == 0
        assert stdout == b"o" * amount
        assert stderr == b"e" * amount

    asyncio.run(scenario())
