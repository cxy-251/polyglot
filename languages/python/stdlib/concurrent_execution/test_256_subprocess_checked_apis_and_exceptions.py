"""256｜checked subprocess API、异常对象与无效参数。

check=True、check_call 和 check_output 把非零退出码转换成 CalledProcessError，并保留
command、returncode 及已捕获的标准流。程序根本无法启动时则传播 OSError，而不是伪造
一个退出码。capture_output/input 是 run 的便利参数，不能再同时手工指定对应 PIPE。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.SubprocessError
# polyglot-covers: python.subprocess.CalledProcessError
# polyglot-covers: python.subprocess.CalledProcessError.cmd
# polyglot-covers: python.subprocess.CalledProcessError.returncode
# polyglot-covers: python.subprocess.CalledProcessError.output
# polyglot-covers: python.subprocess.CalledProcessError.stdout
# polyglot-covers: python.subprocess.CalledProcessError.stderr
# polyglot-covers: python.subprocess.run-check
# polyglot-covers: python.subprocess.call
# polyglot-covers: python.subprocess.check_call
# polyglot-covers: python.subprocess.check_output
# polyglot-covers: python.subprocess.start-failure-oserror
# polyglot-covers: python.subprocess.invalid-redirection-combinations

import subprocess
import sys

import pytest


def _python_command(source):
    return [sys.executable, "-c", source]


def test_run_check_error_retains_both_captured_streams():
    command = _python_command(
        "import os; os.write(1, b'partial-out'); os.write(2, b'partial-err'); "
        "raise SystemExit(9)"
    )

    with pytest.raises(subprocess.CalledProcessError) as raised:
        subprocess.run(command, capture_output=True, check=True)

    error = raised.value
    assert error.cmd == command
    assert error.returncode == 9
    assert error.output == error.stdout == b"partial-out"
    assert error.stderr == b"partial-err"
    assert "exit status 9" in str(error)
    assert isinstance(error, subprocess.SubprocessError)


def test_call_check_call_and_check_output_express_distinct_policies():
    assert subprocess.call(_python_command("raise SystemExit(4)")) == 4
    assert subprocess.check_call(_python_command("pass")) == 0

    output = subprocess.check_output(
        _python_command("import sys; sys.stdout.buffer.write(sys.stdin.buffer.read().upper())"),
        input=b"hello",
    )
    assert output == b"HELLO"

    with pytest.raises(subprocess.CalledProcessError) as raised:
        subprocess.check_output(_python_command("print('kept'); raise SystemExit(3)"))
    assert raised.value.output == b"kept\n"


def test_missing_executable_propagates_oserror_instead_of_returning_status(tmp_path):
    missing = tmp_path / "definitely-missing-program"

    with pytest.raises(FileNotFoundError):
        subprocess.run([missing], check=False)


def test_run_rejects_conflicting_convenience_and_stream_arguments():
    command = _python_command("pass")

    with pytest.raises(ValueError, match="stdout and stderr arguments"):
        subprocess.run(command, capture_output=True, stdout=subprocess.PIPE)
    with pytest.raises(ValueError, match="stdin and input arguments"):
        subprocess.run(command, input=b"", stdin=subprocess.PIPE)
