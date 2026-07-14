"""262｜显式 shell、安全边界与 legacy shell helpers。

subprocess 默认不会隐式启用 shell；只有需要 shell builtin、pipeline 或 expansion 时才应
shell=True。此时 command string 的 quoting 完全由调用者负责，绝不能拼接不可信输入。
getstatusoutput/getoutput 也隐式使用 shell，只适合维护旧代码和受控的固定命令。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.shell-true
# polyglot-covers: python.subprocess.shell-expansion
# polyglot-covers: python.subprocess.shell-injection-responsibility
# polyglot-covers: python.subprocess.shell-command-not-found-status
# polyglot-covers: python.subprocess.getstatusoutput
# polyglot-covers: python.subprocess.getstatusoutput-trailing-newline-stripped
# polyglot-covers: python.subprocess.getoutput
# polyglot-covers: python.subprocess.legacy-shell-stderr-merged

import os
import subprocess

import pytest


pytestmark = pytest.mark.skipif(os.name != "posix", reason="案例使用 POSIX /bin/sh 语法")


def test_shell_expansion_is_explicit_and_quoted_values_remain_data():
    environment = os.environ.copy()
    environment["POLYGLOT_VALUE"] = "literal; $(not-executed)"

    completed = subprocess.run(
        "printf '%s' \"$POLYGLOT_VALUE\"",
        shell=True,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout == environment["POLYGLOT_VALUE"]
    assert completed.stderr == ""


def test_shell_reports_missing_inner_command_as_status_not_start_oserror():
    completed = subprocess.run(
        "polyglot-command-that-does-not-exist",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    assert completed.returncode == 127


def test_getstatusoutput_returns_exitcode_and_strips_one_trailing_newline():
    status, output = subprocess.getstatusoutput("printf 'line\\n'; exit 7")

    assert status == 7
    assert output == "line"


def test_getoutput_ignores_status_and_combines_shell_stdout_and_stderr():
    output = subprocess.getoutput("printf 'out'; printf 'err' >&2; exit 5")

    assert output == "outerr"
