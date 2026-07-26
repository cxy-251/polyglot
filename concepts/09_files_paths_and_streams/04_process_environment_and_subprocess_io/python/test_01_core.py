"""进程环境与子进程输入输出。

共同问题：环境、工作目录和参数属于谁；如何向子进程传入数据并取得输出与退出状态；
哪些能力属于语言标准库，哪些依赖运行时或操作系统。
"""

# polyglot-family: files_paths_and_streams
# polyglot-concept: process_environment_and_subprocess_io
# polyglot-related: languages/python/stdlib/088-094_concurrent_execution/
# polyglot-related+: test_093_subprocess_complete_run_popen_streams_timeouts_signals_and_security.py

import os
import subprocess
import sys


def test_environment_mapping_can_be_copied_for_a_child_only():
    child_environment = os.environ.copy()
    child_environment["POLYGLOT_VALUE"] = "child"
    result = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ['POLYGLOT_VALUE'])"],
        env=child_environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == "child\n"
    assert os.environ.get("POLYGLOT_VALUE") != "child"


def test_child_working_directory_is_explicit(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getcwd())"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == str(tmp_path)


def test_completed_process_captures_standard_io_and_status():
    result = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read().upper())"],
        input="hello",
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.args[0] == sys.executable
    assert result.returncode == 0
    assert result.stdout == "HELLO"


def test_argument_list_avoids_implicit_shell_parsing():
    result = subprocess.run(
        [sys.executable, "-c", "import sys; print(sys.argv[1])", "a b; $HOME"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == "a b; $HOME\n"
