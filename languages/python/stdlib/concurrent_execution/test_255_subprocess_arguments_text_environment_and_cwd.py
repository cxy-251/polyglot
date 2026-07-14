"""255｜subprocess 参数边界、二进制/文本模式、环境与工作目录。

shell=False 时参数序列的每个元素就是一个 argv，不再由 shell 二次解析；空格和元字符
因此不需要 shell quoting。stdin/stdout/stderr 默认为二进制；text、encoding 或 errors
会在管道外包 TextIOWrapper。env 是子进程的整份环境映射，不是对父环境的增量补丁。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.subprocess.args-sequence
# polyglot-covers: python.subprocess.shell-false-literal-arguments
# polyglot-covers: python.subprocess.run-input
# polyglot-covers: python.subprocess.binary-stream-mode
# polyglot-covers: python.subprocess.text-stream-mode
# polyglot-covers: python.subprocess.encoding
# polyglot-covers: python.subprocess.errors
# polyglot-covers: python.subprocess.universal_newlines
# polyglot-covers: python.subprocess.env-replacement
# polyglot-covers: python.subprocess.cwd
# polyglot-covers: python.subprocess.path-like-arguments

import json
import os
from pathlib import Path
import subprocess
import sys


def _python_command(source, *arguments):
    return [Path(sys.executable), "-c", source, *arguments]


def test_argument_sequence_preserves_spaces_empty_strings_and_metacharacters():
    arguments = ["two words", "", "$(not-a-command)", "semi;colon"]
    completed = subprocess.run(
        _python_command(
            "import json, sys; print(json.dumps(sys.argv[1:]))",
            *arguments,
        ),
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(completed.stdout) == arguments


def test_binary_input_and_text_input_have_matching_output_types():
    source = "import sys; data = sys.stdin.buffer.read(); sys.stdout.buffer.write(data[::-1])"

    binary = subprocess.run(
        _python_command(source),
        input=b"abc",
        capture_output=True,
        check=True,
    )
    text = subprocess.run(
        _python_command(source),
        input="abc",
        capture_output=True,
        text=True,
        check=True,
    )

    assert binary.stdout == b"cba"
    assert text.stdout == "cba"


def test_encoding_and_errors_control_pipe_decoding():
    completed = subprocess.run(
        _python_command("import sys; sys.stdout.buffer.write(b'valid\\xff')"),
        stdout=subprocess.PIPE,
        encoding="ascii",
        errors="replace",
        check=True,
    )

    assert completed.stdout == "valid\N{REPLACEMENT CHARACTER}"
    assert isinstance(completed.stdout, str)


def test_universal_newlines_is_the_backward_compatible_text_alias():
    completed = subprocess.run(
        _python_command("print('line')"),
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )

    assert completed.stdout == "line\n"


def test_env_replaces_inheritance_and_cwd_accepts_path_like(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYGLOT_PARENT_ONLY", "parent")
    workdir = tmp_path / "child working directory"
    workdir.mkdir()
    (workdir / "marker.txt").write_text("inside", encoding="utf-8")

    child_env = os.environ.copy()
    child_env.pop("POLYGLOT_PARENT_ONLY")
    child_env["POLYGLOT_CHILD_ONLY"] = "child"
    source = (
        "import json, os, pathlib; "
        "print(json.dumps([os.getenv('POLYGLOT_PARENT_ONLY'), "
        "os.environ['POLYGLOT_CHILD_ONLY'], pathlib.Path('marker.txt').read_text()]))"
    )

    completed = subprocess.run(
        _python_command(source),
        cwd=workdir,
        env=child_env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(completed.stdout) == [None, "child", "inside"]
