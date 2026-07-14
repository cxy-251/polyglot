"""135｜``python -m tarfile`` 创建、列出、校验、过滤解压与退出状态。

CLI 根据目标 suffix 选择 gzip/bz2/xz，``--verbose`` 控制人读反馈，``--filter`` 只对解压
有效。它适合轻量脚本，不替代应用级资源预算。测试通过 ``sys.executable`` 调用相同容器
解释器；宿主机仍只使用仓库统一 Docker 入口。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tarfile.cli python.tarfile.python-m-tarfile
# polyglot-covers: python.tarfile.cli-create python.tarfile.cli-suffix-compression
# polyglot-covers: python.tarfile.cli-list python.tarfile.cli-test
# polyglot-covers: python.tarfile.cli-extract python.tarfile.cli-filter
# polyglot-covers: python.tarfile.cli-verbose python.tarfile.cli-invalid-usage
# polyglot-covers: python.tarfile.cli-exit-status python.tarfile.cli-security-boundary

import io
import subprocess
import sys
import tarfile


def _run_tarfile_cli(*arguments, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "tarfile", *map(str, arguments)],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_create_uses_suffix_compression_and_adds_directory_tree(tmp_path):
    """CLI 用 output extension 选择压缩；在 cwd 传相对 source 避免归档本机绝对前缀。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "member.txt").write_text("content", encoding="utf-8")

    result = _run_tarfile_cli(
        "--create",
        "created.tar.gz",
        "source",
        cwd=tmp_path,
    )

    archive_path = tmp_path / "created.tar.gz"
    assert result.returncode == 0
    assert result.stdout == ""
    assert archive_path.read_bytes().startswith(b"\x1f\x8b")
    with tarfile.open(archive_path, "r:*") as archive:
        assert archive.getnames() == ["source", "source/member.txt"]
        member = archive.extractfile("source/member.txt")
        assert member is not None
        assert member.read() == b"content"


def test_list_and_verbose_test_commands_report_archive_state(tmp_path):
    """list 默认只输出名称；test 只有 -v 时打印成功说明，status 始终是自动化依据。"""

    archive_path = tmp_path / "sample.tar"
    with tarfile.open(archive_path, "w:") as archive:
        archive.addfile(tarfile.TarInfo("member.txt"))

    listed = _run_tarfile_cli("--list", archive_path)
    tested = _run_tarfile_cli("--test", archive_path)
    verbose_test = _run_tarfile_cli("--verbose", "--test", archive_path)

    assert listed.returncode == 0
    assert listed.stdout.strip() == "member.txt"
    assert tested.returncode == 0
    assert tested.stdout == ""
    assert verbose_test.returncode == 0
    assert "is a tar archive" in verbose_test.stdout


def test_extract_with_data_filter_writes_safe_members(tmp_path):
    """--filter data 把命令行入口放到与 API 相同的安全 profile 下。"""

    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")
    archive_path = tmp_path / "sample.tar"
    with tarfile.open(archive_path, "w:") as archive:
        archive.add(source, arcname="nested/source.txt")
    destination = tmp_path / "output"

    result = _run_tarfile_cli(
        "--extract",
        archive_path,
        destination,
        "--filter",
        "data",
    )

    assert result.returncode == 0
    assert (destination / "nested" / "source.txt").read_text(encoding="utf-8") == "content"


def test_data_filter_causes_nonzero_exit_for_a_traversal_member(tmp_path):
    """filter exception 使 process 失败且不写越界成员；CLI 不负责吞掉安全错误。"""

    archive_path = tmp_path / "unsafe.tar"
    info = tarfile.TarInfo("../outside.txt")
    info.size = len(b"outside")

    with tarfile.open(archive_path, "w:") as archive:
        archive.addfile(info, io.BytesIO(b"outside"))
    destination = tmp_path / "output"

    result = _run_tarfile_cli(
        "--extract",
        archive_path,
        destination,
        "--filter",
        "data",
    )

    assert result.returncode != 0
    assert not (tmp_path / "outside.txt").exists()


def test_filter_option_is_rejected_for_non_extraction_operation(tmp_path):
    """--filter 不是 create/list/test 的通用开关，错误组合返回非零状态。"""

    archive_path = tmp_path / "sample.tar"
    with tarfile.open(archive_path, "w:"):
        pass

    result = _run_tarfile_cli("--filter", "data", "--list", archive_path)

    assert result.returncode != 0
    assert "only valid for extraction" in result.stderr


def test_missing_operation_returns_usage_error():
    """create/extract/list/test 属于 required mutually-exclusive group。"""

    result = _run_tarfile_cli()

    assert result.returncode != 0
    assert "usage:" in result.stderr.lower()
