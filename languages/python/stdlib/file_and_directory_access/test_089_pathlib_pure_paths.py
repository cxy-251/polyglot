"""089｜``pathlib`` 纯路径 flavour 与词法变换。

PurePosixPath/PureWindowsPath 只做词法计算，可在任意宿主系统上安全研究另一平台路径。
它们会折叠冗余分隔符和单点，却刻意保留 ``..``，因为符号链接会让天真归一化改变含义。
路径不可变、可哈希，并实现 os.PathLike；大小写与 drive/root 规则由 flavour 决定。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.pathlib.PurePath python.pathlib.PurePosixPath python.pathlib.PureWindowsPath
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

import os
from pathlib import PurePath, PurePosixPath, PureWindowsPath

import pytest


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
