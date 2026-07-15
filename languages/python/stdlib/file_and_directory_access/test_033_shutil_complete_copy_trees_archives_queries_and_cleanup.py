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
import logging
from pathlib import Path, PurePosixPath, PureWindowsPath
import tarfile

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


# 094｜``shutil`` 的 stream、文件与目录树复制工作流。
#
# ``copyfile`` 只复制内容，``copy`` 再复制 mode，``copy2`` 再尽力复制 stat metadata；
# 即便是最高层函数也不保证 owner、ACL、resource fork 等平台 metadata 完整。目录树操作还要
# 明确 symlink、已存在目标、忽略规则和失败清理策略，不能把默认值当作安全策略。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.shutil.copyfileobj python.shutil.copyfileobj.current-position
# polyglot-covers: python.shutil.copyfileobj.length python.shutil.copyfileobj.no-flush
# polyglot-covers: python.shutil.copyfile python.shutil.content-only python.shutil.overwrite
# polyglot-covers: python.shutil.SameFileError python.shutil.hard-link-identity
# polyglot-covers: python.shutil.copyfile.follow-symlinks
# polyglot-covers: python.shutil.copymode python.shutil.copystat python.shutil.metadata-limits
# polyglot-covers: python.shutil.copy python.shutil.copy.destination-directory
# polyglot-covers: python.shutil.copy2 python.shutil.copy2.best-effort-metadata
# polyglot-covers: python.shutil.copytree python.shutil.copytree.nested
# polyglot-covers: python.shutil.ignore-patterns python.shutil.copytree.ignore-callback
# polyglot-covers: python.shutil.copytree.custom-copy-function
# polyglot-covers: python.shutil.copytree.symlinks python.shutil.copytree.dereference-links
# polyglot-covers: python.shutil.copytree.dangling-symlinks python.shutil.Error.aggregate
# polyglot-covers: python.shutil.copytree.dirs-exist-ok python.shutil.copytree.merge-overwrite
# polyglot-covers: python.shutil.rmtree python.shutil.rmtree.ignore-errors
# polyglot-covers: python.shutil.rmtree.onerror python.shutil.rmtree.avoids-symlink-attacks
# polyglot-covers: python.shutil.rmtree.symlink-refusal
# polyglot-covers: python.shutil.move python.shutil.move.destination-directory
# polyglot-covers: python.shutil.move.copy-function-fallback




class FlushTrackingBytesIO(io.BytesIO):
    """只记录当前主题需要的 flush protocol，不模拟完整磁盘文件。"""

    def __init__(self):
        super().__init__()
        self.flush_calls = 0

    def flush(self):
        self.flush_calls += 1
        return super().flush()


def test_copyfileobj_starts_at_the_current_source_position_and_does_not_flush():
    """它复制“剩余 stream”而非自动 rewind；返回后是否 flush 由调用方负责。"""

    source = io.BytesIO(b"header:payload")
    source.seek(len(b"header:"))
    destination = FlushTrackingBytesIO()

    result = shutil.copyfileobj(source, destination, length=3)

    assert result is None
    assert destination.getvalue() == b"payload"
    assert destination.flush_calls == 0


def test_copyfileobj_negative_length_requests_one_unbounded_read():
    """负 length 省去 chunk loop，却可能一次把余下内容读入内存，不适合不受控大输入。"""

    source = io.BytesIO(b"0123456789")
    destination = io.BytesIO()

    shutil.copyfileobj(source, destination, length=-1)

    assert destination.getvalue() == b"0123456789"


def test_copyfile_copies_content_overwrites_target_and_returns_destination(tmp_path):
    """dst 必须是完整文件名；已存在 regular file 会被截断替换。"""

    source = tmp_path / "source.bin"
    destination = tmp_path / "destination.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old content that is longer")

    returned = shutil.copyfile(source, destination)

    assert returned == destination
    assert destination.read_bytes() == b"new"


def test_copyfile_rejects_two_paths_to_the_same_underlying_file(tmp_path):
    """hard link 文本不同但 identity 相同，覆盖它等价于覆盖 source 自身。"""

    source = tmp_path / "source"
    alias = tmp_path / "alias"
    source.write_text("data", encoding="utf-8")
    alias.hardlink_to(source)

    with pytest.raises(shutil.SameFileError):
        shutil.copyfile(source, alias)

    assert issubclass(shutil.SameFileError, shutil.Error)


def test_copyfile_follow_symlinks_false_copies_the_link_not_its_target(tmp_path):
    """默认会 dereference；False 才在目标位置新建一个指向同样文本 target 的 symlink。"""

    target = tmp_path / "target.txt"
    source_link = tmp_path / "source-link"
    copied_link = tmp_path / "copied-link"
    target.write_text("target", encoding="utf-8")
    source_link.symlink_to("target.txt")

    shutil.copyfile(source_link, copied_link, follow_symlinks=False)

    assert copied_link.is_symlink()
    assert os.readlink(copied_link) == "target.txt"


def test_copymode_changes_permission_bits_without_touching_content(tmp_path):
    """copymode 只复制 permission bits；内容、owner 和其他 stat 字段不在契约内。"""

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("source", encoding="utf-8")
    destination.write_text("destination", encoding="utf-8")
    source.chmod(0o640)
    destination.chmod(0o700)

    returned = shutil.copymode(source, destination)

    assert returned is None
    assert stat.S_IMODE(destination.stat().st_mode) == 0o640
    assert destination.read_text(encoding="utf-8") == "destination"


def test_copystat_copies_mode_and_timestamps_but_not_content(tmp_path):
    """copystat 是 metadata 操作；用纳秒字段避免 float 时间比较损失精度。"""

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(b"source")
    destination.write_bytes(b"destination")
    source.chmod(0o604)
    timestamp_ns = 1_234_567_890_000_000_000
    os.utime(source, ns=(timestamp_ns, timestamp_ns))

    returned = shutil.copystat(source, destination)

    assert returned is None
    assert stat.S_IMODE(destination.stat().st_mode) == 0o604
    assert destination.stat().st_mtime_ns == source.stat().st_mtime_ns
    assert destination.read_bytes() == b"destination"


def test_copy_accepts_a_destination_directory_and_preserves_mode(tmp_path):
    """与 copyfile 不同，dst 是目录时会追加 source basename，并返回最终文件路径。"""

    source = tmp_path / "script.sh"
    destination_directory = tmp_path / "bin"
    source.write_text("run", encoding="utf-8")
    source.chmod(0o750)
    destination_directory.mkdir()

    returned = shutil.copy(source, destination_directory)
    copied = destination_directory / source.name

    assert Path(returned) == copied
    assert copied.read_text(encoding="utf-8") == "run"
    assert stat.S_IMODE(copied.stat().st_mode) == 0o750


def test_copy2_preserves_mtime_in_addition_to_content_and_mode(tmp_path):
    """copy2 调用 copystat 尽力保留 metadata；“尽力”不包含跨平台完整 ACL/owner 保真。"""

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(b"payload")
    source.chmod(0o620)
    timestamp_ns = 1_111_111_111_000_000_000
    os.utime(source, ns=(timestamp_ns, timestamp_ns))

    returned = shutil.copy2(source, destination)

    assert returned == destination
    assert destination.read_bytes() == b"payload"
    assert stat.S_IMODE(destination.stat().st_mode) == 0o620
    assert destination.stat().st_mtime_ns == source.stat().st_mtime_ns


def test_copytree_recursively_creates_the_destination_and_returns_it(tmp_path):
    """默认 dst 不存在；中间目录、文件内容和空目录一起复制。"""

    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "empty").mkdir()
    (source / "nested" / "item.txt").write_text("item", encoding="utf-8")
    destination = tmp_path / "outer" / "copied"

    returned = shutil.copytree(source, destination)

    assert returned == destination
    assert (destination / "nested" / "item.txt").read_text(encoding="utf-8") == "item"
    assert (destination / "empty").is_dir()


def test_copytree_existing_destination_requires_an_explicit_merge_policy(tmp_path):
    """默认拒绝已有 dst；dirs_exist_ok=True 合并目录、覆盖同名文件、保留额外文件。"""

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "shared.txt").write_text("new", encoding="utf-8")
    (source / "added.txt").write_text("added", encoding="utf-8")
    (destination / "shared.txt").write_text("old", encoding="utf-8")
    (destination / "kept.txt").write_text("kept", encoding="utf-8")

    with pytest.raises(FileExistsError):
        shutil.copytree(source, destination)

    shutil.copytree(source, destination, dirs_exist_ok=True)

    assert (destination / "shared.txt").read_text(encoding="utf-8") == "new"
    assert (destination / "added.txt").exists()
    assert (destination / "kept.txt").exists()


def test_ignore_patterns_filters_each_directory_by_basename(tmp_path):
    """pattern 匹配当前层 names，不是从 tree root 开始的完整相对路径。"""

    source = tmp_path / "source"
    (source / "package" / "__pycache__").mkdir(parents=True)
    (source / "package" / "module.py").write_text("code", encoding="utf-8")
    (source / "package" / "module.pyc").write_bytes(b"cache")
    (source / "package" / "__pycache__" / "module.pyc").write_bytes(b"cache")
    destination = tmp_path / "destination"

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("*.pyc", "__pycache__"),
    )

    assert (destination / "package" / "module.py").exists()
    assert not (destination / "package" / "module.pyc").exists()
    assert not (destination / "package" / "__pycache__").exists()


def test_copytree_ignore_callback_runs_once_per_visited_directory(tmp_path):
    """callback 收到 directory 与该层 os.listdir names，并返回应跳过的 basename 子集。"""

    source = tmp_path / "source"
    (source / "nested").mkdir(parents=True)
    (source / "public.txt").touch()
    (source / "secret.txt").touch()
    (source / "nested" / "child.txt").touch()
    visits = []

    def ignore_secret(directory, names):
        visits.append((Path(directory).relative_to(source), set(names)))
        return {"secret.txt"} & set(names)

    destination = tmp_path / "destination"
    shutil.copytree(source, destination, ignore=ignore_secret)

    assert (Path("."), {"nested", "public.txt", "secret.txt"}) in visits
    assert (Path("nested"), {"child.txt"}) in visits
    assert (destination / "public.txt").exists()
    assert not (destination / "secret.txt").exists()


def test_copytree_custom_copy_function_is_used_for_each_regular_file(tmp_path):
    """copy_function 允许选择 copy 而非 copy2 或增加观测；它必须接受 src/dst 并返回结果。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").touch()
    (source / "b.txt").touch()
    copied_names = []

    def recording_copy(src, dst):
        copied_names.append(Path(src).name)
        return shutil.copy(src, dst)

    destination = tmp_path / "destination"
    shutil.copytree(source, destination, copy_function=recording_copy)

    assert set(copied_names) == {"a.txt", "b.txt"}


def test_copytree_symlink_policy_chooses_link_or_target_content(tmp_path):
    """symlinks=True 保留 link；默认 False dereference 后创建普通文件。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "target.txt").write_text("payload", encoding="utf-8")
    (source / "alias.txt").symlink_to("target.txt")

    preserved = tmp_path / "preserved"
    dereferenced = tmp_path / "dereferenced"
    shutil.copytree(source, preserved, symlinks=True)
    shutil.copytree(source, dereferenced, symlinks=False)

    assert (preserved / "alias.txt").is_symlink()
    assert os.readlink(preserved / "alias.txt") == "target.txt"
    assert not (dereferenced / "alias.txt").is_symlink()
    assert (dereferenced / "alias.txt").read_text(encoding="utf-8") == "payload"


def test_copytree_aggregates_dangling_link_errors_unless_explicitly_ignored(tmp_path):
    """dereference broken link 时错误延迟汇总为三元组；ignore_dangling_symlinks 可跳过它。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "good.txt").touch()
    (source / "broken").symlink_to("missing")

    with pytest.raises(shutil.Error) as caught:
        shutil.copytree(source, tmp_path / "failed")

    failures = caught.value.args[0]
    assert all(len(failure) == 3 for failure in failures)
    assert any(Path(source_name).name == "broken" for source_name, _, _ in failures)

    ignored = tmp_path / "ignored"
    shutil.copytree(source, ignored, ignore_dangling_symlinks=True)
    assert (ignored / "good.txt").exists()
    assert not os.path.lexists(ignored / "broken")


def test_rmtree_removes_a_tree_but_refuses_a_directory_symlink(tmp_path):
    """rmtree 的输入必须是真目录；拒绝 symlink 可避免意图含糊的递归删除。"""

    target = tmp_path / "target"
    target.mkdir()
    (target / "important.txt").touch()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(OSError):
        shutil.rmtree(link)

    assert link.is_symlink()
    assert (target / "important.txt").exists()

    shutil.rmtree(target)
    assert not target.exists()


def test_rmtree_missing_path_error_can_be_ignored_or_observed(tmp_path):
    """ignore_errors 会吞掉所有删除错误；需要诊断或恢复时应使用三参数 onerror。"""

    missing = tmp_path / "missing"
    shutil.rmtree(missing, ignore_errors=True)
    observed = []

    def observe(function, path, exc_info):
        observed.append((function, Path(path), exc_info))

    shutil.rmtree(missing, onerror=observe)

    assert len(observed) == 1
    assert observed[0][1] == missing
    assert observed[0][2][0] is FileNotFoundError


def test_rmtree_reports_whether_fd_based_symlink_protection_is_available():
    """这是 implementation capability，不应假定所有平台都采用 attack-resistant 路径。"""

    assert type(shutil.rmtree.avoids_symlink_attacks) is bool


def test_move_into_an_existing_directory_returns_the_final_path(tmp_path):
    """dst 是目录时 source basename 会被追加；成功后旧 pathname 不再存在。"""

    source = tmp_path / "report.txt"
    destination_directory = tmp_path / "archive"
    source.write_text("report", encoding="utf-8")
    destination_directory.mkdir()

    returned = shutil.move(source, destination_directory)
    moved = destination_directory / "report.txt"

    assert Path(returned) == moved
    assert moved.read_text(encoding="utf-8") == "report"
    assert not source.exists()


def test_move_uses_copy_function_when_rename_cannot_cross_the_boundary(tmp_path, monkeypatch):
    """跨 filesystem 时先 copy 再删除；注入 rename 失败可演示公开 fallback 而不要求真实挂载点。"""

    source = tmp_path / "source.txt"
    destination = tmp_path / "destination.txt"
    source.write_text("payload", encoding="utf-8")
    calls = []

    def unavailable_rename(src, dst):
        raise OSError("simulated cross-device rename")

    def recording_copy(src, dst):
        calls.append((Path(src), Path(dst)))
        return shutil.copy2(src, dst)

    monkeypatch.setattr(shutil.os, "rename", unavailable_rename)

    returned = shutil.move(source, destination, copy_function=recording_copy)

    assert returned == destination
    assert calls == [(source, destination)]
    assert destination.read_text(encoding="utf-8") == "payload"
    assert not source.exists()


# 095｜``shutil`` 的归档、命令查找与环境查询。
#
# 高层归档 API 适合可信目录的打包与解包，但 extension 只负责选择 unpacker，不证明内容
# 安全；不可信 archive 必须先检查 member path，防止 absolute/``..`` 越过 extract_dir。
# 格式注册表是 process-global mutable state，扩展它时要用唯一名称并在 finally 中恢复。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.shutil.disk-usage python.shutil.disk-usage.namedtuple
# polyglot-covers: python.shutil.which python.shutil.which.path-order
# polyglot-covers: python.shutil.which.permission-mode python.shutil.which.direct-path
# polyglot-covers: python.shutil.which.environment-path python.shutil.which.bytes
# polyglot-covers: python.shutil.chown python.shutil.chown.argument-validation
# polyglot-covers: python.shutil.get-terminal-size python.shutil.terminal-environment
# polyglot-covers: python.shutil.get-terminal-size.fallback
# polyglot-covers: python.shutil.get-archive-formats python.shutil.get-unpack-formats
# polyglot-covers: python.shutil.make-archive python.shutil.archive-root-dir
# polyglot-covers: python.shutil.make-archive.base-dir python.shutil.archive-relative-members
# polyglot-covers: python.shutil.make-archive.zip python.shutil.unpack-archive
# polyglot-covers: python.shutil.make-archive.dry-run python.shutil.archive-logger
# polyglot-covers: python.shutil.unpack-archive.extension-detection
# polyglot-covers: python.shutil.unpack-archive.explicit-format
# polyglot-covers: python.shutil.unpack-archive.unknown-format python.shutil.ReadError
# polyglot-covers: python.shutil.unpack-archive.path-traversal python.archive.preinspection
# polyglot-covers: python.shutil.register-archive-format python.shutil.unregister-archive-format
# polyglot-covers: python.shutil.archive-extra-args python.shutil.archive-global-registry
# polyglot-covers: python.shutil.register-unpack-format python.shutil.unregister-unpack-format
# polyglot-covers: python.shutil.unpack-extra-args




def _make_executable(path, content="#!/bin/sh\nexit 0\n"):
    """测试只需要 which 的 permission contract，不真正执行创建出的文件。"""

    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _archive_name_is_relative_and_contained(name):
    """archive name 使用 POSIX slash，同时拒绝可能在 Windows 生效的 drive/UNC。"""

    posix_path = PurePosixPath(name)
    windows_path = PureWindowsPath(name)
    return (
        not posix_path.is_absolute()
        and ".." not in posix_path.parts
        and not windows_path.drive
    )


def _tar_member_passes_basic_data_only_policy(member):
    """除检查 entry name，还拒绝可再次跳转的 links 与 special device entries。"""

    return (
        _archive_name_is_relative_and_contained(member.name)
        and (member.isfile() or member.isdir())
    )


def test_disk_usage_returns_named_byte_counts_for_a_file_or_directory(tmp_path):
    """结果属于 containing filesystem，不是该文件自身占用量；属性均以 bytes 表示。"""

    file_path = tmp_path / "item.bin"
    file_path.write_bytes(b"small")

    for usage in (shutil.disk_usage(tmp_path), shutil.disk_usage(file_path)):
        assert usage.total > 0
        assert usage.used >= 0
        assert usage.free >= 0
        assert usage.total >= usage.used
        assert usage.total >= usage.free
        assert tuple(usage) == (usage.total, usage.used, usage.free)


def test_which_searches_path_entries_in_order_and_requires_executable_mode(tmp_path):
    """同名命令取 PATH 中第一个可执行 regular file，而不是最新或内容最匹配的文件。"""

    first_bin = tmp_path / "first"
    second_bin = tmp_path / "second"
    first_bin.mkdir()
    second_bin.mkdir()
    _make_executable(first_bin / "tool")
    _make_executable(second_bin / "tool")
    search_path = os.pathsep.join((str(first_bin), str(second_bin)))

    assert shutil.which("tool", path=search_path) == str(first_bin / "tool")


def test_which_mode_can_request_existence_without_execute_permission(tmp_path):
    """默认 mode 含 X_OK；若只是定位 data file，可显式传 F_OK，但通常不应把它当 command。"""

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    candidate = bin_directory / "tool"
    candidate.write_text("not executable", encoding="utf-8")
    candidate.chmod(0o644)

    assert shutil.which("tool", path=str(bin_directory)) is None
    assert shutil.which("tool", mode=os.F_OK, path=str(bin_directory)) == str(candidate)


def test_which_with_a_directory_component_checks_that_path_directly(tmp_path):
    """cmd 已含 separator 时不遍历 PATH；调用方仍得到 access mode 校验。"""

    explicit = tmp_path / "local" / "tool"
    explicit.parent.mkdir()
    _make_executable(explicit)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()

    assert shutil.which(str(explicit), path=str(unrelated)) == str(explicit)


def test_which_uses_environment_path_when_path_is_omitted(tmp_path, monkeypatch):
    """默认读取 process PATH；测试必须隔离该 global input，不能依赖容器已安装哪些命令。"""

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _make_executable(bin_directory / "polyglot-tool")
    monkeypatch.setenv("PATH", str(bin_directory))

    assert shutil.which("polyglot-tool") == str(bin_directory / "polyglot-tool")
    assert shutil.which("missing-tool") is None


def test_which_preserves_bytes_input_in_its_result(tmp_path):
    """bytes command 让 PATH 也跨入 filesystem bytes 域，结果不会隐式 decode。"""

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _make_executable(bin_directory / "tool")

    found = shutil.which(b"tool", path=os.fsencode(bin_directory))

    assert isinstance(found, bytes)
    assert found == os.fsencode(bin_directory / "tool")


def test_chown_requires_at_least_one_owner_or_group_argument(tmp_path):
    """不做真实 ownership 修改也能验证 API guard；名称/uid 的有效性取决于宿主账号数据库。"""

    path = tmp_path / "item"
    path.touch()

    with pytest.raises(ValueError):
        shutil.chown(path)


def test_terminal_size_prefers_positive_environment_dimensions(monkeypatch):
    """COLUMNS/LINES 可覆盖 terminal query，返回值仍是 os.terminal_size tuple subtype。"""

    monkeypatch.setenv("COLUMNS", "132")
    monkeypatch.setenv("LINES", "43")

    size = shutil.get_terminal_size(fallback=(1, 1))

    assert isinstance(size, os.terminal_size)
    assert (size.columns, size.lines) == (132, 43)


def test_terminal_size_uses_fallback_when_no_terminal_can_be_queried(monkeypatch):
    """CI 的 stdout 常不是 TTY；fallback 让 formatter 不依赖交互式 machine state。"""

    monkeypatch.delenv("COLUMNS", raising=False)
    monkeypatch.delenv("LINES", raising=False)

    def unavailable_terminal_size(*_args, **_kwargs):
        raise OSError("not attached to a terminal")

    monkeypatch.setattr(shutil.os, "get_terminal_size", unavailable_terminal_size)

    assert shutil.get_terminal_size(fallback=(100, 30)) == os.terminal_size((100, 30))


def test_default_archive_registries_expose_names_and_descriptions():
    """注册表适合 capability discovery；压缩格式是否存在仍受可选 compression module 影响。"""

    archive_formats = dict(shutil.get_archive_formats())
    unpack_formats = {name: (extensions, description) for name, extensions, description in shutil.get_unpack_formats()}

    assert "tar" in archive_formats
    assert archive_formats["tar"]
    assert ".tar" in unpack_formats["tar"][0]
    assert unpack_formats["tar"][1]


def test_make_tar_archive_uses_root_dir_and_relative_base_dir(tmp_path):
    """root_dir 是 filesystem 参照点；base_dir 是写入 archive 的 relative common prefix。"""

    root = tmp_path / "root"
    bundle = root / "bundle"
    bundle.mkdir(parents=True)
    (bundle / "data.txt").write_text("payload", encoding="utf-8")
    (root / "excluded.txt").write_text("excluded", encoding="utf-8")

    archive_name = shutil.make_archive(
        str(tmp_path / "snapshot"),
        "tar",
        root_dir=root,
        base_dir="bundle",
    )

    assert archive_name == str(tmp_path / "snapshot.tar")
    with tarfile.open(archive_name, mode="r") as archive:
        member_names = set(archive.getnames())

    assert "bundle" in member_names
    assert "bundle/data.txt" in member_names
    assert "excluded.txt" not in member_names


def test_make_zip_and_unpack_archive_form_a_high_level_round_trip(tmp_path):
    """filename extension 自动选择 unpacker；调用方仍要为 extract_dir 选择隔离位置。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "nested").mkdir()
    (source / "nested" / "item.txt").write_text("item", encoding="utf-8")
    archive_name = shutil.make_archive(
        str(tmp_path / "package"), "zip", root_dir=source
    )
    extracted = tmp_path / "extracted"

    returned = shutil.unpack_archive(archive_name, extracted)

    assert returned is None
    assert (extracted / "nested" / "item.txt").read_text(encoding="utf-8") == "item"


def test_unpack_archive_explicit_format_does_not_require_a_known_extension(tmp_path):
    """format 已由可信 metadata 给出时，archive pathname 可以没有注册 extension。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "item.txt").write_text("item", encoding="utf-8")
    generated = Path(
        shutil.make_archive(str(tmp_path / "generated"), "tar", root_dir=source)
    )
    opaque = generated.with_suffix(".bundle")
    generated.rename(opaque)
    destination = tmp_path / "destination"

    shutil.unpack_archive(opaque, destination, format="tar")

    assert (destination / "item.txt").read_text(encoding="utf-8") == "item"


def test_unpack_archive_distinguishes_unknown_name_from_unknown_explicit_format(tmp_path):
    """无法从 extension 推断时是 ReadError；显式给出未注册 format 属于 ValueError。"""

    archive = tmp_path / "payload.unknown"
    archive.write_bytes(b"not an archive")

    with pytest.raises(shutil.ReadError):
        shutil.unpack_archive(archive, tmp_path / "implicit")
    with pytest.raises(ValueError):
        shutil.unpack_archive(archive, tmp_path / "explicit", format="missing")


def test_make_archive_dry_run_reports_a_name_without_creating_the_archive(tmp_path):
    """dry_run 供部署预演；logger 接收计划，返回 pathname 不代表 artifact 已存在。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "item").touch()
    logger = logging.getLogger("polyglot.shutil.dry-run")

    archive_name = shutil.make_archive(
        str(tmp_path / "planned"),
        "tar",
        root_dir=source,
        dry_run=True,
        logger=logger,
    )

    assert archive_name == str(tmp_path / "planned.tar")
    assert not Path(archive_name).exists()


def test_untrusted_archive_members_are_rejected_before_unpacking(tmp_path):
    """extension 与 format 都不是 sandbox；data-only policy 还要拒绝 links 与 special files。"""

    archive_name = tmp_path / "untrusted.tar"
    payload = b"escaped"
    malicious_member = tarfile.TarInfo(name="../escape.txt")
    malicious_member.size = len(payload)
    malicious_link = tarfile.TarInfo(name="safe-looking-link")
    malicious_link.type = tarfile.SYMTYPE
    malicious_link.linkname = "../../escape.txt"
    with tarfile.open(archive_name, mode="w") as archive:
        archive.addfile(malicious_member, io.BytesIO(payload))
        archive.addfile(malicious_link)

    with tarfile.open(archive_name, mode="r") as archive:
        unsafe_names = [
            member.name
            for member in archive.getmembers()
            if not _tar_member_passes_basic_data_only_policy(member)
        ]

    assert unsafe_names == ["../escape.txt", "safe-looking-link"]
    assert not (tmp_path / "escape.txt").exists()
    # 发现不安全 member 后故意不调用 unpack_archive；“解包后再检查”已经太晚。


def test_custom_archive_format_receives_extra_args_and_is_always_unregistered(tmp_path):
    """自定义 archiver 修改 process-global registry；finally 防止后续测试或应用行为被污染。"""

    format_name = "polyglot-manifest"
    calls = []

    def make_manifest(base_name, base_dir, *, marker, **options):
        output = f"{base_name}.manifest"
        calls.append((base_dir, marker, options["dry_run"]))
        if not options["dry_run"]:
            Path(output).write_text(f"{base_dir}:{marker}", encoding="utf-8")
        return output

    shutil.register_archive_format(
        format_name,
        make_manifest,
        extra_args=(("marker", "v1"),),
        description="Polyglot manifest example",
    )
    try:
        source = tmp_path / "payload"
        source.mkdir()
        output = shutil.make_archive(
            str(tmp_path / "custom"),
            format_name,
            root_dir=tmp_path,
            base_dir="payload",
        )

        assert Path(output).read_text(encoding="utf-8") == "payload:v1"
        assert calls == [("payload", "v1", False)]
        assert dict(shutil.get_archive_formats())[format_name] == "Polyglot manifest example"
    finally:
        shutil.unregister_archive_format(format_name)

    assert format_name not in dict(shutil.get_archive_formats())


def test_custom_unpack_format_is_selected_by_extension_and_cleaned_up(tmp_path):
    """extensions 用于 dispatch，不用于内容验证；extra_args 可传固定 decoder 配置。"""

    format_name = "polyglot-bundle"
    extension = ".polyglot-bundle"
    calls = []

    def unpack_bundle(filename, extract_dir, *, marker):
        calls.append((Path(filename).name, marker))
        destination = Path(extract_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "content.txt").write_text(
            Path(filename).read_text(encoding="utf-8"), encoding="utf-8"
        )

    shutil.register_unpack_format(
        format_name,
        [extension],
        unpack_bundle,
        extra_args=(("marker", "v1"),),
        description="Polyglot bundle example",
    )
    try:
        archive = tmp_path / f"input{extension}"
        archive.write_text("payload", encoding="utf-8")
        destination = tmp_path / "destination"

        shutil.unpack_archive(archive, destination)

        assert (destination / "content.txt").read_text(encoding="utf-8") == "payload"
        assert calls == [(archive.name, "v1")]
        registered = {name: extensions for name, extensions, _ in shutil.get_unpack_formats()}
        assert registered[format_name] == [extension]
    finally:
        shutil.unregister_unpack_format(format_name)

    assert format_name not in {name for name, _, _ in shutil.get_unpack_formats()}
