"""路径规范化与解析。

共同问题：路径操作是纯词法计算还是访问文件系统；相对路径以什么为基准；
规范化、绝对化与解析符号链接是否等价。
"""

# polyglot-family: files_paths_and_streams
# polyglot-concept: path_normalization_and_resolution
# polyglot-related: languages/python/stdlib/030-035_file_and_directory_access/
# polyglot-related+: test_030_pathlib_complete_pure_paths_io_traversal_and_links.py

import os
from pathlib import Path, PurePosixPath


def test_pure_path_keeps_parent_segments_without_touching_filesystem():
    path = PurePosixPath("workspace") / ".." / "result.txt"

    assert str(path) == "workspace/../result.txt"
    assert os.path.normpath(path) == "result.txt"


def test_resolve_makes_path_absolute_and_collapses_parent_segments(tmp_path):
    nested = tmp_path / "folder" / ".." / "result.txt"

    assert nested.resolve() == tmp_path / "result.txt"


def test_resolve_follows_symbolic_links(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(target, target_is_directory=True)

    assert link.resolve() == target
    assert PurePosixPath(str(link)) != PurePosixPath(str(target))


def test_path_join_replaces_prefix_when_later_part_is_absolute():
    assert os.path.join("/base", "child") == "/base/child"
    assert os.path.join("/base", "/replacement") == "/replacement"

    # Windows 的驱动器、根目录与分隔符规则不同，不能把 POSIX 字符串结果当成跨平台规范。
