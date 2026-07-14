"""156｜``stat`` metadata、hard/symbolic links、``utime`` 与 ``truncate``。

``stat`` 默认跟随 symlink，``lstat`` 和 ``follow_symlinks=False`` 查询目录项本身。
hard link 是同一 inode 的另一个名称，symlink 保存目标路径文本。时间戳应优先
使用 ``*_ns`` 整数成员，避免 float 丢失 filesystem 提供的精度。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.stat python.os.stat-result
# polyglot-covers: python.os.stat-tuple python.os.stat-nanosecond-fields
# polyglot-covers: python.os.lstat python.os.stat-follow-symlinks
# polyglot-covers: python.os.symlink python.os.readlink
# polyglot-covers: python.os.link python.os.hard-link-inode
# polyglot-covers: python.os.utime python.os.utime-ns
# polyglot-covers: python.os.utime-times-ns-exclusive python.os.truncate
# polyglot-covers: python.os.chmod python.os.permission-bits

import os
import stat

import pytest


def test_stat_result_exposes_named_metadata_and_legacy_tuple_view(tmp_path):
    """named fields 最清晰；legacy tuple 会把时间字段表示成整数。"""

    path = tmp_path / "item.bin"
    path.write_bytes(b"abc")
    metadata = os.stat(path)

    assert metadata.st_size == 3
    assert stat.S_ISREG(metadata.st_mode)
    assert metadata.st_nlink >= 1
    assert all(type(value) is int for value in tuple(metadata)[:10])
    assert metadata.st_mtime_ns // 1_000_000_000 == int(metadata.st_mtime)


def test_stat_follows_symlink_while_lstat_describes_link_itself(tmp_path):
    """link 的 st_size 是所存目标文本长度；target 的 st_size 是文件内容长度。"""

    target = tmp_path / "target.bin"
    target.write_bytes(b"payload")
    link = tmp_path / "alias.bin"
    os.symlink(target.name, link)

    followed = os.stat(link)
    link_metadata = os.lstat(link)

    assert stat.S_ISREG(followed.st_mode)
    assert followed.st_size == 7
    assert stat.S_ISLNK(link_metadata.st_mode)
    assert link_metadata.st_size == len(os.fsencode(target.name))
    assert os.stat(link, follow_symlinks=False) == link_metadata
    assert os.readlink(link) == target.name
    assert os.readlink(os.fsencode(link)) == os.fsencode(target.name)


def test_hard_links_share_inode_and_content_survives_unlink_of_one_name(tmp_path):
    """unlink 删除名称而非立刻删除对象；仍有 hard link 时数据继续存在。"""

    original = tmp_path / "original.bin"
    alias = tmp_path / "alias.bin"
    original.write_bytes(b"shared")
    os.link(original, alias)

    original_stat = os.stat(original)
    alias_stat = os.stat(alias)
    assert (original_stat.st_dev, original_stat.st_ino) == (
        alias_stat.st_dev,
        alias_stat.st_ino,
    )
    assert original_stat.st_nlink >= 2

    os.unlink(original)
    assert not original.exists()
    assert alias.read_bytes() == b"shared"


def test_utime_accepts_integer_nanoseconds_but_filesystem_controls_precision(tmp_path):
    """请求值可能被 filesystem 舍入；ns fields 仍比 float seconds 更可控。"""

    path = tmp_path / "timestamp.bin"
    path.write_bytes(b"data")
    requested_atime = 1_600_000_000_123_456_789
    requested_mtime = 1_600_000_100_987_654_321

    os.utime(path, ns=(requested_atime, requested_mtime))
    metadata = os.stat(path)

    # 允许低精度 filesystem 舍入；现代 Linux filesystems 通常会精确保留请求值。
    assert abs(metadata.st_atime_ns - requested_atime) <= 2_000_000_000
    assert abs(metadata.st_mtime_ns - requested_mtime) <= 2_000_000_000

    with pytest.raises(ValueError):
        os.utime(path, times=(1, 2), ns=(3, 4))


def test_chmod_changes_permissions_and_truncate_changes_length(tmp_path):
    """chmod 只设置 mode bits；truncate 可缩短文件，也可用零字节扩展文件。"""

    path = tmp_path / "mutable.bin"
    path.write_bytes(b"abcdefgh")

    os.chmod(path, 0o640)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o640

    os.truncate(path, 3)
    assert path.read_bytes() == b"abc"
    os.truncate(path, 6)
    assert path.read_bytes() == b"abc\x00\x00\x00"
