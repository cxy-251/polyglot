"""文件、目录、元数据与链接。

共同问题：如何创建和读取文件；目录遍历返回什么；元数据描述链接还是目标；
硬链接与符号链接共享哪些身份。
"""

# polyglot-family: files_paths_and_streams
# polyglot-concept: file_directory_metadata_and_links
# polyglot-related: languages/python/stdlib/030-035_file_and_directory_access/
# polyglot-related+: test_030_pathlib_complete_pure_paths_io_traversal_and_links.py

import os


def test_file_lifecycle_and_metadata_use_temporary_directory(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("你好", encoding="utf-8")

    assert path.read_text(encoding="utf-8") == "你好"
    assert path.stat().st_size == len("你好".encode())
    path.rename(tmp_path / "renamed.txt")
    assert not path.exists()


def test_directory_iteration_returns_entries_without_recursive_descent(tmp_path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "note.txt").write_text("value", encoding="utf-8")

    entries = {entry.name: entry for entry in os.scandir(tmp_path)}

    assert entries["nested"].is_dir()
    assert entries["note.txt"].is_file()


def test_hard_link_names_share_the_same_file_identity(tmp_path):
    original = tmp_path / "original.txt"
    alias = tmp_path / "alias.txt"
    original.write_text("value", encoding="utf-8")
    os.link(original, alias)

    assert os.path.samefile(original, alias)
    alias.write_text("changed", encoding="utf-8")
    assert original.read_text(encoding="utf-8") == "changed"


def test_lstat_observes_symbolic_link_while_stat_follows_it(tmp_path):
    target = tmp_path / "target.txt"
    link = tmp_path / "link.txt"
    target.write_text("value", encoding="utf-8")
    link.symlink_to(target)

    assert link.lstat().st_ino != target.stat().st_ino
    assert link.stat().st_ino == target.stat().st_ino
