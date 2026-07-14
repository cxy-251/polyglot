"""034｜``fnmatch`` / ``glob`` / ``filecmp`` 模式与比较工作流示例。

fnmatch 对一个名称字符串应用 shell-style pattern；glob 按路径段枚举文件系统；
filecmp 则按 stat 签名或实际字节比较文件和目录树。三者层次不同，不能因为都出现
通配符/文件名就混用。

内容基于 Python 3.10 fnmatch、glob、filecmp 文档。所有磁盘案例均限制在 pytest
tmp_path；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.fnmatch python.fnmatch.fnmatch
# polyglot-covers: python.fnmatch.fnmatchcase python.fnmatch.filter
# polyglot-covers: python.fnmatch.translate python.fnmatch.pattern-language
# polyglot-covers: python.stdlib.glob python.glob.glob python.glob.iglob
# polyglot-covers: python.glob.recursive python.glob.root_dir python.glob.dir_fd
# polyglot-covers: python.glob.hidden-files python.glob.escape
# polyglot-covers: python.stdlib.filecmp python.filecmp.cmp python.filecmp.clear_cache
# polyglot-covers: python.filecmp.cmpfiles python.filecmp.dircmp
# polyglot-covers: python.filecmp.dircmp.subdirs python.filecmp.dircmp.reports

import filecmp
import fnmatch
import glob
import os
from pathlib import Path
import re

import pytest


def test_fnmatch_shell_tokens_are_not_regular_expression_syntax():
    """``* ? [seq] [!seq]`` 是文件名模式，其他正则元字符通常只是普通字符。"""

    assert fnmatch.fnmatchcase("report7.csv", "report?.csv")
    assert not fnmatch.fnmatchcase("report12.csv", "report?.csv")
    assert fnmatch.fnmatchcase("image3.png", "image[0-5].png")
    assert not fnmatch.fnmatchcase("image8.png", "image[0-5].png")
    assert fnmatch.fnmatchcase("item-x.txt", "item-[!0-9].txt")
    assert not fnmatch.fnmatchcase("item-7.txt", "item-[!0-9].txt")

    # 正则中的 `+` 在 fnmatch 没有“重复”含义。
    assert fnmatch.fnmatchcase("a+.txt", "a+.txt")
    assert not fnmatch.fnmatchcase("aaaa.txt", "a+.txt")


def test_fnmatchcase_is_exact_while_fnmatch_applies_platform_normcase():
    """跨平台精确大小写规则使用 fnmatchcase；fnmatch 跟随 os.path.normcase。"""

    name = "README.TXT"
    pattern = "readme.txt"

    assert not fnmatch.fnmatchcase(name, pattern)
    assert fnmatch.fnmatch(name, pattern) == fnmatch.fnmatchcase(
        os.path.normcase(name),
        os.path.normcase(pattern),
    )

    # 不直接断言 fnmatch 的大小写结果，因为 Windows/POSIX normcase 契约不同。


def test_fnmatch_filter_preserves_input_order_and_translate_builds_regex():
    """filter 批量筛选；translate 可把同一 shell pattern 交给 re 引擎复用。"""

    names = ["b.py", "notes.txt", "a.py", "README.md"]

    assert fnmatch.filter(names, "*.py") == ["b.py", "a.py"]

    expression = fnmatch.translate("data-??.csv")
    matcher = re.compile(expression)

    assert matcher.match("data-01.csv")
    assert not matcher.match("data-1.csv")
    assert not matcher.match("prefix-data-01.csv")

    # translate 返回锚定表达式；调用者无需再手工拼 `^...$`。


def test_fnmatch_star_can_cross_separator_because_it_only_sees_a_string():
    """fnmatch 不把路径分隔符当特殊边界；glob 才逐路径段处理。"""

    path_text = "src/package/module.py"

    assert fnmatch.fnmatchcase(path_text, "*.py")
    assert fnmatch.fnmatchcase(path_text, "src*module.py")

    # 需要“当前目录下 *.py”时使用 glob/pathlib.glob，而不是对完整路径做 fnmatch。


def test_glob_and_iglob_return_matching_paths_without_promised_order(tmp_path):
    """glob 返回 list，iglob 返回一次性 iterator；两者结果都应显式排序。"""

    (tmp_path / "b.py").write_text("b", encoding="ascii")
    (tmp_path / "a.py").write_text("a", encoding="ascii")
    (tmp_path / "notes.txt").write_text("notes", encoding="ascii")

    pattern = str(tmp_path / "*.py")
    eager = sorted(Path(path).name for path in glob.glob(pattern))
    lazy = glob.iglob(pattern)

    assert eager == ["a.py", "b.py"]
    assert sorted(Path(path).name for path in lazy) == ["a.py", "b.py"]
    assert list(lazy) == []


def test_glob_star_excludes_leading_dot_unless_pattern_starts_with_dot(tmp_path):
    """与 fnmatch 不同，glob 的通配段默认不匹配 dotfile。"""

    (tmp_path / "visible.txt").write_text("visible", encoding="ascii")
    (tmp_path / ".hidden.txt").write_text("hidden", encoding="ascii")

    visible = sorted(Path(path).name for path in glob.glob(str(tmp_path / "*")))
    hidden = sorted(Path(path).name for path in glob.glob(str(tmp_path / ".*")))

    assert visible == ["visible.txt"]
    assert hidden == [".hidden.txt"]
    assert fnmatch.fnmatchcase(".hidden.txt", "*")


def test_recursive_double_star_needs_recursive_true_for_deep_matches(tmp_path):
    """``**`` 只有 recursive=True 时才跨任意层级。"""

    (tmp_path / "src" / "package").mkdir(parents=True)
    (tmp_path / "root.py").write_text("root", encoding="ascii")
    (tmp_path / "src" / "module.py").write_text("module", encoding="ascii")
    (tmp_path / "src" / "package" / "deep.py").write_text(
        "deep",
        encoding="ascii",
    )

    recursive = sorted(
        glob.glob("**/*.py", root_dir=tmp_path, recursive=True)
    )
    non_recursive = sorted(
        glob.glob("**/*.py", root_dir=tmp_path, recursive=False)
    )

    assert recursive == ["root.py", "src/module.py", "src/package/deep.py"]
    assert "src/package/deep.py" not in non_recursive


def test_multiple_double_star_segments_should_be_deduplicated_by_caller(tmp_path):
    """文档允许多个 ``**`` 在 recursive 模式产生重复路径。"""

    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "b" / "item.txt").write_text("item", encoding="ascii")

    raw = glob.glob(
        "**/**/item.txt",
        root_dir=tmp_path,
        recursive=True,
    )
    unique = sorted(set(raw))

    assert unique == ["a/b/item.txt"]

    # 不能假定 raw 永不重复；若每个文件只能处理一次，应按规范化路径显式去重。


def test_glob_root_dir_returns_relative_paths_without_changing_cwd(tmp_path):
    """Python 3.10 root_dir 给 pattern 一个逻辑根，结果仍按 pattern 形式返回。"""

    (tmp_path / "one.txt").write_text("one", encoding="ascii")
    (tmp_path / "two.py").write_text("two", encoding="ascii")
    original_cwd = Path.cwd()

    matches = sorted(glob.glob("*.txt", root_dir=tmp_path))

    assert matches == ["one.txt"]
    assert Path.cwd() == original_cwd


def test_glob_dir_fd_anchors_relative_lookup_to_open_directory(tmp_path):
    """dir_fd 让相对 pattern 基于已打开目录描述符，避免临时切换 cwd。"""

    (tmp_path / "a.txt").write_text("a", encoding="ascii")
    (tmp_path / "b.py").write_text("b", encoding="ascii")
    descriptor = os.open(tmp_path, os.O_RDONLY)

    try:
        assert sorted(glob.glob("*.txt", dir_fd=descriptor)) == ["a.txt"]
    finally:
        os.close(descriptor)


def test_glob_escape_matches_literal_pattern_metacharacters(tmp_path):
    """escape 把文件名中的 ``? * [`` 转成 glob 可按字面匹配的 pattern。"""

    filename = "[draft]?.txt"
    (tmp_path / filename).write_text("draft", encoding="ascii")

    escaped = glob.escape(filename)
    matches = sorted(glob.glob(escaped, root_dir=tmp_path))

    assert matches == [filename]
    assert escaped != filename


def test_glob_includes_broken_symlink_when_name_matches(tmp_path):
    """glob 枚举目录项，因此匹配的 broken symlink 也会出现在结果中。"""

    broken = tmp_path / "broken.txt"
    broken.symlink_to("missing.txt")

    matches = sorted(Path(path).name for path in glob.glob(str(tmp_path / "*.txt")))

    assert matches == ["broken.txt"]
    assert os.path.lexists(broken)
    assert not broken.exists()


def test_filecmp_shallow_can_treat_same_stat_signature_as_equal(tmp_path):
    """shallow=True 在 type/size/mtime 相同时不读取内容。"""

    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"AAAA")
    right.write_bytes(b"BBBB")
    common_ns = 1_600_000_000_000_000_000
    os.utime(left, ns=(common_ns, common_ns))
    os.utime(right, ns=(common_ns, common_ns))
    filecmp.clear_cache()

    assert filecmp.cmp(left, right, shallow=True) is True
    assert filecmp.cmp(left, right, shallow=False) is False

    # 内容完整性、构建缓存等需求必须 shallow=False 或使用内容摘要。


def test_filecmp_cache_can_be_stale_until_clear_cache(tmp_path):
    """deep compare 结果也会按路径/stat 签名缓存；快速同签名改写可命中旧结果。"""

    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"AAAA")
    right.write_bytes(b"AAAA")
    common_ns = 1_600_000_000_000_000_000
    os.utime(left, ns=(common_ns, common_ns))
    os.utime(right, ns=(common_ns, common_ns))
    filecmp.clear_cache()

    assert filecmp.cmp(left, right, shallow=False) is True

    right.write_bytes(b"BBBB")
    os.utime(right, ns=(common_ns, common_ns))

    assert filecmp.cmp(left, right, shallow=False) is True

    filecmp.clear_cache()
    assert filecmp.cmp(left, right, shallow=False) is False


def test_cmpfiles_partitions_match_mismatch_and_error_names(tmp_path):
    """cmpfiles 只比较显式 common 名称，并把无法比较项单独返回。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "same.txt").write_text("same", encoding="ascii")
    (right / "same.txt").write_text("same", encoding="ascii")
    (left / "different.txt").write_text("left", encoding="ascii")
    (right / "different.txt").write_text("right-value", encoding="ascii")
    (left / "missing.txt").write_text("only left", encoding="ascii")

    matches, mismatches, errors = filecmp.cmpfiles(
        left,
        right,
        ["same.txt", "different.txt", "missing.txt"],
        shallow=False,
    )

    assert sorted(matches) == ["same.txt"]
    assert sorted(mismatches) == ["different.txt"]
    assert sorted(errors) == ["missing.txt"]


def _build_dircmp_trees(tmp_path):
    """构造包含独有、相同、不同、类型冲突和共同子目录的比较树。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    (left / "nested").mkdir(parents=True)
    (right / "nested").mkdir(parents=True)

    (left / "left-only.txt").write_text("left", encoding="ascii")
    (right / "right-only.txt").write_text("right", encoding="ascii")
    (left / "same.txt").write_text("same", encoding="ascii")
    (right / "same.txt").write_text("same", encoding="ascii")
    (left / "different.txt").write_text("x", encoding="ascii")
    (right / "different.txt").write_text("much longer", encoding="ascii")

    (left / "type-conflict").write_text("file", encoding="ascii")
    (right / "type-conflict").mkdir()

    (left / "nested" / "same.txt").write_text("nested", encoding="ascii")
    (right / "nested" / "same.txt").write_text("nested", encoding="ascii")
    (left / "nested" / "different.txt").write_text("a", encoding="ascii")
    (right / "nested" / "different.txt").write_text("different", encoding="ascii")

    (left / "ignored.txt").write_text("left ignored", encoding="ascii")
    (right / "ignored.txt").write_text("right ignored", encoding="ascii")
    return left, right


def test_dircmp_classifies_names_files_directories_and_type_conflicts(tmp_path):
    """dircmp 先比较目录项类型，再对共同普通文件做 shallow 内容分类。"""

    left, right = _build_dircmp_trees(tmp_path)
    comparison = filecmp.dircmp(left, right, ignore=["ignored.txt"])

    assert comparison.left_only == ["left-only.txt"]
    assert comparison.right_only == ["right-only.txt"]
    assert sorted(comparison.common) == [
        "different.txt",
        "nested",
        "same.txt",
        "type-conflict",
    ]
    assert comparison.common_dirs == ["nested"]
    assert comparison.common_files == ["different.txt", "same.txt"]
    assert comparison.common_funny == ["type-conflict"]
    assert comparison.same_files == ["same.txt"]
    assert comparison.diff_files == ["different.txt"]
    assert comparison.funny_files == []


def test_dircmp_computes_attributes_lazily_and_exposes_recursive_subdirs(tmp_path):
    """访问属性时才执行相应 phase；subdirs 映射到新的 dircmp 对象。"""

    left, right = _build_dircmp_trees(tmp_path)
    comparison = filecmp.dircmp(left, right, ignore=["ignored.txt"])

    assert "same_files" not in vars(comparison)
    assert comparison.same_files == ["same.txt"]
    assert "same_files" in vars(comparison)

    nested = comparison.subdirs["nested"]
    assert nested.same_files == ["same.txt"]
    assert nested.diff_files == ["different.txt"]


def test_dircmp_reports_human_readable_summary_and_recursive_closures(tmp_path, capsys):
    """report 系列打印摘要；程序逻辑应读取结构化属性而非解析文本。"""

    left, right = _build_dircmp_trees(tmp_path)
    comparison = filecmp.dircmp(left, right, ignore=["ignored.txt"])

    assert comparison.report() is None
    shallow_output = capsys.readouterr().out
    assert "diff" in shallow_output
    assert "left-only.txt" in shallow_output

    assert comparison.report_partial_closure() is None
    partial_output = capsys.readouterr().out
    assert "nested" in partial_output

    assert comparison.report_full_closure() is None
    full_output = capsys.readouterr().out
    assert "nested" in full_output
    assert "different.txt" in full_output

    # report 输出面向人且格式可演进；自动化应使用 left_only/diff_files/subdirs 等属性。
