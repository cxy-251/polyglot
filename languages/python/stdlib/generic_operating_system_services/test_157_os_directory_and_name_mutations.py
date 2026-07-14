"""157｜``mkdir/rmdir``、remove/unlink、rename/replace 与 recursive renames。

目录和名称变更通常返回 ``None``，失败通过精确的 ``OSError`` subclass 表达。
``replace`` 明确允许覆盖现有文件；``renames`` 还会创建新父目录并尝试清理
旧父目录，因此失败时可能留下部分结构，不适合作为事务接口。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.mkdir python.os.mkdir-existing-error
# polyglot-covers: python.os.rmdir python.os.rmdir-nonempty-error
# polyglot-covers: python.os.remove python.os.unlink python.os.remove-directory-error
# polyglot-covers: python.os.rename python.os.replace
# polyglot-covers: python.os.replace-overwrite python.os.renames
# polyglot-covers: python.os.renames-parent-creation python.os.renames-parent-pruning
# polyglot-covers: python.os.mkfifo python.os.named-pipe-filesystem-node

import os
import stat

import pytest


def test_mkdir_requires_parent_and_rmdir_requires_empty_directory(tmp_path):
    """mkdir 不递归创建 parent；rmdir 只删除空目录，并拒绝非空目录。"""

    folder = tmp_path / "folder"
    assert os.mkdir(folder) is None
    with pytest.raises(FileExistsError):
        os.mkdir(folder)
    with pytest.raises(FileNotFoundError):
        os.mkdir(tmp_path / "missing-parent" / "child")

    item = folder / "item.bin"
    item.write_bytes(b"data")
    with pytest.raises(OSError):
        os.rmdir(folder)

    os.unlink(item)
    assert os.rmdir(folder) is None
    assert not folder.exists()


def test_remove_and_unlink_are_file_aliases_but_do_not_remove_directories(tmp_path):
    """两个名称共享删除文件语义；删除目录必须明确使用 rmdir。"""

    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    folder = tmp_path / "folder"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    folder.mkdir()

    assert os.remove(first) is None
    assert os.unlink(second) is None
    assert not first.exists()
    assert not second.exists()
    with pytest.raises(OSError):
        os.remove(folder)


def test_rename_moves_a_name_and_replace_atomically_overwrites_file(tmp_path):
    """replace 的同一 filesystem 成功操作是 atomic；跨 filesystem 仍可能失败。"""

    source = tmp_path / "source.bin"
    moved = tmp_path / "moved.bin"
    source.write_bytes(b"source")
    assert os.rename(source, moved) is None
    assert not source.exists()
    assert moved.read_bytes() == b"source"

    replacement = tmp_path / "replacement.bin"
    replacement.write_bytes(b"new")
    assert os.replace(replacement, moved) is None
    assert not replacement.exists()
    assert moved.read_bytes() == b"new"


def test_renames_creates_new_parents_and_prunes_empty_old_parents(tmp_path):
    """这是 rename 加 makedirs/removedirs 的便利函数，不提供 rollback。"""

    old = tmp_path / "old" / "nested" / "item.bin"
    new = tmp_path / "new" / "deep" / "item.bin"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"payload")

    assert os.renames(old, new) is None
    assert new.read_bytes() == b"payload"
    assert not (tmp_path / "old").exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="平台不提供 named FIFO")
def test_mkfifo_creates_rendezvous_node_without_opening_it(tmp_path):
    """创建 FIFO 本身不阻塞；真正 open/read/write 才需要另一端参与。"""

    fifo = tmp_path / "events.fifo"
    os.mkfifo(fifo, 0o600)

    assert stat.S_ISFIFO(os.stat(fifo).st_mode)
    assert fifo.exists()
    os.unlink(fifo)
    assert not fifo.exists()
