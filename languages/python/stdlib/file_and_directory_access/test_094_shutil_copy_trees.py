"""094｜``shutil`` 的 stream、文件与目录树复制工作流。

``copyfile`` 只复制内容，``copy`` 再复制 mode，``copy2`` 再尽力复制 stat metadata；
即便是最高层函数也不保证 owner、ACL、resource fork 等平台 metadata 完整。目录树操作还要
明确 symlink、已存在目标、忽略规则和失败清理策略，不能把默认值当作安全策略。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import io
import os
from pathlib import Path
import shutil
import stat

import pytest


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
