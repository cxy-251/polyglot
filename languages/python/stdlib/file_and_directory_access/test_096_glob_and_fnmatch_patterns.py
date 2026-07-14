"""096｜``glob`` 路径展开与 ``fnmatch`` 单名称匹配。

两者共享 shell-style wildcard，但边界不同：``glob`` 按 path segment 扫描文件系统并对
leading dot 有特殊规则；``fnmatch`` 只比较给定字符串，separator 与 leading dot 都是普通
字符。结果顺序来自文件系统，递归 ``**`` 还可能昂贵、沿目录 symlink 重复发现内容。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import fnmatch
import glob
import os
from pathlib import Path
import re

import pytest


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
