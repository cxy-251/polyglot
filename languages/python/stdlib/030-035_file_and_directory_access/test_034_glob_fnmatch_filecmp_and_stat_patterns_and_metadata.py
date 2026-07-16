"""034｜``fnmatch`` / ``glob`` / ``filecmp`` 模式与比较工作流示例。

fnmatch 对一个名称字符串应用 shell-style pattern；glob 按路径段枚举文件系统；
filecmp 则按 stat 签名或实际字节比较文件和目录树。三者层次不同，不能因为都出现
通配符/文件名就混用。

内容基于 Python 3.10 fnmatch、glob、filecmp 文档。所有磁盘案例均限制在 pytest
tmp_path。
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
import stat

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


# ``glob`` 路径展开与 ``fnmatch`` 单名称匹配。
#
# 两者共享 shell-style wildcard，但边界不同：``glob`` 按 path segment 扫描文件系统并对
# leading dot 有特殊规则；``fnmatch`` 只比较给定字符串，separator 与 leading dot 都是普通
# 字符。结果顺序来自文件系统，递归 ``**`` 还可能昂贵、沿目录 symlink 重复发现内容。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.glob.glob python.glob.star python.glob.question
# polyglot-covers: python.glob.character-range python.glob.arbitrary-order
# polyglot-covers: python.glob.hidden-files python.glob.explicit-leading-dot
# polyglot-covers: python.glob.no-tilde-expansion python.glob.no-variable-expansion
# polyglot-covers: python.glob.escape python.glob.literal-metacharacters
# polyglot-covers: python.glob.absolute-pattern python.glob.relative-result
# polyglot-covers: python.glob.broken-symlink python.glob.lexical-result
# polyglot-covers: python.glob.recursive python.glob.double-star-zero-or-more
# polyglot-covers: python.glob.recursive-disabled python.glob.trailing-separator
# polyglot-covers: python.glob.multiple-double-star-duplicates
# polyglot-covers: python.glob.symlink-directory-recursion
# polyglot-covers: python.glob.iglob python.glob.iterator
# polyglot-covers: python.glob.python310-root-dir python.glob.no-chdir
# polyglot-covers: python.glob.python310-dir-fd python.glob.bytes-result
# polyglot-covers: python.fnmatch.fnmatch python.fnmatch.shell-wildcards
# polyglot-covers: python.fnmatch.separator-is-ordinary python.fnmatch.dot-is-ordinary
# polyglot-covers: python.fnmatch.fnmatchcase python.fnmatch.normcase
# polyglot-covers: python.fnmatch.filter python.fnmatch.filter-order
# polyglot-covers: python.fnmatch.translate python.fnmatch.regex-anchor
# polyglot-covers: python.fnmatch.literal-brackets python.fnmatch.backslash-is-not-escape
# polyglot-covers: python.fnmatch.bytes python.fnmatch.mixed-types




def test_glob_star_question_and_character_ranges_match_path_segments(tmp_path):
    """pattern 是 shell wildcard 而非 regex；结果没有排序契约，所以用集合比较。"""

    for name in ("1.gif", "2.txt", "card.gif", "12.gif"):
        (tmp_path / name).touch()

    assert set(glob.glob("*.gif", root_dir=tmp_path)) == {"1.gif", "card.gif", "12.gif"}
    assert set(glob.glob("?.gif", root_dir=tmp_path)) == {"1.gif"}
    assert set(glob.glob("[0-9].*", root_dir=tmp_path)) == {"1.gif", "2.txt"}


def test_glob_requires_an_explicit_leading_dot_for_hidden_names(tmp_path):
    """``*`` 不跨过 segment 开头的 dot；这与 fnmatch 和 Path.glob 的规则不同。"""

    (tmp_path / "visible.txt").touch()
    (tmp_path / ".hidden.txt").touch()

    assert glob.glob("*.txt", root_dir=tmp_path) == ["visible.txt"]
    assert glob.glob(".*.txt", root_dir=tmp_path) == [".hidden.txt"]
    assert fnmatch.fnmatch(".hidden.txt", "*.txt") is True


def test_glob_does_not_expand_tilde_or_environment_variables(tmp_path, monkeypatch):
    """``~`` 与 ``$NAME`` 只是 directory names；需要时先调用 expanduser/expandvars。"""

    literal_tilde = tmp_path / "~"
    literal_variable = tmp_path / "$DATA"
    literal_tilde.mkdir()
    literal_variable.mkdir()
    (literal_tilde / "item.txt").touch()
    (literal_variable / "item.txt").touch()
    monkeypatch.setenv("DATA", "somewhere-else")

    assert glob.glob("~/*.txt", root_dir=tmp_path) == ["~/item.txt"]
    assert glob.glob("$DATA/*.txt", root_dir=tmp_path) == ["$DATA/item.txt"]


def test_glob_escape_turns_user_supplied_metacharacters_into_literals(tmp_path):
    """不要手写 backslash：glob 的 literal 技巧是 ``[*]``、``[?]``、``[[]``。"""

    literal_name = "report[1]?.txt"
    (tmp_path / literal_name).touch()
    (tmp_path / "report11x.txt").touch()
    escaped = glob.escape(literal_name)

    assert escaped == "report[[]1][?].txt"
    assert glob.glob(escaped, root_dir=tmp_path) == [literal_name]


def test_absolute_pattern_returns_absolute_paths_while_root_dir_keeps_results_relative(tmp_path):
    """root_dir 改变搜索参照点但不把它拼入 relative result，适合可搬移 manifest。"""

    nested = tmp_path / "assets"
    nested.mkdir()
    file_path = nested / "logo.svg"
    file_path.touch()

    absolute_matches = glob.glob(str(tmp_path / "assets" / "*.svg"))
    relative_matches = glob.glob("assets/*.svg", root_dir=tmp_path)

    assert absolute_matches == [str(file_path)]
    assert relative_matches == [os.path.join("assets", "logo.svg")]


def test_glob_includes_broken_symlink_directory_entries(tmp_path):
    """匹配结果是 pathname，不保证 target 存在；消费前按需求选择 exists 或 lexists。"""

    broken = tmp_path / "broken.txt"
    broken.symlink_to("missing.txt")

    assert glob.glob("*.txt", root_dir=tmp_path) == ["broken.txt"]
    assert broken.exists() is False
    assert os.path.lexists(broken) is True


def test_recursive_double_star_matches_zero_or_more_directories(tmp_path):
    """``**/*.txt`` 同时命中 root 文件和任意深度文件；必须传 recursive=True 才有此语义。"""

    (tmp_path / "root.txt").touch()
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "one.txt").touch()
    (tmp_path / "a" / "b" / "two.txt").touch()

    matches = set(glob.glob("**/*.txt", root_dir=tmp_path, recursive=True))

    assert matches == {
        "root.txt",
        os.path.join("a", "one.txt"),
        os.path.join("a", "b", "two.txt"),
    }


def test_double_star_without_recursive_flag_is_just_one_star_segment(tmp_path):
    """忘记 recursive=True 不会报错；``**`` 退化为普通 ``*``，容易静默漏掉层级。"""

    (tmp_path / "root.txt").touch()
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "one.txt").touch()
    (tmp_path / "a" / "b" / "two.txt").touch()

    assert glob.glob("**/*.txt", root_dir=tmp_path, recursive=False) == [
        os.path.join("a", "one.txt")
    ]


def test_recursive_pattern_ending_in_separator_yields_directories_only(tmp_path):
    """``**/`` 不返回 regular files；不同文件系统的枚举顺序仍不可依赖。"""

    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "item.txt").touch()

    pattern = f".{os.sep}**{os.sep}"
    matches = glob.glob(pattern, root_dir=tmp_path, recursive=True)

    assert all(match.endswith(os.sep) for match in matches)
    assert f".{os.sep}" in matches
    assert os.path.join(".", "a", "") in matches
    assert os.path.join(".", "a", "b", "") in matches
    assert all(not match.endswith("item.txt") for match in matches)


def test_multiple_recursive_segments_can_emit_the_same_path_more_than_once(tmp_path):
    """一个路径可由多个 ``**`` 深度分配得到；需要 manifest identity 时由调用方去重。"""

    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "b" / "item.txt").touch()

    matches = glob.glob("**/**/item.txt", root_dir=tmp_path, recursive=True)

    assert set(matches) == {os.path.join("a", "b", "item.txt")}
    assert len(matches) > len(set(matches))


def test_recursive_glob_follows_directory_symlinks_and_can_revisit_content(tmp_path):
    """真实目录与指向它的 alias 产生两条 pathname；更危险的 symlink cycle 会放大搜索。"""

    real = tmp_path / "real"
    real.mkdir()
    (real / "item.txt").touch()
    (tmp_path / "alias").symlink_to(real, target_is_directory=True)

    matches = set(glob.glob("**/*.txt", root_dir=tmp_path, recursive=True))

    assert matches == {
        os.path.join("real", "item.txt"),
        os.path.join("alias", "item.txt"),
    }


def test_recursive_glob_does_not_descend_into_hidden_directories_by_default(tmp_path):
    """3.10 没有 include_hidden 参数；``**`` 也必须由 dot-leading segment 显式进入隐藏目录。"""

    hidden = tmp_path / ".cache"
    hidden.mkdir()
    (hidden / "item.txt").touch()
    (tmp_path / "visible.txt").touch()

    assert glob.glob("**/*.txt", root_dir=tmp_path, recursive=True) == ["visible.txt"]
    assert glob.glob(".*/**/*.txt", root_dir=tmp_path, recursive=True) == [
        os.path.join(".cache", "item.txt")
    ]


def test_iglob_returns_an_iterator_with_the_same_match_semantics(tmp_path):
    """iglob 不先 materialize 全部结果；若需要重复遍历，调用方必须自己转成 list。"""

    (tmp_path / "a.txt").touch()
    (tmp_path / "b.txt").touch()
    iterator = glob.iglob("*.txt", root_dir=tmp_path)

    assert iter(iterator) is iterator
    assert set(iterator) == {"a.txt", "b.txt"}
    assert list(iterator) == []


def test_root_dir_search_does_not_mutate_process_current_directory(tmp_path, monkeypatch):
    """Python 3.10 root_dir 替代临时 chdir，避免并发代码观察到 process-global cwd 变化。"""

    working_directory = tmp_path / "working"
    search_root = tmp_path / "search"
    working_directory.mkdir()
    search_root.mkdir()
    (search_root / "item.txt").touch()
    monkeypatch.chdir(working_directory)

    assert glob.glob("*.txt", root_dir=search_root) == ["item.txt"]
    assert Path.cwd() == working_directory


def test_dir_fd_makes_relative_searches_relative_to_an_open_directory(tmp_path):
    """Python 3.10 dir_fd 适合 descriptor-relative workflow；调用方仍负责关闭 descriptor。"""

    (tmp_path / "a.txt").touch()
    (tmp_path / "b.bin").touch()
    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        assert glob.glob("*.txt", dir_fd=descriptor) == ["a.txt"]
    finally:
        os.close(descriptor)


def test_glob_bytes_pattern_produces_bytes_pathnames(tmp_path):
    """底层 filesystem bytes 输入保持 bytes 域；不可和文本 root/pattern 随意混用。"""

    file_path = tmp_path / "item.txt"
    file_path.touch()
    pattern = os.fsencode(tmp_path / "*.txt")

    matches = glob.glob(pattern)

    assert matches == [os.fsencode(file_path)]
    assert isinstance(matches[0], bytes)


def test_fnmatch_wildcards_are_not_regular_expressions():
    """``*`` 可匹配任意长度，``?`` 恰好一个字符，``[!seq]`` 表示否定 character class。"""

    assert fnmatch.fnmatchcase("report.txt", "*.txt")
    assert fnmatch.fnmatchcase("a.txt", "?.txt")
    assert not fnmatch.fnmatchcase("ab.txt", "?.txt")
    assert fnmatch.fnmatchcase("item7", "item[0-9]")
    assert fnmatch.fnmatchcase("itemx", "item[!0-9]")
    assert not fnmatch.fnmatchcase("item7", "item[!0-9]")


def test_fnmatch_treats_separator_and_leading_dot_as_ordinary_characters():
    """它匹配传入的整个字符串，不按 pathname segment 拆分，也不保护 hidden basename。"""

    assert fnmatch.fnmatchcase("directory/item.txt", "*.txt")
    assert fnmatch.fnmatchcase(".hidden", "*")


def test_fnmatch_literal_metacharacters_use_bracket_expressions():
    """backslash 没有通用 escape 语义；用 ``[*]`` 与 ``[?]`` 表示 literal wildcard。"""

    assert fnmatch.fnmatchcase("*", "[*]")
    assert fnmatch.fnmatchcase("?", "[?]")
    assert not fnmatch.fnmatchcase("*", r"\*")
    assert fnmatch.fnmatchcase("file[abc", "file[abc")


def test_fnmatchcase_is_always_case_sensitive_while_fnmatch_uses_normcase():
    """fnmatch 的 case behavior 随 native path flavour；fnmatchcase 才是跨平台固定策略。"""

    filename = "README.TXT"
    pattern = "*.txt"

    assert fnmatch.fnmatchcase(filename, pattern) is False
    assert fnmatch.fnmatch(filename, pattern) is fnmatch.fnmatchcase(
        os.path.normcase(filename), os.path.normcase(pattern)
    )


def test_fnmatch_filter_preserves_input_order_and_matches_hidden_names():
    """filter 返回新 list，顺序沿用输入 iterable；它没有 glob 的 leading-dot 例外。"""

    names = (name for name in ["b.txt", ".hidden.txt", "a.py", "a.txt"])

    assert fnmatch.filter(names, "*.txt") == ["b.txt", ".hidden.txt", "a.txt"]


def test_fnmatch_translate_produces_an_anchored_regular_expression():
    """translate 用于把 wildcard 嵌入 regex workflow；生成式样是 implementation detail，不硬编码全文。"""

    expression = re.compile(fnmatch.translate("report-?.txt"))

    assert expression.match("report-1.txt") is not None
    assert expression.match("report-12.txt") is None
    assert expression.match("report-1.txt.bak") is None


def test_fnmatch_supports_bytes_but_rejects_mixed_text_domains():
    """filename 与 pattern 必须同为 str 或同为 ISO-8859-1-compatible bytes 表示。"""

    assert fnmatch.fnmatch(b"item.txt", b"*.txt") is True

    with pytest.raises(TypeError):
        fnmatch.fnmatch(b"item.txt", "*.txt")


# ``filecmp`` 的正确性权衡与 ``stat`` mode 位域解释。
#
# ``filecmp`` 的 shallow=True 比较 stat signature，不是内容证明；deep comparison 也有按 stat
# 失效的 process cache。``stat`` 则把一次 system call 的 mode 拆成 file type、普通权限与
# set-id/sticky 特殊位，适合在不重复访问文件系统的前提下做多项判断。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.filecmp.cmp python.filecmp.shallow-signature
# polyglot-covers: python.filecmp.deep-content python.filecmp.shallow-fallback
# polyglot-covers: python.filecmp.cache python.filecmp.clear-cache
# polyglot-covers: python.filecmp.mtime-resolution-trap
# polyglot-covers: python.filecmp.cmpfiles python.filecmp.match-mismatch-errors
# polyglot-covers: python.filecmp.dircmp python.filecmp.dircmp.lazy-attributes
# polyglot-covers: python.filecmp.dircmp.left-right-only python.filecmp.dircmp.common
# polyglot-covers: python.filecmp.dircmp.common-dirs python.filecmp.dircmp.common-files
# polyglot-covers: python.filecmp.dircmp.common-funny python.filecmp.dircmp.type-mismatch
# polyglot-covers: python.filecmp.dircmp.same-files python.filecmp.dircmp.diff-files
# polyglot-covers: python.filecmp.dircmp.ignore python.filecmp.DEFAULT-IGNORES
# polyglot-covers: python.filecmp.dircmp.subdirs python.filecmp.python310-subclass-preservation
# polyglot-covers: python.filecmp.dircmp.report python.filecmp.dircmp.partial-closure
# polyglot-covers: python.filecmp.dircmp.full-closure
# polyglot-covers: python.stat.S-ISDIR python.stat.S-ISREG python.stat.S-ISLNK
# polyglot-covers: python.stat.S-ISCHR python.stat.S-ISBLK python.stat.S-ISFIFO python.stat.S-ISSOCK
# polyglot-covers: python.stat.S-IFMT python.stat.S-IMODE
# polyglot-covers: python.stat.filemode python.stat.symbolic-permissions
# polyglot-covers: python.stat.permission-masks python.stat.set-id python.stat.sticky-bit
# polyglot-covers: python.stat.stat-result-indexes python.stat.ST-MODE python.stat.ST-SIZE
# polyglot-covers: python.stat.lstat python.stat.symlink-following
# polyglot-covers: python.stat.platform-file-types



def test_shallow_cmp_can_accept_different_content_with_the_same_stat_signature(tmp_path):
    """type、size、mtime 完全相同就直接判 equal；校验内容必须显式 shallow=False。"""

    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"AAAA")
    right.write_bytes(b"BBBB")
    timestamp_ns = 1_234_567_890_000_000_000
    os.utime(left, ns=(timestamp_ns, timestamp_ns))
    os.utime(right, ns=(timestamp_ns, timestamp_ns))

    assert filecmp.cmp(left, right, shallow=True) is True
    assert filecmp.cmp(left, right, shallow=False) is False


def test_shallow_cmp_falls_back_to_content_when_signatures_are_not_equal(tmp_path):
    """shallow 不是“永不读内容”：mtime 不同而 size 相同，会继续做 byte comparison。"""

    left = tmp_path / "left.bin"
    right = tmp_path / "right.bin"
    left.write_bytes(b"same")
    right.write_bytes(b"same")
    os.utime(left, ns=(1_000_000_000, 1_000_000_000))
    os.utime(right, ns=(2_000_000_000, 2_000_000_000))

    assert filecmp.cmp(left, right, shallow=True) is True


def test_cmp_rejects_different_sizes_before_a_full_content_scan(tmp_path):
    """size 不同在 shallow/deep 两种模式下都足以判 mismatch。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.write_bytes(b"short")
    right.write_bytes(b"longer")

    assert filecmp.cmp(left, right, shallow=True) is False
    assert filecmp.cmp(left, right, shallow=False) is False


def test_clear_cache_handles_same_size_same_mtime_rewrites(tmp_path):
    """若 rewrite 落在相同 mtime resolution 且 size 不变，cache key 不变；clear_cache 后才重读。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.write_bytes(b"AAAA")
    right.write_bytes(b"AAAA")
    timestamp_ns = 1_111_111_111_000_000_000
    os.utime(left, ns=(timestamp_ns, timestamp_ns))
    os.utime(right, ns=(timestamp_ns, timestamp_ns))
    filecmp.clear_cache()
    try:
        assert filecmp.cmp(left, right, shallow=False) is True

        right.write_bytes(b"BBBB")
        os.utime(right, ns=(timestamp_ns, timestamp_ns))

        assert filecmp.cmp(left, right, shallow=False) is True
        filecmp.clear_cache()
        assert filecmp.cmp(left, right, shallow=False) is False
    finally:
        filecmp.clear_cache()


def test_cmpfiles_partitions_requested_names_into_three_lists(tmp_path):
    """不存在于任一侧、无权限或其他无法比较项进入 errors，而不是混入 mismatch。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "same.txt").write_text("same", encoding="utf-8")
    (right / "same.txt").write_text("same", encoding="utf-8")
    (left / "different.txt").write_text("left", encoding="utf-8")
    (right / "different.txt").write_text("right", encoding="utf-8")
    (left / "missing.txt").touch()

    match, mismatch, errors = filecmp.cmpfiles(
        left,
        right,
        ["same.txt", "different.txt", "missing.txt"],
        shallow=False,
    )

    assert match == ["same.txt"]
    assert mismatch == ["different.txt"]
    assert errors == ["missing.txt"]


def test_cmpfiles_accepts_relative_names_with_subdirectories(tmp_path):
    """common items 不限 basename；相同 relative route 会分别拼到左右根目录。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    relative = Path("nested") / "item.txt"
    (left / relative).parent.mkdir(parents=True)
    (right / relative).parent.mkdir(parents=True)
    (left / relative).write_text("same", encoding="utf-8")
    (right / relative).write_text("same", encoding="utf-8")

    match, mismatch, errors = filecmp.cmpfiles(
        left, right, [os.fspath(relative)], shallow=False
    )

    assert match == [os.fspath(relative)]
    assert mismatch == []
    assert errors == []


def test_dircmp_computes_lightweight_name_sets_lazily(tmp_path):
    """构造对象不立即做全部递归比较；首次读取 attribute 才运行对应 phase 并缓存结果。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "left-only").touch()
    (right / "right-only").touch()
    (left / "common").touch()
    (right / "common").touch()
    comparison = filecmp.dircmp(left, right)

    assert "left_list" not in comparison.__dict__
    assert comparison.left_only == ["left-only"]
    assert comparison.right_only == ["right-only"]
    assert comparison.common == ["common"]
    assert "left_list" in comparison.__dict__
    assert comparison.left == left
    assert comparison.right == right


def test_dircmp_classifies_common_directories_files_and_type_conflicts(tmp_path):
    """同名但一侧 file、一侧 directory 属于 common_funny，不是 common_files/diff_files。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "directory").mkdir()
    (right / "directory").mkdir()
    (left / "file.txt").touch()
    (right / "file.txt").touch()
    (left / "conflict").touch()
    (right / "conflict").mkdir()
    comparison = filecmp.dircmp(left, right)

    assert comparison.common_dirs == ["directory"]
    assert comparison.common_files == ["file.txt"]
    assert comparison.common_funny == ["conflict"]


def test_dircmp_partitions_comparable_common_files_into_same_and_different(tmp_path):
    """dircmp 固定采用 shallow comparison；让 diff size 不同可避免 timestamp signature 误判。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "same.txt").write_text("same", encoding="utf-8")
    (right / "same.txt").write_text("same", encoding="utf-8")
    (left / "different.txt").write_text("short", encoding="utf-8")
    (right / "different.txt").write_text("a different length", encoding="utf-8")
    comparison = filecmp.dircmp(left, right)

    assert comparison.same_files == ["same.txt"]
    assert comparison.diff_files == ["different.txt"]
    assert comparison.funny_files == []


def test_dircmp_default_and_custom_ignore_names_are_removed_from_lists(tmp_path):
    """DEFAULT_IGNORES 通常排除 VCS/cache 管理目录；自定义 ignore 是完全替换时要保留默认项。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    for root in (left, right):
        (root / ".git").mkdir()
        (root / "generated").mkdir()
        (root / "source").mkdir()

    default_comparison = filecmp.dircmp(left, right)
    custom_comparison = filecmp.dircmp(
        left,
        right,
        ignore=[*filecmp.DEFAULT_IGNORES, "generated"],
    )

    assert ".git" in filecmp.DEFAULT_IGNORES
    assert ".git" not in default_comparison.common
    assert "generated" in default_comparison.common
    assert custom_comparison.common == ["source"]


def test_python_310_subdirs_preserves_a_dircmp_subclass(tmp_path):
    """3.10 起 recursive node 使用 self 的 subclass，便于扩展整棵 comparison tree。"""

    class TaggedDirCmp(filecmp.dircmp):
        pass

    left = tmp_path / "left"
    right = tmp_path / "right"
    (left / "nested").mkdir(parents=True)
    (right / "nested").mkdir(parents=True)
    comparison = TaggedDirCmp(left, right)

    assert isinstance(comparison.subdirs["nested"], TaggedDirCmp)


def test_dircmp_reports_have_current_partial_and_full_recursion_scopes(tmp_path, capsys):
    """report 只看当前层，partial 再看一层，full 才递归到任意深度。"""

    left = tmp_path / "left"
    right = tmp_path / "right"
    (left / "level1" / "level2").mkdir(parents=True)
    (right / "level1" / "level2").mkdir(parents=True)
    (left / "level1" / "level2" / "deep.txt").write_text("left", encoding="utf-8")
    (right / "level1" / "level2" / "deep.txt").write_text(
        "a different length", encoding="utf-8"
    )
    comparison = filecmp.dircmp(left, right)

    comparison.report()
    assert "deep.txt" not in capsys.readouterr().out

    comparison.report_partial_closure()
    assert "deep.txt" not in capsys.readouterr().out

    comparison.report_full_closure()
    assert "deep.txt" in capsys.readouterr().out


def test_stat_and_lstat_give_different_type_modes_for_a_symlink(tmp_path):
    """stat 跟随 target；lstat 描述 link directory entry 本身。"""

    target = tmp_path / "target.txt"
    target.touch()
    link = tmp_path / "link"
    link.symlink_to(target)

    assert stat.S_ISREG(os.stat(link).st_mode)
    assert stat.S_ISLNK(os.lstat(link).st_mode)
    assert not stat.S_ISLNK(os.stat(link).st_mode)


def test_file_type_predicates_decode_the_type_field_without_filesystem_access():
    """已有 st_mode 时可重复检查，不要为每种 is* predicate 重做 system call。"""

    predicates = [
        (stat.S_IFDIR, stat.S_ISDIR),
        (stat.S_IFREG, stat.S_ISREG),
        (stat.S_IFLNK, stat.S_ISLNK),
        (stat.S_IFCHR, stat.S_ISCHR),
        (stat.S_IFBLK, stat.S_ISBLK),
        (stat.S_IFIFO, stat.S_ISFIFO),
        (stat.S_IFSOCK, stat.S_ISSOCK),
    ]

    for type_bits, predicate in predicates:
        assert predicate(type_bits)


def test_ifmt_and_imode_split_type_bits_from_settable_permission_bits():
    """S_IFMT 只留 file type；S_IMODE 留 chmod 可设置的 rwx、set-id 与 sticky bits。"""

    permission_bits = 0o640 | stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX
    mode = stat.S_IFREG | permission_bits

    assert stat.S_IFMT(mode) == stat.S_IFREG
    assert stat.S_IMODE(mode) == permission_bits
    assert stat.S_IFMT(mode) & stat.S_IMODE(mode) == 0


def test_permission_constants_are_composable_bit_masks():
    """owner/group/other masks 可整体提取，也可用单 bit 检查；不要比较完整 st_mode 与 0o644。"""

    permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

    assert permissions == 0o644
    assert permissions & stat.S_IRWXU == 0o600
    assert permissions & stat.S_IRWXG == 0o040
    assert permissions & stat.S_IRWXO == 0o004
    assert permissions & stat.S_IXUSR == 0


def test_legacy_permission_aliases_and_enfmt_share_existing_bits():
    """S_IREAD/IWRITE/IEXEC 是 owner bits 的旧别名；S_ENFMT 与 S_ISGID 复用同一 bit。"""

    assert stat.S_IREAD == stat.S_IRUSR
    assert stat.S_IWRITE == stat.S_IWUSR
    assert stat.S_IEXEC == stat.S_IXUSR
    assert stat.S_ENFMT == stat.S_ISGID


def test_filemode_renders_type_permissions_and_special_execute_states():
    """set-id 位在 execute 存在时显示小写 s/t，否则显示大写 S/T。"""

    assert stat.filemode(stat.S_IFREG | 0o754) == "-rwxr-xr--"
    assert stat.filemode(stat.S_IFDIR | 0o700) == "drwx------"
    assert stat.filemode(stat.S_IFLNK | 0o777) == "lrwxrwxrwx"
    assert stat.filemode(stat.S_IFREG | stat.S_IRUSR | stat.S_ISUID) == "-r-S------"
    assert stat.filemode(stat.S_IFREG | stat.S_IXUSR | stat.S_ISUID) == "---s------"
    assert stat.filemode(stat.S_IFDIR | stat.S_ISVTX) == "d--------T"
    assert stat.filemode(stat.S_IFDIR | stat.S_ISVTX | stat.S_IXOTH) == "d--------t"


def test_stat_symbolic_indexes_map_to_the_portable_ten_tuple(tmp_path):
    """stat_result 还可能有平台扩展属性；前十个 sequence slots 由 ST_* 常量稳定索引。"""

    path = tmp_path / "item.txt"
    path.write_bytes(b"abc")
    metadata = path.stat()

    assert len(tuple(metadata)) == 10
    assert metadata[stat.ST_MODE] == metadata.st_mode
    assert metadata[stat.ST_INO] == metadata.st_ino
    assert metadata[stat.ST_DEV] == metadata.st_dev
    assert metadata[stat.ST_NLINK] == metadata.st_nlink
    assert metadata[stat.ST_UID] == metadata.st_uid
    assert metadata[stat.ST_GID] == metadata.st_gid
    assert metadata[stat.ST_SIZE] == metadata.st_size == 3
    assert metadata[stat.ST_ATIME] == int(metadata.st_atime)
    assert metadata[stat.ST_MTIME] == int(metadata.st_mtime)
    assert metadata[stat.ST_CTIME] == int(metadata.st_ctime)
    # 十槽 tuple 为兼容旧接口保留整数秒；命名属性可能包含亚秒精度。


def test_optional_platform_file_type_constants_are_zero_when_unsupported():
    """door/event port/whiteout 并非所有 OS 都有；不能把常量存在误解为当前 filesystem 支持。"""

    for name in ("S_IFDOOR", "S_IFPORT", "S_IFWHT"):
        value = getattr(stat, name)
        assert isinstance(value, int)
        if value == 0:
            predicate = getattr(stat, name.replace("S_IF", "S_IS"))
            assert predicate(stat.S_IFREG) is False
