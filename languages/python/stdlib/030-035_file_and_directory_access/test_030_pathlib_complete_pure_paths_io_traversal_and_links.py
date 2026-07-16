"""030｜``pathlib`` 的纯路径语义与临时文件系统工作流示例。

PurePath 只做路径字符串的词法操作，不查询磁盘；Path 在对应平台 flavor 上增加
stat、读写、枚举、重命名等系统调用。本文件所有有副作用案例均限制在 pytest
tmp_path 内。

内容基于 Python 3.10 pathlib 和 os.PathLike 文档。built-in open 的 text/binary
基础已在 029 展示。
"""

# polyglot-covers: python.stdlib.pathlib python.pathlib.PurePath python.pathlib.Path
# polyglot-covers: python.pathlib.PurePosixPath python.pathlib.PureWindowsPath
# polyglot-covers: python.pathlib.path-parts python.pathlib.path-properties
# polyglot-covers: python.pathlib.path-transformations python.pathlib.relative_to
# polyglot-covers: python.pathlib.match python.pathlib.resolve python.pathlib.expanduser
# polyglot-covers: python.pathlib.mkdir python.pathlib.touch
# polyglot-covers: python.pathlib.text-io python.pathlib.binary-io
# polyglot-covers: python.pathlib.stat python.pathlib.iterdir python.pathlib.glob
# polyglot-covers: python.pathlib.rename python.pathlib.replace python.pathlib.unlink
# polyglot-covers: python.pathlib.symlink python.pathlib.readlink python.os.PathLike




import os
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
import pytest
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from pathlib import Path, PosixPath, WindowsPath
import stat
from pathlib import Path

def test_pure_paths_join_lexically_without_touching_filesystem():
    """构造参数和 ``/`` 运算符拼接路径片段，结果不要求磁盘对象存在。"""

    generic = PurePath("not-created", "example.txt")
    base = PurePosixPath("/srv", "app")
    config = base / "config" / "settings.toml"

    assert generic.parts == ("not-created", "example.txt")
    assert config == PurePosixPath("/srv/app/config/settings.toml")
    assert base.joinpath("data", "items.json") == PurePosixPath(
        "/srv/app/data/items.json"
    )
    assert config.is_absolute()
    assert not PurePosixPath("relative/file.txt").is_absolute()

    # PurePath 没有 exists/read_text 等磁盘方法，适合解析配置中的另一平台路径。
    assert not hasattr(config, "exists")


def test_absolute_joined_part_discards_earlier_posix_parts():
    """POSIX 拼接遇到绝对片段时，该片段成为新路径根。"""

    base = PurePosixPath("/srv/app")

    assert base / "logs" == PurePosixPath("/srv/app/logs")
    assert base / "/etc/app.conf" == PurePosixPath("/etc/app.conf")

    # 动态片段若意外以 `/` 开头会丢掉 base；接收用户片段时应先验证其是否相对。


def test_windows_flavor_preserves_drive_and_understands_drive_replacement():
    """Windows rooted-relative 路径保留当前 drive，带新 drive 的绝对路径会替换它。"""

    base = PureWindowsPath("c:/Windows")

    assert base / "System32" == PureWindowsPath("c:/Windows/System32")
    assert base / "/Program Files" == PureWindowsPath("c:/Program Files")
    assert base / "d:/Data" == PureWindowsPath("d:/Data")

    # 在 Linux 上用 Path("c:\\...") 不会自动获得 Windows 语义；应显式 PureWindowsPath。


def test_path_flavors_have_different_case_and_reserved_name_rules():
    """Windows 路径比较不区分大小写，POSIX 路径比较区分大小写。"""

    assert PureWindowsPath("README.TXT") == PureWindowsPath("readme.txt")
    assert PurePosixPath("README.TXT") != PurePosixPath("readme.txt")
    assert PureWindowsPath("nul").is_reserved()
    assert PureWindowsPath("folder/con.txt").is_reserved()
    assert not PurePosixPath("nul").is_reserved()

    with pytest.raises(TypeError):
        PureWindowsPath("a") < PurePosixPath("b")


def test_drive_root_anchor_and_parts_expose_platform_structure():
    """anchor 组合 drive/root，parts 则保留可逐段处理的路径组成。"""

    posix = PurePosixPath("/usr/local/bin/python")
    windows = PureWindowsPath("c:/Program Files/Python/python.exe")

    assert posix.drive == ""
    assert posix.root == "/"
    assert posix.anchor == "/"
    assert posix.parts == ("/", "usr", "local", "bin", "python")

    assert windows.drive == "c:"
    assert windows.root == "\\"
    assert windows.anchor == "c:\\"
    assert windows.parts == (
        "c:\\",
        "Program Files",
        "Python",
        "python.exe",
    )


def test_name_stem_suffix_and_suffixes_handle_multi_extension_names():
    """suffix 只取最后扩展名，suffixes 返回全部扩展片段。"""

    archive = PurePosixPath("downloads/project.tar.gz")

    assert archive.name == "project.tar.gz"
    assert archive.stem == "project.tar"
    assert archive.suffix == ".gz"
    assert archive.suffixes == [".tar", ".gz"]

    hidden = PurePosixPath(".gitignore")
    assert hidden.name == ".gitignore"
    assert hidden.stem == ".gitignore"
    assert hidden.suffix == ""
    assert hidden.suffixes == []

    # 需要识别 `.tar.gz` 格式时检查 suffixes/完整名称，不能只看 suffix。


def test_with_name_stem_and_suffix_create_new_paths_without_mutation():
    """with_* 只替换最后名称组成，原 PurePath 保持不变。"""

    source = PurePosixPath("reports/summary.old.txt")

    assert source.with_name("final.csv") == PurePosixPath("reports/final.csv")
    assert source.with_stem("final") == PurePosixPath("reports/final.txt")
    assert source.with_suffix(".md") == PurePosixPath("reports/summary.old.md")
    assert source.with_suffix("") == PurePosixPath("reports/summary.old")
    assert source == PurePosixPath("reports/summary.old.txt")

    with pytest.raises(ValueError):
        PurePosixPath("/").with_name("root.txt")


def test_parent_and_parents_are_lexical_and_do_not_resolve_dotdot():
    """parent 只是移除最后片段，不查询或规范化真实目录。"""

    path = PurePosixPath("/srv/app/config/settings.toml")

    assert path.parent == PurePosixPath("/srv/app/config")
    assert path.parents[0] == PurePosixPath("/srv/app/config")
    assert path.parents[1] == PurePosixPath("/srv/app")
    assert path.parents[-1] == PurePosixPath("/")
    assert path.parents[:2] == (
        PurePosixPath("/srv/app/config"),
        PurePosixPath("/srv/app"),
    )

    unresolved = PurePosixPath("/srv/app/../secrets")
    assert unresolved.parent == PurePosixPath("/srv/app/..")
    assert ".." in unresolved.parts

    # Python 3.10 的 parents 支持切片；解析 `..` 要用具体 Path.resolve()。


def test_relative_to_and_is_relative_to_require_lexical_containment():
    """relative_to 只移除共同前缀，不生成通往任意路径的 ``..``。"""

    path = PurePosixPath("/srv/app/config/settings.toml")

    assert path.is_relative_to("/srv/app")
    assert path.relative_to("/srv/app") == PurePosixPath("config/settings.toml")
    assert not path.is_relative_to("/etc")

    with pytest.raises(ValueError, match="not in the subpath"):
        path.relative_to("/etc")

    # 需要任意两条路径间的相对路线时使用 os.path.relpath，并明确它依赖词法基准。


def test_match_uses_flavor_rules_and_matches_from_the_right_for_relative_patterns():
    """relative glob pattern 从路径右侧匹配，Windows flavor 同样不区分大小写。"""

    path = PurePosixPath("src/package/module.py")

    assert path.match("*.py")
    assert path.match("package/*.py")
    assert path.match("src/**/module.py")
    assert not path.match("tests/*.py")
    assert PureWindowsPath("SRC/APP.PY").match("src/*.py")

    with pytest.raises(ValueError, match="empty pattern"):
        path.match("")


def test_path_construction_does_not_expand_tilde_or_resolve_dotdot():
    """Path 构造仍是词法操作；展开/解析必须调用明确方法。"""

    home_like = Path("~/documents")
    unresolved = Path("folder/../other")

    assert home_like.parts[0] == "~"
    assert not home_like.is_absolute()
    assert ".." in unresolved.parts

    # 这两个对象的创建不会访问 HOME、cwd 或磁盘。


def test_path_is_immutable_hashable_and_implements_pathlike_protocol():
    """Path 可作 dict key，并通过 os.fspath 交给接受路径协议的 API。"""

    path = Path("data/items.json")
    mapping = {path: "payload"}

    assert mapping[Path("data/items.json")] == "payload"
    assert os.fspath(path) == str(path)
    assert path.__fspath__() == str(path)

    with pytest.raises(AttributeError):
        path.name = "other.json"


def test_cwd_home_expanduser_absolute_and_resolve_have_distinct_jobs(tmp_path, monkeypatch):
    """环境展开、变为绝对路径和规范化/解析是三步不同操作。"""

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    assert Path.cwd().is_absolute()
    assert Path.home() == fake_home
    assert Path("~/docs").expanduser() == fake_home / "docs"

    relative = Path("folder/../target")
    assert relative.absolute().is_absolute()
    assert relative.resolve(strict=False).is_absolute()

    # 不断言真实 cwd，只断言契约；测试文件路径仍全部来自 tmp_path。


def test_mkdir_parents_exist_ok_and_touch_manage_creation_boundaries(tmp_path):
    """parents 创建缺失祖先，exist_ok 只放宽“已是目录”的冲突。"""

    nested = tmp_path / "a" / "b" / "c"

    with pytest.raises(FileNotFoundError):
        nested.mkdir()

    nested.mkdir(parents=True)
    assert nested.is_dir()

    with pytest.raises(FileExistsError):
        nested.mkdir()

    nested.mkdir(exist_ok=True)

    marker = nested / "ready.flag"
    marker.touch()
    assert marker.is_file()

    with pytest.raises(FileExistsError):
        marker.touch(exist_ok=False)


def test_path_text_and_binary_helpers_use_explicit_content_boundaries(tmp_path):
    """write_text/read_text 处理 str，write_bytes/read_bytes 处理 bytes。"""

    text_path = tmp_path / "message.txt"
    binary_path = tmp_path / "packet.bin"

    assert text_path.write_text("咖啡\n", encoding="utf-8", newline="\n") == 3
    assert text_path.read_text(encoding="utf-8") == "咖啡\n"

    payload = b"\x00\x01\xff"
    assert binary_path.write_bytes(payload) == 3
    assert binary_path.read_bytes() == payload

    # write_* 与 open(..., "w"/"wb") 一样会覆盖已有内容。
    text_path.write_text("new", encoding="utf-8")
    assert text_path.read_text(encoding="utf-8") == "new"


def test_path_open_supports_streaming_modes_when_one_shot_helpers_are_not_enough(tmp_path):
    """Path.open 返回普通 file object，可追加或逐行处理。"""

    path = tmp_path / "events.log"

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("first\n")

    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("second\n")

    with path.open("r", encoding="utf-8") as handle:
        assert list(handle) == ["first\n", "second\n"]


def test_exists_file_dir_stat_and_samefile_query_real_filesystem(tmp_path):
    """这些 concrete Path 方法才会发出文件系统查询。"""

    directory = tmp_path / "data"
    file_path = directory / "items.txt"
    directory.mkdir()
    file_path.write_text("abc", encoding="ascii")

    assert directory.exists() and directory.is_dir()
    assert not directory.is_file()
    assert file_path.exists() and file_path.is_file()
    assert not file_path.is_dir()
    assert file_path.stat().st_size == 3
    assert file_path.samefile(directory / "items.txt")

    missing = directory / "missing.txt"
    assert not missing.exists()
    assert not missing.is_file()


def test_iterdir_glob_and_rglob_results_must_be_sorted_for_determinism(tmp_path):
    """文件系统枚举顺序未承诺；断言/输出前按明确键排序。"""

    (tmp_path / "nested").mkdir()
    (tmp_path / "b.txt").write_text("b", encoding="ascii")
    (tmp_path / "a.py").write_text("a", encoding="ascii")
    (tmp_path / "nested" / "c.py").write_text("c", encoding="ascii")
    (tmp_path / "nested" / "d.txt").write_text("d", encoding="ascii")

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "a.py",
        "b.txt",
        "nested",
    ]
    assert sorted(path.name for path in tmp_path.glob("*.py")) == ["a.py"]
    assert sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*.py")
    ) == ["a.py", "nested/c.py"]

    # glob 返回 Path iterator；是否递归由模式/rglob 明确决定，而不是自动遍历子目录。


def test_rename_moves_path_and_replace_overwrites_destination(tmp_path):
    """rename/replace 返回新 Path；原 Path 对象不变但所指旧位置可能不再存在。"""

    source = tmp_path / "source.txt"
    renamed = tmp_path / "renamed.txt"
    destination = tmp_path / "destination.txt"
    source.write_text("first", encoding="ascii")

    returned = source.rename(renamed)
    assert returned == renamed
    assert not source.exists()
    assert renamed.read_text(encoding="ascii") == "first"

    destination.write_text("old", encoding="ascii")
    returned = renamed.replace(destination)
    assert returned == destination
    assert not renamed.exists()
    assert destination.read_text(encoding="ascii") == "first"


def test_unlink_missing_ok_and_rmdir_enforce_file_directory_distinction(tmp_path):
    """unlink 删除文件/链接，rmdir 只删除空目录。"""

    directory = tmp_path / "folder"
    directory.mkdir()
    file_path = directory / "item.txt"
    file_path.write_text("data", encoding="ascii")

    with pytest.raises(OSError):
        directory.rmdir()

    with pytest.raises((IsADirectoryError, PermissionError)):
        directory.unlink()

    file_path.unlink()
    assert not file_path.exists()
    file_path.unlink(missing_ok=True)

    directory.rmdir()
    assert not directory.exists()


def test_symlink_readlink_resolve_and_broken_link_have_distinct_observations(tmp_path):
    """链接本身与其目标是两个对象；exists 跟随目标，is_symlink 检查链接。"""

    target = tmp_path / "target.txt"
    target.write_text("payload", encoding="ascii")

    link = tmp_path / "current.txt"
    link.symlink_to(target.name)

    assert link.is_symlink()
    assert link.readlink() == Path("target.txt")
    assert link.resolve(strict=True) == target.resolve(strict=True)
    assert link.samefile(target)
    assert link.read_text(encoding="ascii") == "payload"

    broken = tmp_path / "broken.txt"
    broken.symlink_to("missing.txt")

    assert broken.is_symlink()
    assert not broken.exists()
    assert broken.readlink() == Path("missing.txt")
    assert broken.resolve(strict=False) == tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        broken.resolve(strict=True)

    # broken.exists() 为 False 不代表目录项完全不存在；清理时仍可 broken.unlink()。
    broken.unlink()
    assert not broken.is_symlink()


# ``pathlib`` 纯路径 flavour 与词法变换。
#
# PurePosixPath/PureWindowsPath 只做词法计算，可在任意宿主系统上安全研究另一平台路径。
# 它们会折叠冗余分隔符和单点，却刻意保留 ``..``，因为符号链接会让天真归一化改变含义。
# 路径不可变、可哈希，并实现 os.PathLike；大小写与 drive/root 规则由 flavour 决定。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.pathlib.PurePath python.pathlib.PurePosixPath
# polyglot-covers: python.pathlib.PureWindowsPath
# polyglot-covers: python.pathlib.path-segments python.pathlib.os-PathLike
# polyglot-covers: python.pathlib.absolute-segment-reset python.pathlib.windows-rooted-relative
# polyglot-covers: python.pathlib.lexical-normalization python.pathlib.preserve-dotdot
# polyglot-covers: python.pathlib.pure-immutable python.pathlib.flavour-casefold
# polyglot-covers: python.pathlib.cross-flavour-comparison python.pathlib.slash-operator
# polyglot-covers: python.pathlib.fspath python.pathlib.parts
# polyglot-covers: python.pathlib.drive python.pathlib.root python.pathlib.anchor
# polyglot-covers: python.pathlib.parents python.pathlib.python310-parents-slice
# polyglot-covers: python.pathlib.parent python.pathlib.name
# polyglot-covers: python.pathlib.suffix python.pathlib.suffixes python.pathlib.stem
# polyglot-covers: python.pathlib.as_posix python.pathlib.as_uri
# polyglot-covers: python.pathlib.is_absolute python.pathlib.is_relative_to
# polyglot-covers: python.pathlib.is_reserved python.pathlib.joinpath
# polyglot-covers: python.pathlib.match python.pathlib.relative-pattern-right-match
# polyglot-covers: python.pathlib.relative_to python.pathlib.lexical-relative
# polyglot-covers: python.pathlib.with_name python.pathlib.with_stem python.pathlib.with_suffix




class ConfigPath:
    """最小 os.PathLike：把领域对象交给 pathlib，而不继承具体 Path class。"""

    def __init__(self, value):
        self.value = value

    def __fspath__(self):
        return self.value


def test_explicit_pure_flavours_are_platform_independent():
    """PurePath 选择宿主 flavour；显式 PurePosix/PureWindows 则可在任何机器上构造。"""

    generic = PurePath("project", "src")
    posix = PurePosixPath("project", "src")
    windows = PureWindowsPath("project", "src")

    assert isinstance(generic, (PurePosixPath, PureWindowsPath))
    assert str(posix) == "project/src"
    assert str(windows) == r"project\src"


def test_constructor_combines_strings_paths_and_pathlike_segments():
    """每个 segment 可为 str、另一 Path 或返回 str 的 os.PathLike。"""

    path = PurePosixPath(ConfigPath("project"), PurePosixPath("src/package"), "module.py")

    assert path == PurePosixPath("project/src/package/module.py")
    assert os.fspath(path) == "project/src/package/module.py"


def test_empty_segments_and_no_arguments_represent_current_directory():
    """空构造与空字符串都规范为逻辑当前目录 ``.``，不是空的 path object。"""

    assert PurePosixPath() == PurePosixPath(".")
    assert PurePosixPath("") == PurePosixPath(".")
    assert str(PurePosixPath()) == "."


def test_absolute_segment_discards_previous_posix_segments():
    """与 os.path.join 相同，后遇到绝对路径时之前的 base 已无意义。"""

    assert PurePosixPath("/etc", "/usr", "lib64") == PurePosixPath("/usr/lib64")
    assert PurePosixPath("base") / "/absolute" == PurePosixPath("/absolute")


def test_windows_drive_and_rooted_relative_segments_have_distinct_reset_rules():
    """新 drive 会替换旧 drive；只有 root 没有 drive 的片段保留当前 drive。"""

    assert PureWindowsPath("c:/Windows", "d:bar") == PureWindowsPath("d:bar")
    assert PureWindowsPath("c:/Windows", "/Program Files") == PureWindowsPath("c:/Program Files")


def test_normalization_collapses_slashes_and_dot_but_preserves_dotdot():
    """foo 可能是 symlink，故 ``foo/..`` 不能在纯词法阶段化简成当前目录。"""

    assert PurePosixPath("foo//bar") == PurePosixPath("foo/bar")
    assert PurePosixPath("foo/./bar") == PurePosixPath("foo/bar")
    assert PurePosixPath("foo/../bar") != PurePosixPath("bar")
    assert str(PurePosixPath("foo/../bar")) == "foo/../bar"


def test_posix_leading_double_slash_is_preserved_but_longer_runs_collapse():
    """POSIX 允许 ``//`` 有实现定义语义，三个以上前导 slash 才统一折叠为一个。"""

    assert str(PurePosixPath("//server/share")) == "//server/share"
    assert str(PurePosixPath("///server/share")) == "/server/share"


def test_pure_paths_are_immutable_and_hashable():
    """路径变换返回新对象；原对象可安全作为 dict/set key。"""

    path = PurePosixPath("project/readme.md")
    child = path.parent / "license.txt"

    assert {path: "document"}[PurePosixPath("project/readme.md")] == "document"
    assert path == PurePosixPath("project/readme.md")
    assert child == PurePosixPath("project/license.txt")

    with pytest.raises(AttributeError):
        path.name = "changed.md"


def test_equality_and_hashing_follow_flavour_case_rules():
    """POSIX 大小写敏感，Windows path 比较与 hash 使用该 flavour 的 case folding。"""

    assert PurePosixPath("foo") != PurePosixPath("FOO")
    assert PureWindowsPath("foo") == PureWindowsPath("FOO")
    assert PureWindowsPath("FOO") in {PureWindowsPath("foo")}


def test_different_flavours_are_unequal_and_cannot_be_ordered():
    """跨 flavour 没有统一排序语义；相等比较为 False，方向比较明确报 TypeError。"""

    posix = PurePosixPath("foo")
    windows = PureWindowsPath("foo")

    assert posix != windows
    with pytest.raises(TypeError):
        posix < windows


def test_slash_operator_accepts_path_on_either_side():
    """Path 实现正向与反向 /，让字符串 base 也能和 path segment 组合。"""

    child = PurePosixPath("bin")

    assert PurePosixPath("/usr") / child == PurePosixPath("/usr/bin")
    assert "/usr" / child == PurePosixPath("/usr/bin")


def test_pathlike_string_and_bytes_representations_have_distinct_roles():
    """os.fspath/str 给 native 文本；bytes 用文件系统编码，文档只建议在 Unix 使用。"""

    path = PurePosixPath("/tmp/data.txt")

    assert os.fspath(path) == "/tmp/data.txt"
    assert str(path) == "/tmp/data.txt"
    assert bytes(path) == b"/tmp/data.txt"


def test_parts_preserve_anchor_as_a_single_component():
    """POSIX root 与 Windows drive+root 各自形成首个 part，而非按字符分隔。"""

    assert PurePosixPath("/usr/bin/python3").parts == ("/", "usr", "bin", "python3")
    assert PureWindowsPath("c:/Program Files/PSF").parts == ("c:\\", "Program Files", "PSF")


def test_drive_root_and_anchor_expose_windows_path_kinds():
    """drive 与 root 独立；anchor 是二者拼接，drive-relative ``c:foo`` 没有 root。"""

    absolute = PureWindowsPath("c:/Program Files")
    drive_relative = PureWindowsPath("c:Program Files")
    unc = PureWindowsPath("//host/share/folder")

    assert (absolute.drive, absolute.root, absolute.anchor) == ("c:", "\\", "c:\\")
    assert (drive_relative.drive, drive_relative.root, drive_relative.anchor) == ("c:", "", "c:")
    assert unc.drive == r"\\host\share"
    assert unc.root == "\\"
    assert unc.anchor == "\\\\host\\share\\"


def test_parents_support_index_negative_index_and_slice_in_python_310():
    """3.10 的 parents 是 immutable sequence，可倒数和切片；顺序从最近 ancestor 向 anchor。"""

    path = PurePosixPath("/a/b/c/file.txt")

    assert path.parents[0] == PurePosixPath("/a/b/c")
    assert path.parents[-1] == PurePosixPath("/")
    assert path.parents[:2] == (PurePosixPath("/a/b/c"), PurePosixPath("/a/b"))


def test_parent_is_lexical_and_cannot_walk_past_anchor():
    """parent 不访问文件系统，也不消解 ``..``；需要真实 canonical ancestor 时先 resolve。"""

    assert PurePosixPath("/").parent == PurePosixPath("/")
    assert PurePosixPath(".").parent == PurePosixPath(".")
    assert PurePosixPath("foo/..").parent == PurePosixPath("foo")


def test_name_suffixes_and_stem_split_only_the_final_component():
    """suffix 是最后一个扩展名，suffixes 保留全部扩展名，stem 只移除最后 suffix。"""

    path = PurePosixPath("archives/library.tar.gz")

    assert path.name == "library.tar.gz"
    assert path.suffix == ".gz"
    assert path.suffixes == [".tar", ".gz"]
    assert path.stem == "library.tar"
    assert PurePosixPath(".bashrc").suffix == ""


def test_as_posix_normalizes_windows_separators_without_changing_flavour():
    """as_posix 只返回正斜杠文本；原 PureWindowsPath 仍保有 Windows 比较和 drive 语义。"""

    path = PureWindowsPath(r"c:\Windows\System32")

    assert path.as_posix() == "c:/Windows/System32"
    assert path.drive == "c:"


def test_as_uri_requires_an_absolute_path():
    """file URI 必须具备 absolute anchor，relative path 没有足够信息编码。"""

    assert PurePosixPath("/etc/passwd").as_uri() == "file:///etc/passwd"
    assert PureWindowsPath("c:/Windows").as_uri() == "file:///c:/Windows"

    with pytest.raises(ValueError):
        PurePosixPath("relative.txt").as_uri()


def test_absolute_rules_differ_for_windows_drive_relative_paths():
    """Windows absolute 需要 drive 与 root；仅 ``/path`` 或仅 ``c:path`` 都不完整。"""

    assert PurePosixPath("/a/b").is_absolute() is True
    assert PurePosixPath("a/b").is_absolute() is False
    assert PureWindowsPath("c:/a/b").is_absolute() is True
    assert PureWindowsPath("/a/b").is_absolute() is False
    assert PureWindowsPath("c:a/b").is_absolute() is False
    assert PureWindowsPath("//server/share").is_absolute() is True


def test_is_relative_to_is_a_boolean_form_of_relative_to_check():
    """3.9+ 可先用 boolean 查询 containment，避免把普通“不在此树”当 exception control flow。"""

    path = PurePosixPath("/etc/passwd")

    assert path.is_relative_to("/etc") is True
    assert path.is_relative_to("/usr") is False


def test_reserved_names_are_windows_specific():
    """NUL/CON 等 Windows device 名可能导致异常系统行为，POSIX flavour 不把它们保留。"""

    assert PureWindowsPath("NUL").is_reserved() is True
    assert PureWindowsPath("folder/con.txt").is_reserved() is True
    assert PurePosixPath("NUL").is_reserved() is False


def test_joinpath_matches_repeated_slash_composition():
    """joinpath 可一次接收多个 segment，绝对 segment 的 reset 规则与 / 完全相同。"""

    base = PurePosixPath("/etc")

    assert base.joinpath("init.d", "apache2") == base / "init.d" / "apache2"
    assert base.joinpath("relative", "/reset") == PurePosixPath("/reset")


def test_relative_match_patterns_compare_from_the_right():
    """relative glob pattern 不要求覆盖完整 path；匹配从末尾 components 开始。"""

    path = PurePosixPath("/a/b/c.py")

    assert path.match("*.py") is True
    assert path.match("b/*.py") is True
    assert path.match("a/*.py") is False


def test_absolute_match_patterns_require_the_whole_absolute_path():
    """absolute pattern 不使用右侧 suffix 规则，relative candidate 也不能匹配 absolute pattern。"""

    assert PurePosixPath("/a.py").match("/*.py") is True
    assert PurePosixPath("a/b.py").match("/*.py") is False


def test_match_case_sensitivity_follows_path_flavour():
    """同一个 pattern 在 POSIX 区分大小写，在 Windows 使用 case-insensitive flavour 规则。"""

    assert PurePosixPath("b.py").match("*.PY") is False
    assert PureWindowsPath("b.py").match("*.PY") is True


def test_relative_to_requires_a_real_lexical_subpath():
    """relative_to 不是 os.path.relpath：self 必须位于 base 下，且 absolute/relative 类型一致。"""

    path = PurePosixPath("/etc/nginx/nginx.conf")

    assert path.relative_to("/etc") == PurePosixPath("nginx/nginx.conf")
    with pytest.raises(ValueError):
        path.relative_to("/usr")
    with pytest.raises(ValueError):
        path.relative_to("etc")


def test_with_name_stem_and_suffix_return_new_paths():
    """with_stem 只保留最后 suffix；多扩展名 ``tar.gz`` 改 stem 后得到 ``new.gz``。"""

    original = PurePosixPath("downloads/archive.tar.gz")

    assert original.with_name("setup.py") == PurePosixPath("downloads/setup.py")
    assert original.with_stem("library") == PurePosixPath("downloads/library.gz")
    assert original.with_suffix(".bz2") == PurePosixPath("downloads/archive.tar.bz2")
    assert original.with_suffix("") == PurePosixPath("downloads/archive.tar")
    assert original == PurePosixPath("downloads/archive.tar.gz")


def test_path_component_replacements_validate_names_and_suffix_shape():
    """anchor 没有 name 可替换；name 不能含 separator，非空 suffix 必须以点开头。"""

    with pytest.raises(ValueError):
        PurePosixPath("/").with_name("file.txt")
    with pytest.raises(ValueError):
        PurePosixPath("file.txt").with_name("folder/file.txt")
    with pytest.raises(ValueError):
        PurePosixPath("file.txt").with_suffix("txt")


# ``pathlib.Path`` 目录、文件 I/O 与基础状态变更。
#
# Path 继承纯路径的词法 API，并增加真实系统调用。所有案例只在 pytest tmp_path 下工作；
# 目录枚举不依赖系统返回顺序，权限只检查 chmod 后的 mode bits，不访问真实用户目录。
# write_text/write_bytes 会覆盖同名文件，mkdir/touch/unlink 则通过选项明确幂等边界。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.pathlib.Path python.pathlib.concrete-platform-flavour
# polyglot-covers: python.pathlib.Path.cwd python.pathlib.Path.home python.pathlib.expanduser
# polyglot-covers: python.pathlib.mkdir python.pathlib.mkdir-parents python.pathlib.mkdir-exist-ok
# polyglot-covers: python.pathlib.open python.pathlib.open-modes
# polyglot-covers: python.pathlib.write_text python.pathlib.read_text
# polyglot-covers: python.pathlib.python310-newline
# polyglot-covers: python.pathlib.write_bytes python.pathlib.read_bytes python.pathlib.overwrite
# polyglot-covers: python.pathlib.touch python.pathlib.touch-exist-ok
# polyglot-covers: python.pathlib.exists python.pathlib.is_file python.pathlib.is_dir
# polyglot-covers: python.pathlib.special-file-predicates python.pathlib.missing-predicate-false
# polyglot-covers: python.pathlib.iterdir python.pathlib.iterdir-order
# polyglot-covers: python.pathlib.stat python.pathlib.lstat python.pathlib.stat-fresh-lookup
# polyglot-covers: python.pathlib.chmod python.pathlib.permissions
# polyglot-covers: python.pathlib.unlink python.pathlib.unlink-missing-ok
# polyglot-covers: python.pathlib.rmdir python.pathlib.remove-kind-boundary
# polyglot-covers: python.pathlib.rename python.pathlib.replace python.pathlib.rename-return
# polyglot-covers: python.pathlib.resolve python.pathlib.resolve-strict




def test_path_selects_the_concrete_flavour_for_the_running_platform(tmp_path):
    """Path 是 factory-like concrete class，结果 flavour 与宿主系统一致并可直接 I/O。"""

    path = Path(tmp_path, "example.txt")

    assert isinstance(path, Path)
    assert isinstance(path, PosixPath if os.name == "posix" else WindowsPath)
    assert os.fspath(path).endswith("example.txt")


def test_cwd_and_home_can_be_isolated_to_temporary_locations(tmp_path, monkeypatch):
    """测试不依赖真实用户目录：临时改变 cwd/HOME 后，两个 classmethod 返回对应 Path。"""

    working = tmp_path / "working"
    home = tmp_path / "home"
    working.mkdir()
    home.mkdir()
    monkeypatch.chdir(working)
    monkeypatch.setenv("HOME", str(home))

    assert Path.cwd() == working
    assert Path.home() == home
    assert Path("~/documents").expanduser() == home / "documents"


def test_mkdir_default_requires_an_existing_parent(tmp_path):
    """parents=False 只创建最后一层，缺失 parent 会抛 FileNotFoundError。"""

    target = tmp_path / "missing" / "child"

    with pytest.raises(FileNotFoundError):
        target.mkdir()


def test_mkdir_parents_creates_a_tree_and_exist_ok_makes_retry_idempotent(tmp_path):
    """parents=True 类似 mkdir -p；exist_ok=True 只忽略最后目标已经是 directory 的情况。"""

    target = tmp_path / "one" / "two" / "three"

    assert target.mkdir(parents=True) is None
    assert target.is_dir()
    assert target.mkdir(parents=True, exist_ok=True) is None

    with pytest.raises(FileExistsError):
        target.mkdir(exist_ok=False)


def test_mkdir_exist_ok_does_not_accept_an_existing_regular_file(tmp_path):
    """同名 file 不是已经满足的 directory，exist_ok=True 仍必须失败。"""

    target = tmp_path / "not-a-directory"
    target.write_text("content", encoding="utf-8")

    with pytest.raises(FileExistsError):
        target.mkdir(exist_ok=True)


def test_write_and_read_text_round_trip_explicit_encoding(tmp_path):
    """显式 encoding 让结果不依赖 locale；write_text 返回写入的字符数而非 byte 数。"""

    path = tmp_path / "message.txt"
    text = "你好，Python"

    written = path.write_text(text, encoding="utf-8")

    assert written == len(text)
    assert path.read_text(encoding="utf-8") == text
    assert len(path.read_bytes()) > written


def test_python_310_write_text_newline_controls_translation(tmp_path):
    """3.10 新增 newline；指定 CRLF 后，输入中的 \n 以两个 bytes 写入。"""

    path = tmp_path / "windows-lines.txt"

    path.write_text("first\nsecond\n", encoding="ascii", newline="\r\n")

    assert path.read_bytes() == b"first\r\nsecond\r\n"


def test_write_text_overwrites_an_existing_file(tmp_path):
    """便利方法等价于 mode='w'，不是 append；第二次写会 truncate 原内容。"""

    path = tmp_path / "state.txt"
    path.write_text("old data", encoding="utf-8")
    path.write_text("new", encoding="utf-8")

    assert path.read_text(encoding="utf-8") == "new"


def test_write_and_read_bytes_preserve_arbitrary_binary_data(tmp_path):
    """bytes API 不做编码/换行转换，返回值是实际写入 byte 数。"""

    path = tmp_path / "payload.bin"
    payload = bytes([0, 1, 2, 255])

    assert path.write_bytes(payload) == 4
    assert path.read_bytes() == payload


def test_write_bytes_overwrites_instead_of_appending(tmp_path):
    """和 write_text 一样，write_bytes 重新以 wb 打开并清空旧文件。"""

    path = tmp_path / "payload.bin"
    path.write_bytes(b"abcdef")
    path.write_bytes(b"xy")

    assert path.read_bytes() == b"xy"


def test_path_open_exposes_normal_file_modes_and_context_management(tmp_path):
    """open 转交 builtins.open 参数；需要 append/exclusive 等模式时用它而非 read/write 便利方法。"""

    path = tmp_path / "events.txt"

    with path.open("x", encoding="utf-8") as stream:
        assert stream.write("first\n") == 6
    with path.open("a", encoding="utf-8") as stream:
        stream.write("second\n")
    with path.open("r", encoding="utf-8") as stream:
        assert stream.readlines() == ["first\n", "second\n"]

    with pytest.raises(FileExistsError):
        path.open("x").close()


def test_touch_creates_an_empty_file_and_exist_ok_controls_collision(tmp_path):
    """默认 exist_ok=True 适合确保存在；False 可检测意外覆盖。"""

    path = tmp_path / "marker"

    assert path.touch() is None
    assert path.is_file()
    assert path.read_bytes() == b""
    assert path.touch(exist_ok=True) is None

    with pytest.raises(FileExistsError):
        path.touch(exist_ok=False)


def test_exists_is_file_and_is_dir_distinguish_path_kinds(tmp_path):
    """exists 只说明有对象；后续操作前通常还要区分 regular file 与 directory。"""

    file_path = tmp_path / "file.txt"
    directory = tmp_path / "folder"
    missing = tmp_path / "missing"
    file_path.write_text("x", encoding="utf-8")
    directory.mkdir()

    assert (file_path.exists(), file_path.is_file(), file_path.is_dir()) == (True, True, False)
    assert (directory.exists(), directory.is_file(), directory.is_dir()) == (True, False, True)
    assert (missing.exists(), missing.is_file(), missing.is_dir()) == (False, False, False)


def test_special_file_predicates_are_false_for_regular_files_and_missing_paths(tmp_path):
    """is_socket/is_fifo/device 不因“存在”就成立；缺失路径也统一返回 False。"""

    regular = tmp_path / "regular"
    missing = tmp_path / "missing"
    regular.touch()

    predicates = [Path.is_socket, Path.is_fifo, Path.is_block_device, Path.is_char_device]

    assert all(predicate(regular) is False for predicate in predicates)
    assert all(predicate(missing) is False for predicate in predicates)


def test_iterdir_yields_direct_children_without_dot_entries_or_order_guarantee(tmp_path):
    """系统顺序任意，断言前应按 name 排序；递归需求应使用 glob/rglob。"""

    (tmp_path / "b.txt").touch()
    (tmp_path / "a.txt").touch()
    (tmp_path / "folder").mkdir()

    children = sorted(tmp_path.iterdir(), key=lambda path: path.name)

    assert [path.name for path in children] == ["a.txt", "b.txt", "folder"]
    assert all(path.parent == tmp_path for path in children)


def test_stat_is_looked_up_again_on_each_call(tmp_path):
    """Path 不缓存 stat_result；文件变化后下一次 stat 反映新 size。"""

    path = tmp_path / "growing.bin"
    path.write_bytes(b"abc")
    first = path.stat()
    path.write_bytes(b"abcdefgh")
    second = path.stat()

    assert first.st_size == 3
    assert second.st_size == 8
    assert first is not second


def test_lstat_matches_stat_for_a_non_symlink(tmp_path):
    """普通文件没有“link 本身/target”区别；两种调用看到相同 inode 与 size。"""

    path = tmp_path / "plain.txt"
    path.write_text("plain", encoding="utf-8")

    assert path.stat().st_ino == path.lstat().st_ino
    assert path.stat().st_size == path.lstat().st_size == 5


def test_chmod_changes_permission_bits_on_the_temporary_file(tmp_path):
    """stat().st_mode 还含 file-type bits；用 stat.S_IMODE 只提取 permission 部分。"""

    path = tmp_path / "private.txt"
    path.touch()

    path.chmod(0o600)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_unlink_missing_ok_controls_idempotent_removal(tmp_path):
    """missing_ok=True 类似 rm -f；默认模式让“不该缺失”的数据问题可见。"""

    path = tmp_path / "remove-me.txt"
    path.touch()

    assert path.unlink() is None
    assert not path.exists()
    assert path.unlink(missing_ok=True) is None

    with pytest.raises(FileNotFoundError):
        path.unlink()


def test_unlink_and_rmdir_enforce_file_directory_boundary(tmp_path):
    """unlink 不删除 directory，rmdir 只删除空 directory，递归树需 shutil.rmtree。"""

    directory = tmp_path / "folder"
    directory.mkdir()
    child = directory / "child.txt"
    child.touch()

    with pytest.raises(OSError):
        directory.unlink()
    with pytest.raises(OSError):
        directory.rmdir()

    child.unlink()
    assert directory.rmdir() is None
    assert not directory.exists()


def test_rename_returns_a_new_path_and_moves_the_entry(tmp_path):
    """原 Path 对象不可变，rename 返回指向 target 的新 Path；旧对象仍保存旧文本但已不存在。"""

    source = tmp_path / "before.txt"
    target = tmp_path / "after.txt"
    source.write_text("content", encoding="utf-8")

    returned = source.rename(target)

    assert returned == target
    assert not source.exists()
    assert target.read_text(encoding="utf-8") == "content"


def test_replace_unconditionally_replaces_an_existing_file(tmp_path):
    """replace 明确提供覆盖目标的语义，比依赖 rename 的平台差异更可移植。"""

    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.write_text("new", encoding="utf-8")
    target.write_text("old", encoding="utf-8")

    returned = source.replace(target)

    assert returned == target
    assert target.read_text(encoding="utf-8") == "new"
    assert not source.exists()


def test_resolve_makes_paths_absolute_and_eliminates_dotdot(tmp_path):
    """resolve 是 pathlib 中会消除 ``..`` 的 concrete 方法，并从真实 filesystem 起点形成 absolute。"""

    folder = tmp_path / "folder"
    folder.mkdir()
    path = folder / ".." / "folder" / "file.txt"

    assert path.resolve(strict=False) == folder / "file.txt"
    assert path.resolve(strict=False).is_absolute()


def test_resolve_strict_controls_missing_remainder_handling(tmp_path):
    """strict=False 尽量解析后附上缺失 remainder；True 要求整条路径都真实存在。"""

    missing = tmp_path / "missing" / "child.txt"

    assert missing.resolve(strict=False) == missing
    with pytest.raises(FileNotFoundError):
        missing.resolve(strict=True)


# ``pathlib.Path`` 遍历、模式匹配与链接语义。
#
# glob/rglob 返回无顺序保证的惰性路径迭代器；``**`` 会递归整棵树，生产代码应控制范围。
# symlink 的 ``exists`` 跟随 target，而 ``is_symlink``/lstat 检查 link 本身；hard link
# 则是同一 inode 的另一个目录项。所有链接和遍历案例都局限在 pytest tmp_path。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.pathlib.glob python.pathlib.glob-relative-pattern
# polyglot-covers: python.pathlib.glob-hidden python.pathlib.glob-order
# polyglot-covers: python.pathlib.recursive-glob python.pathlib.rglob
# polyglot-covers: python.pathlib.symlink_to python.pathlib.symlink-argument-order
# polyglot-covers: python.pathlib.readlink python.pathlib.relative-symlink-target
# polyglot-covers: python.pathlib.broken-symlink python.pathlib.exists-follows-symlink
# polyglot-covers: python.pathlib.stat-follow-symlinks python.pathlib.python310-stat-follow
# polyglot-covers: python.pathlib.lstat python.pathlib.symlink-file-dir-predicates
# polyglot-covers: python.pathlib.resolve-symlink python.pathlib.resolve-loop
# polyglot-covers: python.pathlib.hardlink_to python.pathlib.python310-hardlink
# polyglot-covers: python.pathlib.samefile python.pathlib.hardlink-shared-content
# polyglot-covers: python.pathlib.link_to python.pathlib.deprecated-link-to
# polyglot-covers: python.pathlib.rename-relative-target python.pathlib.rename-cwd-boundary




def build_tree(root):
    """创建小型固定树，避免测试依赖仓库或真实用户目录。"""

    (root / "src" / "package").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "src" / "main.py").write_text("main", encoding="utf-8")
    (root / "src" / "package" / "model.py").write_text("model", encoding="utf-8")
    (root / "src" / "package" / "data.json").write_text("{}", encoding="utf-8")
    (root / "docs" / "conf.py").write_text("conf", encoding="utf-8")
    (root / "README.md").write_text("readme", encoding="utf-8")


def relative_strings(paths, root):
    """排序前转为 POSIX relative 文本，让断言不依赖目录枚举顺序。"""

    return sorted(path.relative_to(root).as_posix() for path in paths)


def test_glob_matches_a_relative_pattern_below_the_path(tmp_path):
    """pattern 以 Path 为搜索根；``src/*.py`` 只检查这一层，不进入 package。"""

    build_tree(tmp_path)

    assert relative_strings(tmp_path.glob("src/*.py"), tmp_path) == ["src/main.py"]
    assert relative_strings(tmp_path.glob("*/*.py"), tmp_path) == ["docs/conf.py", "src/main.py"]


def test_path_glob_includes_dotfiles_for_star_patterns(tmp_path):
    """与 glob 模块的传统 shell 规则不同，pathlib 的 ``*`` 会匹配以点开头的名称。"""

    (tmp_path / ".env").touch()
    (tmp_path / "visible.txt").touch()

    assert {path.name for path in tmp_path.glob("*")} == {".env", "visible.txt"}


def test_glob_results_should_be_sorted_when_order_matters(tmp_path):
    """文件系统枚举顺序不属于 API；测试或 UI 要求稳定顺序时由调用者显式 sorted。"""

    for name in ["c.txt", "a.txt", "b.txt"]:
        (tmp_path / name).touch()

    assert [path.name for path in sorted(tmp_path.glob("*.txt"))] == ["a.txt", "b.txt", "c.txt"]


def test_glob_rejects_an_absolute_pattern(tmp_path):
    """Path 自身已经提供搜索 root，pattern 必须 relative；absolute pattern 会产生歧义。"""

    with pytest.raises(NotImplementedError):
        list(tmp_path.glob("/absolute/*.py"))


def test_double_star_recurses_through_descendant_directories(tmp_path):
    """``**`` 可跨任意层级；大目录树可能昂贵，不能把它当无成本 selector。"""

    build_tree(tmp_path)

    assert relative_strings(tmp_path.glob("**/*.py"), tmp_path) == [
        "docs/conf.py",
        "src/main.py",
        "src/package/model.py",
    ]


def test_rglob_is_glob_with_a_double_star_prefix(tmp_path):
    """rglob('*.py') 与 glob('**/*.py') 在同一 root 下表达相同递归匹配。"""

    build_tree(tmp_path)

    assert relative_strings(tmp_path.rglob("*.py"), tmp_path) == relative_strings(
        tmp_path.glob("**/*.py"), tmp_path
    )


def test_symlink_to_uses_link_path_as_self_and_target_as_argument(tmp_path):
    """调用顺序是 link.symlink_to(target)，与 os.symlink(target, link) 正好相反。"""

    target = tmp_path / "target.txt"
    link = tmp_path / "shortcut.txt"
    target.write_text("content", encoding="utf-8")

    assert link.symlink_to(target) is None
    assert link.is_symlink()
    assert link.read_text(encoding="utf-8") == "content"
    assert link.resolve() == target


def test_relative_symlink_target_is_resolved_from_the_link_parent(tmp_path):
    """readlink 保留链接中记录的 relative 文本；访问时从 link 所在目录解释它。"""

    target = tmp_path / "target.txt"
    links = tmp_path / "links"
    links.mkdir()
    target.write_text("content", encoding="utf-8")
    link = links / "shortcut.txt"

    link.symlink_to(Path("..") / "target.txt")

    assert link.readlink() == Path("../target.txt")
    assert link.resolve() == target
    assert link.read_text(encoding="utf-8") == "content"


def test_readlink_on_a_regular_file_raises_oserror(tmp_path):
    """readlink 只读取 link payload，不是读取普通文件内容的另一种拼写。"""

    regular = tmp_path / "plain.txt"
    regular.touch()

    with pytest.raises(OSError):
        regular.readlink()


def test_broken_symlink_exists_false_but_is_symlink_true(tmp_path):
    """exists 跟随 target，broken target 因而为 False；link directory entry 本身仍真实存在。"""

    link = tmp_path / "broken"
    link.symlink_to("missing-target")

    assert link.exists() is False
    assert link.is_file() is False
    assert link.is_dir() is False
    assert link.is_symlink() is True
    assert link.readlink() == Path("missing-target")


def test_stat_follow_symlinks_false_matches_lstat_in_python_310(tmp_path):
    """3.10 新增 follow_symlinks；False 观察 link inode，默认 True 观察 target。"""

    target = tmp_path / "target.txt"
    link = tmp_path / "link.txt"
    target.write_text("target content", encoding="utf-8")
    link.symlink_to(target)

    followed = link.stat()
    not_followed = link.stat(follow_symlinks=False)

    assert followed.st_ino == target.stat().st_ino
    assert not_followed.st_ino == link.lstat().st_ino
    assert stat.S_ISREG(followed.st_mode)
    assert stat.S_ISLNK(not_followed.st_mode)


def test_symlink_to_directory_is_both_a_symlink_and_directory_view(tmp_path):
    """is_symlink 检查 entry，is_dir 默认跟随 target；两个 predicate 可以同时为 True。"""

    target = tmp_path / "target-dir"
    link = tmp_path / "dir-link"
    target.mkdir()
    link.symlink_to(target, target_is_directory=True)

    assert link.is_symlink() is True
    assert link.is_dir() is True
    assert link.is_file() is False


def test_resolve_follows_a_symlink_chain_and_eliminates_dotdot(tmp_path):
    """resolve 同时做 absolute、symlink resolution 和 ``..`` 消除。"""

    target = tmp_path / "data" / "target.txt"
    target.parent.mkdir()
    target.touch()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.symlink_to(Path("data") / "target.txt")
    second.symlink_to(Path("data") / ".." / "first")

    assert second.resolve(strict=True) == target


def test_resolve_detects_a_symbolic_link_loop(tmp_path):
    """循环链接没有 canonical target，3.10 用 RuntimeError 报告而不是无限遍历。"""

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.symlink_to(second.name)
    second.symlink_to(first.name)

    with pytest.raises(RuntimeError):
        first.resolve()


def test_python_310_hardlink_to_creates_another_name_for_the_same_file(tmp_path):
    """3.10 的 link.hardlink_to(target) 与 symlink_to 保持同样 self/argument 顺序。"""

    target = tmp_path / "target.txt"
    link = tmp_path / "hard-link.txt"
    target.write_text("original", encoding="utf-8")

    assert link.hardlink_to(target) is None
    assert link.samefile(target)
    assert link.stat().st_ino == target.stat().st_ino


def test_hard_links_share_file_content_and_metadata(tmp_path):
    """hard link 不是内容副本；从任一名称覆盖文件，另一名称立即看到相同 inode 内容。"""

    target = tmp_path / "target.txt"
    link = tmp_path / "hard-link.txt"
    target.write_text("before", encoding="utf-8")
    link.hardlink_to(target)

    link.write_text("after", encoding="utf-8")

    assert target.read_text(encoding="utf-8") == "after"
    assert target.samefile(link)


def test_samefile_uses_filesystem_identity_not_path_text(tmp_path):
    """相同文本显然 samefile，hard link 文本不同也 samefile；缺失输入会抛 OSError。"""

    target = tmp_path / "target.txt"
    alias = tmp_path / "alias.txt"
    target.touch()
    alias.hardlink_to(target)

    assert target.samefile(target) is True
    assert target.samefile(alias) is True

    with pytest.raises(OSError):
        target.samefile(tmp_path / "missing")


def test_deprecated_link_to_has_reversed_and_confusing_argument_order(tmp_path):
    """3.10 保留 source.link_to(link) 但已弃用；新代码应写 link.hardlink_to(source)。"""

    source = tmp_path / "source.txt"
    legacy_link = tmp_path / "legacy-link.txt"
    source.touch()

    with pytest.warns(DeprecationWarning):
        source.link_to(legacy_link)

    assert source.samefile(legacy_link)


def test_relative_rename_target_is_interpreted_from_cwd_not_source_parent(tmp_path, monkeypatch):
    """target='new.txt' 相对当前工作目录，而不是 self.parent；这是移动文件时的常见坑。"""

    nested = tmp_path / "nested"
    nested.mkdir()
    source = nested / "source.txt"
    source.write_text("content", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    returned = source.rename("new.txt")

    assert returned == Path("new.txt")
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "content"
    assert not (nested / "new.txt").exists()
