"""263｜Popen constructor 的 executable/bufsize 与审计事件。

executable 可替换实际执行文件，而 Popen.args 仍保留调用者传入的 argv；这是少见的高级
入口。text=True、bufsize=1 产生 line-buffered stdin，可用于简单请求/响应协议。每次创建
进程还会发出 subprocess.Popen audit event；审计 hook 不可移除，所以案例放在隔离子进程。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.Popen.executable
# polyglot-covers: python.subprocess.executable-does-not-rewrite-args
# polyglot-covers: python.subprocess.Popen.bufsize
# polyglot-covers: python.subprocess.text-line-buffering
# polyglot-covers: python.subprocess.Popen-audit-event
# polyglot-covers: python.subprocess.Popen-audit-arguments
# polyglot-covers: python.subprocess.audit-hook-process-isolation

import subprocess
import sys


def test_executable_replaces_program_but_args_retains_original_argv():
    arguments = [
        "educational-display-name",
        "-c",
        "import sys; print(sys.argv[0])",
    ]

    completed = subprocess.run(
        arguments,
        executable=sys.executable,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.args == arguments
    assert completed.stdout == "-c\n"


def test_text_line_buffering_flushes_a_newline_to_a_waiting_child():
    source = (
        "import sys; line = sys.stdin.readline(); "
        "sys.stdout.write('ack:' + line); sys.stdout.flush()"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", source],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        assert process.stdin.line_buffering is True
        process.stdin.write("request\n")
        assert process.stdout.readline() == "ack:request\n"
        process.stdin.close()
        assert process.wait(timeout=2) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_popen_audit_event_exposes_launch_boundary_in_isolated_interpreter():
    source = """
import subprocess
import sys

seen = []


def audit(event, arguments):
    if event == "subprocess.Popen":
        seen.append(arguments)


sys.addaudithook(audit)
command = [sys.executable, "-c", "pass"]
subprocess.run(command, check=True)
executable, arguments, cwd, env = seen[0]
print(executable == sys.executable, arguments == command, cwd is None, env is None)
"""

    completed = subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout == "True True True True\n"
