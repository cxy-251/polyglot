"""128｜``python -m zipfile`` 的创建、列出、校验与提取工作流。

标准库提供轻量命令行入口，适合脚本和人工检查：``--create`` 递归加入文件/目录，
``--list`` 打印目录，``--test`` 读取并校验成员，``--extract`` 展开归档。它没有应用级
资源限制或交互式冲突策略；不可信输入仍应由调用方先执行与 Python API 相同的预检。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.zipfile.cli python.zipfile.python-m-zipfile
# polyglot-covers: python.zipfile.cli-create python.zipfile.cli-recursive-directory
# polyglot-covers: python.zipfile.cli-list python.zipfile.cli-test
# polyglot-covers: python.zipfile.cli-extract python.zipfile.cli-invalid-usage
# polyglot-covers: python.zipfile.cli-short-options python.zipfile.cli-long-options
# polyglot-covers: python.zipfile.cli-exit-status python.zipfile.cli-security-boundary

import subprocess
import sys
import zipfile


def _run_zipfile_cli(*arguments):
    """统一捕获输出；实际测试只会由仓库 Docker 入口调用容器内解释器。"""

    return subprocess.run(
        [sys.executable, "-m", "zipfile", *map(str, arguments)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_create_command_adds_a_file_and_a_directory_tree(tmp_path):
    """输入的 basename 成为归档根名称；目录本身及 descendants 都会加入。"""

    source_file = tmp_path / "standalone.txt"
    source_file.write_text("standalone", encoding="utf-8")
    source_dir = tmp_path / "assets"
    source_dir.mkdir()
    (source_dir / "nested.txt").write_text("nested", encoding="utf-8")
    archive_path = tmp_path / "created.zip"

    result = _run_zipfile_cli(
        "--create",
        archive_path,
        source_file,
        source_dir,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == [
            "standalone.txt",
            "assets/",
            "assets/nested.txt",
        ]
        assert archive.read("standalone.txt") == b"standalone"
        assert archive.read("assets/nested.txt") == b"nested"


def test_list_and_test_commands_report_archive_state(tmp_path):
    """-l 是人读表格；-t 成功固定输出 Done testing，process status 才适合自动化判定。"""

    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("member.txt", b"content")

    listed = _run_zipfile_cli("-l", archive_path)
    tested = _run_zipfile_cli("--test", archive_path)

    assert listed.returncode == 0
    assert "File Name" in listed.stdout
    assert "member.txt" in listed.stdout
    assert tested.returncode == 0
    assert tested.stdout.strip() == "Done testing"


def test_extract_command_expands_members_to_the_target_directory(tmp_path):
    """-e 接收 archive 和 output_dir 两个位置参数；父目录按成员名自动创建。"""

    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nested/member.txt", b"content")
    output_dir = tmp_path / "output"

    result = _run_zipfile_cli("--extract", archive_path, output_dir)

    assert result.returncode == 0
    assert result.stdout == ""
    assert (output_dir / "nested" / "member.txt").read_bytes() == b"content"


def test_missing_operation_returns_a_nonzero_status_and_usage():
    """四个 operation 互斥且必须选一个；argparse 把错误写到 stderr。"""

    result = _run_zipfile_cli()

    assert result.returncode != 0
    assert result.stdout == ""
    assert "usage:" in result.stderr.lower()
