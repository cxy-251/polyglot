"""031｜``os.path``、``listdir``、``scandir`` 与 ``walk`` 工作流示例。

os.path 以 str/bytes 做平台路径操作，许多函数只做词法变换；listdir/scandir/walk
才枚举真实目录。本文件所有磁盘行为均限制在 pytest tmp_path，并显式排序枚举结果。

pathlib 的对象式接口已在 030 展示；本文件聚焦 os.PathLike、bytes path、DirEntry
和可裁剪目录遍历等低层接口。
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
import ntpath
import posixpath

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
    assert os.path.relpath("/srv/data", start="/srv/app") == "../data"

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


# ``os.path`` flavour、词法处理与文件 identity。
#
# os.path 绑定宿主 flavour；需要离线处理固定格式时可显式用 posixpath/ntpath。多数函数
# 只做字符串计算，不展开 shell 变量、不访问磁盘，也不能用 normpath 代替 symlink-aware
# 安全校验。samefile/sameopenfile/samestat 才按 device/inode 判断真实文件 identity。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.os.path python.posixpath python.ntpath
# polyglot-covers: python.os.pathlike-input python.os.path-str-bytes-consistency
# polyglot-covers: python.os.path.abspath python.os.path.cwd-dependency
# polyglot-covers: python.os.path.basename python.os.path.dirname python.os.path.split
# polyglot-covers: python.os.path.commonpath python.os.path.commonprefix
# polyglot-covers: python.os.path.security-prefix
# polyglot-covers: python.os.path.exists python.os.path.open-file-descriptor
# polyglot-covers: python.os.path.lexists python.os.path.broken-symlink
# polyglot-covers: python.os.path.expanduser python.os.path.expandvars
# polyglot-covers: python.os.path.explicit-expansion
# polyglot-covers: python.os.path.getsize python.os.path.getatime
# polyglot-covers: python.os.path.getmtime python.os.path.getctime
# polyglot-covers: python.os.path.isabs python.os.path.isfile
# polyglot-covers: python.os.path.isdir python.os.path.islink
# polyglot-covers: python.os.path.ismount python.os.path.join
# polyglot-covers: python.os.path.normcase python.os.path.normpath
# polyglot-covers: python.os.path.symlink-normalization-trap
# polyglot-covers: python.os.path.realpath python.os.path.python310-realpath-strict
# polyglot-covers: python.os.path.relpath python.os.path.lexical-relpath
# polyglot-covers: python.os.path.samefile python.os.path.sameopenfile python.os.path.samestat
# polyglot-covers: python.os.path.splitdrive python.os.path.splitext
# polyglot-covers: python.os.path.leading-dot-extension
# polyglot-covers: python.os.path.supports_unicode_filenames




class DomainPath:
    """os.path 接受返回 str 或 bytes 的 PathLike，而不要求 pathlib 类型。"""

    def __init__(self, value):
        self.value = value

    def __fspath__(self):
        return self.value


def test_os_path_is_the_native_module_while_explicit_flavours_are_portable():
    """os.path 始终适合本机路径；posixpath/ntpath 可在另一系统上做纯格式计算。"""

    assert os.path is (posixpath if os.name == "posix" else ntpath)
    assert posixpath.join("/srv", "app", "data") == "/srv/app/data"
    assert ntpath.join("c:\\srv", "app", "data") == "c:\\srv\\app\\data"


def test_path_functions_accept_pathlike_and_preserve_str_or_bytes_results():
    """输入路径返回值保持文本/bytes 域；同一次调用不能混用两种表示。"""

    assert posixpath.basename(DomainPath("/srv/data.txt")) == "data.txt"
    assert posixpath.basename(DomainPath(b"/srv/data.txt")) == b"data.txt"
    assert posixpath.join(b"/srv", b"data") == b"/srv/data"

    with pytest.raises(TypeError):
        posixpath.join("/srv", b"data")


def test_path_functions_do_not_implicitly_expand_shell_syntax():
    """``~``、``$VAR`` 与 glob metacharacters 都只是普通字符，必须调用对应显式函数。"""

    raw = "~/data/$PROJECT/*.txt"

    assert posixpath.normpath(raw) == raw
    assert posixpath.basename(raw) == "*.txt"


def test_abspath_combines_cwd_and_normpath_without_resolving_symlinks(tmp_path, monkeypatch):
    """abspath 通常等价于 normpath(join(cwd,path))，只建立 absolute lexical 文本。"""

    monkeypatch.chdir(tmp_path)

    assert os.path.abspath("folder/../item.txt") == str(tmp_path / "item.txt")


def test_split_basename_and_dirname_preserve_trailing_separator_semantics():
    """以 slash 结尾表示最后 component 为空，所以 Python basename 与 Unix 命令结果不同。"""

    path = "/srv/app/"

    assert posixpath.split(path) == ("/srv/app", "")
    assert posixpath.dirname(path) == "/srv/app"
    assert posixpath.basename(path) == ""
    assert posixpath.split("filename") == ("", "filename")
    assert posixpath.split("") == ("", "")


def test_commonpath_uses_components_while_commonprefix_uses_characters():
    """commonprefix('/usr/lib','/usr/local') 得到无效目录 ``/usr/l``，安全边界应使用 commonpath。"""

    paths = ["/usr/lib", "/usr/local"]

    assert posixpath.commonprefix(paths) == "/usr/l"
    assert posixpath.commonpath(paths) == "/usr"


def test_commonpath_validates_empty_mixed_and_cross_drive_inputs():
    """component 算法要求兼容的 absolute/relative 与 drive 域；字符前缀函数没有这些保护。"""

    with pytest.raises(ValueError):
        posixpath.commonpath([])
    with pytest.raises(ValueError):
        posixpath.commonpath(["/absolute", "relative"])
    with pytest.raises(ValueError):
        ntpath.commonpath(["c:\\data", "d:\\data"])

    assert posixpath.commonprefix([]) == ""


def test_exists_accepts_an_open_file_descriptor_and_changes_after_close(tmp_path):
    """整数参数被解释为 file descriptor 而非路径字符；close 后同一 fd 通常不再有效。"""

    path = tmp_path / "descriptor.txt"
    path.touch()
    descriptor = os.open(path, os.O_RDONLY)
    try:
        assert os.path.exists(descriptor) is True
    finally:
        os.close(descriptor)

    assert os.path.exists(descriptor) is False


def test_exists_and_lexists_differ_for_a_broken_symlink(tmp_path):
    """exists 跟随 target，lexists 只检查 link directory entry。"""

    link = tmp_path / "broken"
    link.symlink_to("missing")

    assert os.path.exists(link) is False
    assert os.path.lexists(link) is True
    assert os.path.islink(link) is True


def test_expanduser_and_expandvars_are_explicit_and_leave_unknowns_unchanged(tmp_path, monkeypatch):
    """展开只替换已知标记，不验证或创建结果路径；不存在变量保留原文本。"""

    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PROJECT", "polyglot")

    assert posixpath.expanduser("~/docs") == str(home / "docs")
    assert posixpath.expandvars("$PROJECT/${MISSING}/data") == "polyglot/${MISSING}/data"
    assert home.exists() is False


def test_metadata_convenience_functions_match_stat_fields(tmp_path):
    """ctime 在 Unix 是 metadata change time、在 Windows 才常是 creation time，不应跨平台误命名。"""

    path = tmp_path / "data.bin"
    path.write_bytes(b"abc")
    metadata = path.stat()

    assert os.path.getsize(path) == metadata.st_size == 3
    assert os.path.getatime(path) == metadata.st_atime
    assert os.path.getmtime(path) == metadata.st_mtime
    assert os.path.getctime(path) == metadata.st_ctime


def test_isabs_follows_the_selected_path_flavour():
    """POSIX 只需 leading slash；Windows 同时区分 rooted、drive-relative 与 drive+root。"""

    assert posixpath.isabs("/srv/data") is True
    assert posixpath.isabs("srv/data") is False
    assert ntpath.isabs("c:\\data") is True
    assert ntpath.isabs("c:data") is False


def test_file_directory_and_link_predicates_can_overlap_for_symlinks(tmp_path):
    """isfile/isdir 跟随 target，islink 检查 link 本身，因此 link 可同时满足两类 predicate。"""

    file_target = tmp_path / "file.txt"
    directory_target = tmp_path / "folder"
    file_target.touch()
    directory_target.mkdir()
    file_link = tmp_path / "file-link"
    directory_link = tmp_path / "dir-link"
    file_link.symlink_to(file_target)
    directory_link.symlink_to(directory_target, target_is_directory=True)

    assert os.path.islink(file_link) and os.path.isfile(file_link)
    assert os.path.islink(directory_link) and os.path.isdir(directory_link)
    assert not os.path.isdir(file_link)
    assert not os.path.isfile(directory_link)


def test_filesystem_root_is_a_mount_point_but_regular_children_are_not_assumed(tmp_path):
    """根的 parent 与自身同 inode，按定义是 mount；临时目录是否另挂载取决于环境，不硬断言。"""

    assert os.path.ismount(os.path.abspath(os.sep)) is True
    assert isinstance(os.path.ismount(tmp_path), bool)


def test_join_reset_rules_are_flavour_specific():
    """POSIX absolute segment 清空前缀；Windows rooted segment 保留 drive，新 drive 则替换。"""

    assert posixpath.join("/srv/app", "logs", "today.log") == "/srv/app/logs/today.log"
    assert posixpath.join("/srv/app", "/etc", "config") == "/etc/config"
    assert ntpath.join("c:\\Windows", "\\Program Files") == "c:\\Program Files"
    assert ntpath.join("c:\\Windows", "d:\\Data") == "d:\\Data"
    assert ntpath.join("c:", "foo") == "c:foo"


def test_normcase_is_noop_on_posix_and_casefolds_windows_paths():
    """normcase 不判断磁盘实际大小写；它只按指定 flavour 转换文本形式。"""

    assert posixpath.normcase("/Data/Report.TXT") == "/Data/Report.TXT"
    assert ntpath.normcase("C:/Data/Report.TXT") == r"c:\data\report.txt"


def test_normpath_collapses_dotdot_lexically_and_can_change_symlink_meaning(tmp_path):
    """link/.. 按真实 target parent 解释，normpath 却按 link 文本 parent 化简，两者可能不同。"""

    real = tmp_path / "real"
    nested = real / "nested"
    nested.mkdir(parents=True)
    (real / "item.txt").touch()
    link = tmp_path / "link"
    link.symlink_to(nested, target_is_directory=True)
    raw = os.fspath(link / ".." / "item.txt")

    assert os.path.normpath(raw) == os.fspath(tmp_path / "item.txt")
    assert os.path.realpath(raw) == os.fspath(real / "item.txt")
    assert os.path.normpath(raw) != os.path.realpath(raw)


def test_python_310_realpath_strict_controls_missing_path_errors(tmp_path):
    """3.10 新增 strict；False 把首个错误后的 remainder 原样附加，True 立即重抛。"""

    missing = tmp_path / "missing" / "child.txt"

    assert os.path.realpath(missing, strict=False) == str(missing)
    with pytest.raises(FileNotFoundError):
        os.path.realpath(missing, strict=True)


def test_relpath_is_a_lexical_route_and_does_not_require_existing_paths():
    """它能为任意 compatible 文本生成含 ``..`` 的路线，不像 PurePath.relative_to 要求 containment。"""

    start = "/does/not/exist/project"
    target = "/does/not/exist/data/items.json"

    assert posixpath.relpath(target, start=start) == "../data/items.json"


def test_samefile_detects_hard_link_identity(tmp_path):
    """不同 pathname 可以指向同一 device/inode；字符串比较无法替代 samefile。"""

    source = tmp_path / "source.txt"
    alias = tmp_path / "alias.txt"
    source.touch()
    alias.hardlink_to(source)

    assert os.fspath(source) != os.fspath(alias)
    assert os.path.samefile(source, alias) is True


def test_sameopenfile_and_samestat_reuse_descriptor_and_stat_identity(tmp_path):
    """打开两次同一文件得到不同 fd 数字，但 underlying file identity 相同。"""

    path = tmp_path / "data.txt"
    path.touch()

    with path.open("rb") as first, path.open("rb") as second:
        assert first.fileno() != second.fileno()
        assert os.path.sameopenfile(first.fileno(), second.fileno()) is True
        assert os.path.samestat(os.fstat(first.fileno()), os.fstat(second.fileno())) is True


def test_splitdrive_understands_windows_drive_and_unc_sharepoints():
    """显式 ntpath 可在 Linux 上纯词法解析 drive/UNC，不应拿 native posixpath 猜 Windows 路径。"""

    assert ntpath.splitdrive("c:/dir/file") == ("c:", "/dir/file")
    assert ntpath.splitdrive("//host/share/dir") == ("//host/share", "/dir")
    assert posixpath.splitdrive("c:/dir/file") == ("", "c:/dir/file")


def test_splitext_uses_only_the_last_extension_and_treats_leading_dots_as_name():
    """extension 最多含一个 leading dot；先前 dots 留在 root，纯 dotfile 默认没有 extension。"""

    assert posixpath.splitext("archive.tar.gz") == ("archive.tar", ".gz")
    assert posixpath.splitext(".cshrc") == (".cshrc", "")
    assert posixpath.splitext("/tmp/....jpg") == ("/tmp/....jpg", "")


def test_supports_unicode_filenames_is_a_platform_capability_boolean():
    """该常量描述操作系统级能力，不保证每个具体 filesystem/名称都可用。"""

    assert type(os.path.supports_unicode_filenames) is bool
