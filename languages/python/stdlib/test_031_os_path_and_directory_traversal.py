"""031｜``os.path``、``listdir``、``scandir`` 与 ``walk`` 工作流示例。

os.path 以 str/bytes 做平台路径操作，许多函数只做词法变换；listdir/scandir/walk
才枚举真实目录。本文件所有磁盘行为均限制在 pytest tmp_path，并显式排序枚举结果。

pathlib 的对象式接口已在 030 展示；本文件聚焦 os.PathLike、bytes path、DirEntry
和可裁剪目录遍历等低层接口。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.os python.stdlib.os.path python.os.PathLike
# polyglot-covers: python.os.fspath python.os.fsencode python.os.fsdecode
# polyglot-covers: python.os.path.join python.os.path.normpath
# polyglot-covers: python.os.path.abspath python.os.path.realpath python.os.path.relpath
# polyglot-covers: python.os.path.split python.os.path.splitext
# polyglot-covers: python.os.path.commonpath python.os.path.commonprefix
# polyglot-covers: python.os.path.expanduser python.os.path.expandvars
# polyglot-covers: python.os.path.exists python.os.path.lexists python.os.path.samefile
# polyglot-covers: python.os.listdir python.os.scandir python.os.DirEntry
# polyglot-covers: python.os.walk python.os.makedirs python.os.removedirs

import os
from pathlib import Path

import pytest


def test_fspath_fsencode_and_fsdecode_bridge_pathlike_and_os_representation():
    """PathLike.__fspath__ 只能返回 str/bytes；fsencode/fsdecode 使用文件系统编码。"""

    class ReportPath:
        def __init__(self, value):
            self.value = value

        def __fspath__(self):
            return self.value

    path = ReportPath("reports/咖啡.txt")

    assert os.fspath(path) == "reports/咖啡.txt"
    encoded = os.fsencode(path)
    assert isinstance(encoded, bytes)
    assert os.fsdecode(encoded) == "reports/咖啡.txt"
    assert os.fspath(Path("reports/items.txt")) == "reports/items.txt"

    class InvalidPath:
        def __fspath__(self):
            return 42

    with pytest.raises(TypeError, match="__fspath__"):
        os.fspath(InvalidPath())


def test_os_path_preserves_str_or_bytes_and_rejects_mixing_them():
    """同一次路径运算应选择文本路径或原始字节路径，返回类型随输入保持一致。"""

    assert os.path.join("/srv", "app") == "/srv/app"
    assert os.path.join(b"/srv", b"app") == b"/srv/app"
    assert isinstance(os.path.basename(b"/srv/app.txt"), bytes)

    with pytest.raises(TypeError, match="str.*bytes"):
        os.path.join("/srv", b"app")

    # 大多数应用优先使用 str；bytes path 主要用于必须无损处理不可解码文件名的边界。


def test_join_and_normpath_are_lexical_operations():
    """绝对片段重置前缀；normpath 折叠分隔符、`.` 和可消去的 `..`。"""

    assert os.path.join("/srv/app", "logs", "today.log") == (
        "/srv/app/logs/today.log"
    )
    assert os.path.join("/srv/app", "/etc", "config") == "/etc/config"
    assert os.path.normpath("/srv//app/../data/./items") == "/srv/data/items"
    assert os.path.normpath("") == "."

    # normpath 不查询 symlink，也不验证结果是否留在安全根目录，不能单独防路径穿越。


def test_abspath_uses_cwd_while_realpath_resolves_symlinks(tmp_path, monkeypatch):
    """abspath 组合 cwd 并规范化；realpath 进一步解析实际链接。"""

    real = tmp_path / "real"
    real.mkdir()
    target = real / "item.txt"
    target.write_text("data", encoding="ascii")
    (tmp_path / "alias").symlink_to(real.name, target_is_directory=True)
    monkeypatch.chdir(tmp_path)

    lexical = os.path.abspath("alias/item.txt")
    resolved = os.path.realpath("alias/item.txt")

    assert lexical == str(tmp_path / "alias" / "item.txt")
    assert resolved == str(target)
    assert lexical != resolved


def test_split_basename_dirname_splitdrive_and_splitext_are_component_tools():
    """拆分函数不访问磁盘，且 splitext 只拆最后一个扩展名。"""

    path = "/srv/app/archive.tar.gz"

    assert os.path.split(path) == ("/srv/app", "archive.tar.gz")
    assert os.path.dirname(path) == "/srv/app"
    assert os.path.basename(path) == "archive.tar.gz"
    assert os.path.splitext(path) == ("/srv/app/archive.tar", ".gz")
    assert os.path.splitdrive(path) == ("", path)

    assert os.path.basename("/srv/app/") == ""

    # Python basename 保留“末尾分隔符表示目录”的空名称语义，不等同于 Unix basename 命令。


def test_relpath_commonpath_and_commonprefix_answer_different_questions():
    """commonpath 按路径组件计算；commonprefix 只比较原始字符。"""

    assert os.path.relpath("/srv/app/logs", start="/srv/app") == "logs"
    assert os.path.relpath("/srv/data", start="/srv/app") == "../../data"

    paths = ["/usr/lib", "/usr/local"]
    assert os.path.commonpath(paths) == "/usr"
    assert os.path.commonprefix(paths) == "/usr/l"

    with pytest.raises(ValueError, match="absolute and relative"):
        os.path.commonpath(["/absolute", "relative"])

    # `/usr/l` 不是有效共同目录；权限/沙箱判断必须使用组件级 commonpath 后再校验。


def test_expanduser_and_expandvars_use_environment_without_validating_result(
    tmp_path,
    monkeypatch,
):
    """展开只替换已知标记，不创建路径，也不会拒绝未定义变量。"""

    fake_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("PROJECT", "demo")

    assert os.path.expanduser("~/docs") == str(fake_home / "docs")
    assert os.path.expandvars("$DATA_ROOT/${PROJECT}/$MISSING") == (
        f"{tmp_path}/data/demo/$MISSING"
    )

    assert not fake_home.exists()
    assert not (tmp_path / "data").exists()


def test_exists_lexists_and_link_predicates_distinguish_broken_symlink(tmp_path):
    """exists 跟随链接目标；lexists 只要求目录项本身存在。"""

    target = tmp_path / "target.txt"
    target.write_text("abc", encoding="ascii")
    live_link = tmp_path / "live.txt"
    live_link.symlink_to(target.name)
    broken_link = tmp_path / "broken.txt"
    broken_link.symlink_to("missing.txt")

    assert os.path.exists(target)
    assert os.path.isfile(target)
    assert not os.path.isdir(target)
    assert not os.path.islink(target)

    assert os.path.exists(live_link)
    assert os.path.lexists(live_link)
    assert os.path.islink(live_link)
    assert os.path.samefile(live_link, target)

    assert not os.path.exists(broken_link)
    assert os.path.lexists(broken_link)
    assert os.path.islink(broken_link)


def test_stat_convenience_functions_report_metadata_of_existing_path(tmp_path):
    """getsize/getmtime 等是 os.stat 字段的便捷入口，并会查询文件系统。"""

    path = tmp_path / "item.bin"
    path.write_bytes(b"abc")
    metadata = os.stat(path)

    assert os.path.getsize(path) == metadata.st_size == 3
    assert os.path.getmtime(path) == metadata.st_mtime
    assert os.path.getatime(path) == metadata.st_atime
    assert os.path.getctime(path) == metadata.st_ctime

    # Unix ctime 是 metadata change time，不是可移植的创建时间。


def test_listdir_returns_names_and_preserves_bytes_path_type(tmp_path):
    """listdir 返回目录内名称而非完整路径；bytes 输入产生 bytes 名称。"""

    (tmp_path / "b.txt").write_text("b", encoding="ascii")
    (tmp_path / "a.txt").write_text("a", encoding="ascii")
    (tmp_path / "folder").mkdir()

    assert sorted(os.listdir(tmp_path)) == ["a.txt", "b.txt", "folder"]
    assert sorted(os.listdir(os.fsencode(tmp_path))) == [
        b"a.txt",
        b"b.txt",
        b"folder",
    ]

    # 文件系统不保证返回顺序；还要访问条目属性时优先 scandir，避免重复 stat。


def test_scandir_direntry_combines_name_path_type_and_stat_queries(tmp_path):
    """DirEntry 携带枚举所得元数据，并按需提供 is_file/is_dir/stat。"""

    file_path = tmp_path / "item.txt"
    file_path.write_text("abc", encoding="ascii")
    directory = tmp_path / "folder"
    directory.mkdir()
    link = tmp_path / "item-link.txt"
    link.symlink_to(file_path.name)

    with os.scandir(tmp_path) as iterator:
        entries = {entry.name: entry for entry in iterator}

    assert sorted(entries) == ["folder", "item-link.txt", "item.txt"]

    item = entries["item.txt"]
    assert item.path == str(file_path)
    assert item.is_file()
    assert not item.is_dir()
    assert item.stat().st_size == 3

    folder = entries["folder"]
    assert folder.is_dir()
    assert not folder.is_file()

    link_entry = entries["item-link.txt"]
    assert link_entry.is_symlink()
    assert link_entry.is_file()
    assert not link_entry.is_file(follow_symlinks=False)

    # DirEntry 的部分结果会缓存；外部并发修改时不能把旧对象当实时事务快照。


def test_topdown_walk_can_prune_directories_by_mutating_dirnames(tmp_path):
    """topdown=True 时原地修改 dirnames 决定 walk 后续是否下降。"""

    keep = tmp_path / "keep"
    skip = tmp_path / "skip"
    (keep / "nested").mkdir(parents=True)
    skip.mkdir()
    (keep / "visible.txt").write_text("v", encoding="ascii")
    (keep / "nested" / "deep.txt").write_text("d", encoding="ascii")
    (skip / "secret.txt").write_text("s", encoding="ascii")

    visited = []
    for root, dirnames, filenames in os.walk(tmp_path, topdown=True):
        dirnames[:] = sorted(name for name in dirnames if name != "skip")
        filenames.sort()
        visited.append(
            (
                Path(root).relative_to(tmp_path).as_posix(),
                tuple(dirnames),
                tuple(filenames),
            )
        )

    assert visited == [
        (".", ("keep",), ()),
        ("keep", ("nested",), ("visible.txt",)),
        ("keep/nested", (), ("deep.txt",)),
    ]

    # 写 `dirnames = [...]` 只重绑定局部变量，不会裁剪 walk；必须使用 `dirnames[:] =`。


def test_walk_default_does_not_descend_into_directory_symlink(tmp_path):
    """followlinks=False 避免默认沿目录链接递归，但链接名仍可能出现在 dirnames。"""

    real = tmp_path / "real"
    real.mkdir()
    (real / "item.txt").write_text("data", encoding="ascii")
    alias = tmp_path / "alias"
    alias.symlink_to(real.name, target_is_directory=True)

    roots = []
    top_dirnames = None
    for root, dirnames, _ in os.walk(tmp_path):
        dirnames.sort()
        relative = Path(root).relative_to(tmp_path).as_posix()
        roots.append(relative)
        if relative == ".":
            top_dirnames = tuple(dirnames)

    assert top_dirnames == ("alias", "real")
    assert roots == [".", "real"]

    # followlinks=True 时 os.walk 不记录 visited；链接环需要调用者按 inode/realpath 防环。


def test_bottom_up_walk_supports_removing_children_before_parents(tmp_path):
    """topdown=False 先产出最深目录，适合递归清理。"""

    root = tmp_path / "delete-tree"
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    (root / "top.txt").write_text("top", encoding="ascii")
    (nested / "deep.txt").write_text("deep", encoding="ascii")

    visit_order = []
    for current, dirnames, filenames in os.walk(root, topdown=False):
        visit_order.append(Path(current).relative_to(root).as_posix())
        for filename in filenames:
            os.remove(os.path.join(current, filename))
        for dirname in dirnames:
            os.rmdir(os.path.join(current, dirname))

    assert visit_order[-1] == "."
    assert "a/b" in visit_order
    assert list(root.iterdir()) == []

    root.rmdir()
    assert not root.exists()


def test_makedirs_and_removedirs_create_and_prune_multiple_levels(tmp_path):
    """makedirs 创建祖先；removedirs 删除叶子后继续删除空祖先直到遇到非空目录。"""

    top = tmp_path / "one"
    nested = top / "two" / "three"

    os.makedirs(nested)
    assert nested.is_dir()

    with pytest.raises(FileExistsError):
        os.makedirs(nested)

    os.makedirs(nested, exist_ok=True)

    # 保留文件让 removedirs 在 top 停止；否则它会继续尝试删除所有空祖先。
    (top / "keep.txt").write_text("keep", encoding="ascii")
    os.removedirs(nested)

    assert top.is_dir()
    assert (top / "keep.txt").is_file()
    assert not (top / "two").exists()
