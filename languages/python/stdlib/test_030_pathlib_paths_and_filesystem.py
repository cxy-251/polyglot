"""030｜``pathlib`` 的纯路径语义与临时文件系统工作流示例。

PurePath 只做路径字符串的词法操作，不查询磁盘；Path 在对应平台 flavor 上增加
stat、读写、枚举、重命名等系统调用。本文件所有有副作用案例均限制在 pytest
tmp_path 内。

内容基于 Python 3.10 pathlib 和 os.PathLike 文档。built-in open 的 text/binary
基础已在 029 展示；当前文件尚未经过 pytest 验证。
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
