"""258｜``Popen`` 生命周期、属性、poll/wait 与 communicate。

Popen 提供 run 下层的异步句柄。poll 只做状态快照，wait 等待退出，communicate 同时写入
stdin、排空 stdout/stderr 并 wait，可避免多个 PIPE 互相填满造成死锁。Popen 作为 context
manager 退出时关闭标准流并等待子进程，适合把资源生命周期限制在一个代码块内。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.Popen
# polyglot-covers: python.subprocess.Popen.args
# polyglot-covers: python.subprocess.Popen.pid
# polyglot-covers: python.subprocess.Popen.returncode
# polyglot-covers: python.subprocess.Popen.stdin
# polyglot-covers: python.subprocess.Popen.stdout
# polyglot-covers: python.subprocess.Popen.stderr
# polyglot-covers: python.subprocess.Popen.poll
# polyglot-covers: python.subprocess.Popen.wait
# polyglot-covers: python.subprocess.Popen.communicate
# polyglot-covers: python.subprocess.Popen-context-manager
# polyglot-covers: python.subprocess.Popen-text-pipes
# polyglot-covers: python.subprocess.communicate-drains-all-pipes

import io
import subprocess
import sys


def _python_command(source):
    return [sys.executable, "-c", source]


def test_popen_attributes_and_poll_reflect_a_live_then_finished_child():
    command = _python_command("import sys; sys.stdin.buffer.read()")
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        assert process.args == command
        assert process.pid > 0
        assert process.poll() is None
        assert process.returncode is None

        process.stdin.close()
        assert process.wait(timeout=2) == 0
        assert process.poll() == process.returncode == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_communicate_writes_input_and_drains_stdout_and_stderr_together():
    source = (
        "import sys; data = sys.stdin.read(); "
        "sys.stdout.write(data.upper()); sys.stderr.write(str(len(data)))"
    )
    process = subprocess.Popen(
        _python_command(source),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout, stderr = process.communicate("hello")

    assert stdout == "HELLO"
    assert stderr == "5"
    assert process.returncode == 0
    assert isinstance(process.stdout, io.TextIOBase)


def test_popen_context_manager_closes_streams_and_waits_on_exit():
    with subprocess.Popen(
        _python_command("print('finished')"),
        stdout=subprocess.PIPE,
        text=True,
    ) as process:
        stream = process.stdout
        assert stream.read() == "finished\n"

    assert process.returncode == 0
    assert stream.closed is True
