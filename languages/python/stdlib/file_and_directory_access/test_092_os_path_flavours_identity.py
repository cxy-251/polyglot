"""092｜``os.path`` flavour、词法处理与文件 identity。

os.path 绑定宿主 flavour；需要离线处理固定格式时可显式用 posixpath/ntpath。多数函数
只做字符串计算，不展开 shell 变量、不访问磁盘，也不能用 normpath 代替 symlink-aware
安全校验。samefile/sameopenfile/samestat 才按 device/inode 判断真实文件 identity。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.path python.posixpath python.ntpath
# polyglot-covers: python.os.pathlike-input python.os.path-str-bytes-consistency
# polyglot-covers: python.os.path.abspath python.os.path.cwd-dependency
# polyglot-covers: python.os.path.basename python.os.path.dirname python.os.path.split
# polyglot-covers: python.os.path.commonpath python.os.path.commonprefix python.os.path.security-prefix
# polyglot-covers: python.os.path.exists python.os.path.open-file-descriptor
# polyglot-covers: python.os.path.lexists python.os.path.broken-symlink
# polyglot-covers: python.os.path.expanduser python.os.path.expandvars python.os.path.explicit-expansion
# polyglot-covers: python.os.path.getsize python.os.path.getatime python.os.path.getmtime python.os.path.getctime
# polyglot-covers: python.os.path.isabs python.os.path.isfile python.os.path.isdir python.os.path.islink
# polyglot-covers: python.os.path.ismount python.os.path.join
# polyglot-covers: python.os.path.normcase python.os.path.normpath python.os.path.symlink-normalization-trap
# polyglot-covers: python.os.path.realpath python.os.path.python310-realpath-strict
# polyglot-covers: python.os.path.relpath python.os.path.lexical-relpath
# polyglot-covers: python.os.path.samefile python.os.path.sameopenfile python.os.path.samestat
# polyglot-covers: python.os.path.splitdrive python.os.path.splitext python.os.path.leading-dot-extension
# polyglot-covers: python.os.path.supports_unicode_filenames

import ntpath
import os
from pathlib import Path
import posixpath

import pytest


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
