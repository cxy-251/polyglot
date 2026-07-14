"""254｜``subprocess.run``、CompletedProcess 与标准流重定向。

run 是能满足大多数同步调用时应优先使用的入口：它启动子进程、等待退出，并把参数、
退出码及可选捕获内容汇总成 CompletedProcess。默认不会捕获输出；PIPE、STDOUT 与
DEVNULL 分别表示新管道、合并到 stdout，以及丢弃到操作系统空设备。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.run
# polyglot-covers: python.subprocess.CompletedProcess
# polyglot-covers: python.subprocess.CompletedProcess.args
# polyglot-covers: python.subprocess.CompletedProcess.returncode
# polyglot-covers: python.subprocess.CompletedProcess.stdout
# polyglot-covers: python.subprocess.CompletedProcess.stderr
# polyglot-covers: python.subprocess.CompletedProcess.check_returncode
# polyglot-covers: python.subprocess.PIPE
# polyglot-covers: python.subprocess.STDOUT
# polyglot-covers: python.subprocess.DEVNULL
# polyglot-covers: python.subprocess.capture-output

import subprocess
import sys

import pytest


def _python_command(source, *arguments):
    return [sys.executable, "-c", source, *map(str, arguments)]


def test_run_returns_binary_captured_streams_and_original_arguments():
    command = _python_command(
        "import os; os.write(1, b'normal'); os.write(2, b'problem')"
    )

    completed = subprocess.run(command, capture_output=True, check=False)

    assert isinstance(completed, subprocess.CompletedProcess)
    assert completed.args == command
    assert completed.returncode == 0
    assert completed.stdout == b"normal"
    assert completed.stderr == b"problem"
    assert completed.check_returncode() is None


def test_stderr_can_be_combined_into_stdout_in_write_order():
    completed = subprocess.run(
        _python_command("import os; os.write(1, b'out|'); os.write(2, b'err')"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )

    assert completed.stdout == b"out|err"
    assert completed.stderr is None


def test_devnull_discards_output_without_creating_captured_attributes():
    completed = subprocess.run(
        _python_command("import os; os.write(1, b'out'); os.write(2, b'err')"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    assert completed.stdout is None
    assert completed.stderr is None


def test_completed_process_check_returncode_raises_for_nonzero_status():
    completed = subprocess.run(
        _python_command("raise SystemExit(7)"),
        capture_output=True,
        check=False,
    )

    with pytest.raises(subprocess.CalledProcessError) as raised:
        completed.check_returncode()

    assert raised.value.returncode == 7
    assert raised.value.cmd == completed.args
