"""033｜``shutil`` 的复制、目录树、删除、查找与归档工作流示例。

shutil 在 open/os/pathlib 之上组合高层文件操作。不同 copy 函数保留的 metadata
范围不同，copytree/rmtree 对 symlink 的策略也必须显式选择。本文件所有路径均位于
pytest tmp_path；归档只解包测试自己刚创建的可信内容。

内容基于 Python 3.10 shutil 文档；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.shutil python.shutil.copyfileobj
# polyglot-covers: python.shutil.copyfile python.shutil.copy python.shutil.copy2
# polyglot-covers: python.shutil.copymode python.shutil.copystat
# polyglot-covers: python.shutil.copytree python.shutil.ignore_patterns
# polyglot-covers: python.shutil.copytree.symlinks python.shutil.copytree.errors
# polyglot-covers: python.shutil.move python.shutil.rmtree
# polyglot-covers: python.shutil.disk_usage python.shutil.which
# polyglot-covers: python.shutil.make_archive python.shutil.unpack_archive
# polyglot-covers: python.shutil.get_terminal_size

import io
import os
from pathlib import Path
import shutil
import stat

import pytest


def test_copyfileobj_starts_at_current_position_and_length_is_buffer_size():
    """length 控制每次读取块大小，不是最多复制多少字节。"""

    source = io.BytesIO(b"prefix-payload")
    destination = io.BytesIO()
    source.seek(len(b"prefix-"))

    returned = shutil.copyfileobj(source, destination, length=3)

    assert returned is None
    assert destination.getvalue() == b"payload"
    assert source.read() == b""

    # copyfileobj 不 rewind；要复制整个输入必须由调用者先 seek(0)。


def test_copyfileobj_does_not_flush_destination():
    """复制完成只表示 write 已调用，持久化/网络刷新仍由流所有者负责。"""

    class RecordingDestination(io.BytesIO):
        def __init__(self):
            super().__init__()
            self.flush_count = 0

        def flush(self):
            self.flush_count += 1
            super().flush()

    destination = RecordingDestination()
    shutil.copyfileobj(io.BytesIO(b"data"), destination)

    assert destination.getvalue() == b"data"
    assert destination.flush_count == 0

    destination.flush()
    assert destination.flush_count == 1


def test_copyfile_copies_content_returns_destination_and_rejects_same_file(tmp_path):
    """copyfile 只负责文件内容，不复制 mode 等 metadata。"""

    source = tmp_path / "source.bin"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"payload")

    returned = shutil.copyfile(source, destination)

    assert Path(returned) == destination
    assert destination.read_bytes() == b"payload"

    with pytest.raises(shutil.SameFileError):
        shutil.copyfile(source, source)


def test_copymode_and_copystat_have_different_metadata_scope(tmp_path):
    """copymode 只复制权限位；copystat 再尽力复制时间等 stat metadata。"""

    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"
    source.write_text("source", encoding="ascii")
    destination.write_text("destination", encoding="ascii")

    source.chmod(0o640)
    destination.chmod(0o600)
    old_ns = 1_600_000_000_000_000_000
    os.utime(source, ns=(old_ns, old_ns))

    assert shutil.copymode(source, destination) is None
    assert stat.S_IMODE(destination.stat().st_mode) == 0o640
    assert destination.stat().st_mtime_ns != source.stat().st_mtime_ns

    assert shutil.copystat(source, destination) is None
    assert destination.stat().st_mtime_ns == source.stat().st_mtime_ns

    # owner/group、ACL、resource fork 等不能用这一断言推导为已完整复制。


def test_copy_preserves_mode_while_copy2_also_preserves_stat_times(tmp_path):
    """copy 等价于内容+copymode；copy2 等价于内容+尽力 copystat。"""

    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="ascii")
    source.chmod(0o640)
    old_ns = 1_600_000_000_000_000_000
    os.utime(source, ns=(old_ns, old_ns))

    copy_target = tmp_path / "copy.txt"
    copy2_target = tmp_path / "copy2.txt"

    assert Path(shutil.copy(source, copy_target)) == copy_target
    assert copy_target.read_text(encoding="ascii") == "payload"
    assert stat.S_IMODE(copy_target.stat().st_mode) == 0o640

    assert Path(shutil.copy2(source, copy2_target)) == copy2_target
    assert copy2_target.read_text(encoding="ascii") == "payload"
    assert stat.S_IMODE(copy2_target.stat().st_mode) == 0o640
    assert copy2_target.stat().st_mtime_ns == source.stat().st_mtime_ns


def test_copyfile_follow_symlinks_selects_target_content_or_link_object(tmp_path):
    """follow_symlinks=True 复制目标内容；False 尽量创建同样指向的链接。"""

    target = tmp_path / "target.txt"
    target.write_text("payload", encoding="ascii")
    source_link = tmp_path / "source-link.txt"
    source_link.symlink_to(target.name)

    followed = tmp_path / "followed.txt"
    shutil.copyfile(source_link, followed, follow_symlinks=True)
    assert followed.is_file()
    assert not followed.is_symlink()
    assert followed.read_text(encoding="ascii") == "payload"

    copied_link = tmp_path / "copied-link.txt"
    shutil.copyfile(source_link, copied_link, follow_symlinks=False)
    assert copied_link.is_symlink()
    assert os.readlink(copied_link) == target.name


def test_copytree_recursively_copies_and_ignore_patterns_filters_names(tmp_path):
    """ignore callable 每层返回要跳过的名称；ignore_patterns 提供 glob 便捷形式。"""

    source = tmp_path / "source"
    (source / "package" / "__pycache__").mkdir(parents=True)
    (source / "package" / "module.py").write_text("code", encoding="ascii")
    (source / "package" / "notes.tmp").write_text("tmp", encoding="ascii")
    (source / "package" / "__pycache__" / "module.pyc").write_bytes(b"cache")

    destination = tmp_path / "destination"
    returned = shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("*.tmp", "__pycache__"),
    )

    assert Path(returned) == destination
    assert (destination / "package" / "module.py").is_file()
    assert not (destination / "package" / "notes.tmp").exists()
    assert not (destination / "package" / "__pycache__").exists()


def test_copytree_custom_ignore_receives_directory_and_names(tmp_path):
    """自定义 ignore 可按目录上下文决定排除项，返回名称集合而非完整路径。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "public.txt").write_text("public", encoding="ascii")
    (source / "secret.txt").write_text("secret", encoding="ascii")
    calls = []

    def ignore_secret(directory, names):
        calls.append((Path(directory), tuple(sorted(names))))
        return {name for name in names if name.startswith("secret")}

    destination = tmp_path / "destination"
    shutil.copytree(source, destination, ignore=ignore_secret)

    assert calls == [(source, ("public.txt", "secret.txt"))]
    assert (destination / "public.txt").is_file()
    assert not (destination / "secret.txt").exists()


def test_copytree_existing_destination_needs_dirs_exist_ok(tmp_path):
    """默认要求新目标；dirs_exist_ok=True 合并目录且源同名文件获胜。"""

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "shared.txt").write_text("new", encoding="ascii")
    (destination / "shared.txt").write_text("old", encoding="ascii")
    (destination / "destination-only.txt").write_text("keep", encoding="ascii")

    with pytest.raises(FileExistsError):
        shutil.copytree(source, destination)

    returned = shutil.copytree(source, destination, dirs_exist_ok=True)

    assert Path(returned) == destination
    assert (destination / "shared.txt").read_text(encoding="ascii") == "new"
    assert (destination / "destination-only.txt").read_text(
        encoding="ascii"
    ) == "keep"


def test_copytree_symlinks_true_preserves_live_and_broken_links(tmp_path):
    """symlinks=True 复制链接目录项本身，不要求目标存在。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "target.txt").write_text("payload", encoding="ascii")
    (source / "live.txt").symlink_to("target.txt")
    (source / "broken.txt").symlink_to("missing.txt")

    destination = tmp_path / "destination"
    shutil.copytree(source, destination, symlinks=True)

    assert (destination / "live.txt").is_symlink()
    assert os.readlink(destination / "live.txt") == "target.txt"
    assert (destination / "broken.txt").is_symlink()
    assert os.readlink(destination / "broken.txt") == "missing.txt"


def test_copytree_can_ignore_dangling_links_or_report_aggregated_error(tmp_path):
    """跟随链接复制时，broken symlink 可选择跳过或汇总为 shutil.Error。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "regular.txt").write_text("regular", encoding="ascii")
    (source / "broken.txt").symlink_to("missing.txt")

    ignored_destination = tmp_path / "ignored"
    shutil.copytree(
        source,
        ignored_destination,
        symlinks=False,
        ignore_dangling_symlinks=True,
    )
    assert (ignored_destination / "regular.txt").is_file()
    assert not os.path.lexists(ignored_destination / "broken.txt")

    error_destination = tmp_path / "error-copy"
    with pytest.raises(shutil.Error) as captured:
        shutil.copytree(source, error_destination, symlinks=False)

    errors = captured.value.args[0]
    assert any("broken.txt" in source_name for source_name, _, _ in errors)


def test_move_handles_exact_destination_and_existing_directory(tmp_path):
    """目标是目录时把源放入其中；目标是新路径时完成重命名/移动。"""

    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="ascii")
    renamed = tmp_path / "renamed.txt"

    returned = shutil.move(source, renamed)
    assert Path(returned) == renamed
    assert not source.exists()
    assert renamed.read_text(encoding="ascii") == "payload"

    directory = tmp_path / "archive"
    directory.mkdir()
    returned = shutil.move(renamed, directory)

    nested = directory / renamed.name
    assert Path(returned) == nested
    assert nested.read_text(encoding="ascii") == "payload"

    # 跨文件系统时 move 可能退化为复制后删除，原子性/metadata 语义与 rename 不同。


def test_rmtree_removes_tree_and_refuses_symbolic_link_root(tmp_path):
    """rmtree 递归删除真实目录树，但不会把目录 symlink 当树根跟随。"""

    tree = tmp_path / "tree"
    (tree / "nested").mkdir(parents=True)
    (tree / "nested" / "item.txt").write_text("data", encoding="ascii")

    assert shutil.rmtree(tree) is None
    assert not tree.exists()

    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="ascii")
    link = tmp_path / "target-link"
    link.symlink_to(target.name, target_is_directory=True)

    with pytest.raises(OSError):
        shutil.rmtree(link)

    assert link.is_symlink()
    assert (target / "keep.txt").is_file()


def test_rmtree_missing_path_can_be_ignored_or_reported_to_onerror(tmp_path):
    """ignore_errors 丢弃异常；onerror 接收失败函数、路径和 exc_info。"""

    missing = tmp_path / "missing"

    assert shutil.rmtree(missing, ignore_errors=True) is None

    calls = []

    def record_error(function, path, exc_info):
        calls.append((function, Path(path), exc_info[0]))

    assert shutil.rmtree(missing, onerror=record_error) is None
    assert len(calls) == 1
    assert calls[0][1] == missing
    assert issubclass(calls[0][2], FileNotFoundError)
    assert isinstance(shutil.rmtree.avoids_symlink_attacks, bool)

    # onerror 返回即表示调用者选择继续；不要为“清理成功”而吞掉未知权限/磁盘错误。


def test_disk_usage_reports_named_capacity_fields_without_assuming_no_reserve(tmp_path):
    """total/used/free 来自文件系统统计，保留块可能让 used+free 小于 total。"""

    usage = shutil.disk_usage(tmp_path)

    assert usage.total > 0
    assert 0 <= usage.used <= usage.total
    assert 0 <= usage.free <= usage.total
    assert usage.used + usage.free <= usage.total
    assert tuple(usage) == (usage.total, usage.used, usage.free)


def test_which_searches_explicit_path_for_executable_file(tmp_path, monkeypatch):
    """which 按 PATH 和 mode 查找；测试只提供自己创建的目录。"""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "demo-tool"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
    executable.chmod(0o755)
    non_executable = bin_dir / "data-file"
    non_executable.write_text("data", encoding="ascii")
    non_executable.chmod(0o644)
    monkeypatch.setenv("PATH", str(bin_dir))

    assert shutil.which("demo-tool") == str(executable)
    assert shutil.which("data-file") is None
    assert shutil.which("missing") is None

    # 不显式控制 PATH 时，结果取决于进程环境，不能作为可重现测试断言。


def test_make_and_unpack_archive_round_trip_trusted_tree(tmp_path):
    """make_archive 返回归档路径；unpack_archive 按扩展名选择已注册解包器。"""

    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "root.txt").write_text("root", encoding="ascii")
    (source / "nested" / "item.txt").write_text("item", encoding="ascii")

    archive_base = tmp_path / "backup"
    archive_name = shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=source,
    )
    archive = Path(archive_name)

    assert archive == archive_base.with_suffix(".zip")
    assert archive.is_file()

    destination = tmp_path / "unpacked"
    shutil.unpack_archive(archive, destination)

    assert (destination / "root.txt").read_text(encoding="ascii") == "root"
    assert (destination / "nested" / "item.txt").read_text(
        encoding="ascii"
    ) == "item"

    # Python 3.10 不应直接解包不可信归档；成员名可尝试越过目标目录。


def test_archive_format_registries_describe_available_handlers():
    """格式注册表返回 (name, description) 等公开信息，不应硬编码完整平台列表。"""

    archive_formats = dict(shutil.get_archive_formats())
    unpack_formats = {name for name, _, _ in shutil.get_unpack_formats()}

    assert "zip" in archive_formats
    assert "gztar" in archive_formats
    assert "zip" in unpack_formats


def test_get_terminal_size_uses_environment_then_fallback(monkeypatch):
    """COLUMNS/LINES 优先；无法查询终端且无环境值时使用 fallback。"""

    def unavailable(_descriptor):
        raise OSError("not a terminal")

    monkeypatch.setattr(os, "get_terminal_size", unavailable)
    monkeypatch.delenv("COLUMNS", raising=False)
    monkeypatch.delenv("LINES", raising=False)

    assert shutil.get_terminal_size(fallback=(80, 24)) == os.terminal_size((80, 24))

    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.setenv("LINES", "40")
    assert shutil.get_terminal_size(fallback=(80, 24)) == os.terminal_size((120, 40))
