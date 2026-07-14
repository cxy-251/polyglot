"""091｜``pathlib.Path`` 遍历、模式匹配与链接语义。

glob/rglob 返回无顺序保证的惰性路径迭代器；``**`` 会递归整棵树，生产代码应控制范围。
symlink 的 ``exists`` 跟随 target，而 ``is_symlink``/lstat 检查 link 本身；hard link
则是同一 inode 的另一个目录项。所有链接和遍历案例都局限在 pytest tmp_path。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

from pathlib import Path
import stat

import pytest


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
