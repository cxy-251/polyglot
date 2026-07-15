"""375｜python -m json.tool 的验证、格式化与 JSON Lines 模式。

json.tool 是标准库自带的命令行验证器。它成功时输出 pretty JSON，语法错误时非零退出并把位置
信息写到 stderr；--sort-keys 便于稳定 diff，--no-ensure-ascii 保留可读 Unicode，--json-lines
逐行处理独立文档。案例使用 sys.executable，确保调用的正是运行测试的 Python 3.10。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.tool
# polyglot-covers: python.json.tool-validates-and-pretty-prints
# polyglot-covers: python.json.tool-invalid-input-nonzero-exit
# polyglot-covers: python.json.tool-error-to-stderr
# polyglot-covers: python.json.tool-sort-keys
# polyglot-covers: python.json.tool-no-ensure-ascii
# polyglot-covers: python.json.tool-json-lines
# polyglot-covers: python.json.tool-compact
# polyglot-covers: python.json.tool-sys-executable-workflow

import json
import subprocess
import sys


def run_json_tool(*arguments, input_text=None):
    return subprocess.run(
        [sys.executable, "-m", "json.tool", *map(str, arguments)],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_tool_validates_sorts_and_preserves_unicode_in_file_workflow(tmp_path):
    source = tmp_path / "input.json"
    target = tmp_path / "output.json"
    source.write_text('{"z": 1, "城市": "深圳"}', encoding="utf-8")

    completed = run_json_tool("--sort-keys", "--no-ensure-ascii", source, target)
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert json.loads(target.read_text(encoding="utf-8")) == {"z": 1, "城市": "深圳"}
    rendered = target.read_text(encoding="utf-8")
    assert rendered.index('"z"') < rendered.index('"城市"')
    assert "深圳" in rendered


def test_tool_reports_invalid_input_and_handles_json_lines_from_stdin():
    invalid = run_json_tool(input_text="{not json}")
    assert invalid.returncode != 0
    assert invalid.stdout == ""
    assert "line 1 column 2" in invalid.stderr

    lines = run_json_tool("--json-lines", "--compact", input_text='{"id": 1}\n{"id": 2}\n')
    assert lines.returncode == 0
    assert [json.loads(line) for line in lines.stdout.splitlines()] == [
        {"id": 1},
        {"id": 2},
    ]
