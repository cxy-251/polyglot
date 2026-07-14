"""130｜``TarFile.add``、``gettarinfo``/``addfile``、归档过滤与链接语义。

``add`` 从文件系统递归采集并在 3.7+ 按名称排序；``filter`` 可在写入前修改 metadata
或排除成员/整棵目录。``gettarinfo`` 与 ``addfile`` 把 metadata 和 payload 分离，适合
内存或生成式数据。``dereference`` 决定记录链接本身还是目标内容。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tarfile.TarFile.add python.tarfile.add-arcname
# polyglot-covers: python.tarfile.add-recursive python.tarfile.add-sorted
# polyglot-covers: python.tarfile.add-recursive-false python.tarfile.add-filter
# polyglot-covers: python.tarfile.filter-modify python.tarfile.filter-exclude
# polyglot-covers: python.tarfile.filter-directory-subtree
# polyglot-covers: python.tarfile.gettarinfo python.tarfile.addfile
# polyglot-covers: python.tarfile.addfile-size python.tarfile.addfile-short-input
# polyglot-covers: python.tarfile.dereference python.tarfile.symbolic-link
# polyglot-covers: python.tarfile.hard-link python.tarfile.linkname
# polyglot-covers: python.tarfile.path-like-member python.tarfile.member-metadata

import io
import os
import tarfile

import pytest


def test_add_uses_arcname_and_recurses_in_sorted_order(tmp_path):
    """arcname 隔离本机绝对路径；递归顺序稳定，便于生成可重现的 archive。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "zeta.txt").write_bytes(b"z")
    (source / "alpha.txt").write_bytes(b"a")
    nested = source / "nested"
    nested.mkdir()
    (nested / "child.txt").write_bytes(b"child")
    buffer = io.BytesIO()

    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == [
            "bundle",
            "bundle/alpha.txt",
            "bundle/nested",
            "bundle/nested/child.txt",
            "bundle/zeta.txt",
        ]
        member = archive.extractfile("bundle/nested/child.txt")
        assert member is not None
        assert member.read() == b"child"


def test_recursive_false_adds_only_the_directory_entry(tmp_path):
    """recursive=False 仍保存目录自身的 metadata，但不遍历 children。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "child.txt").write_bytes(b"child")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle", recursive=False)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == ["bundle"]
        assert archive.getmember("bundle").isdir() is True


def test_add_filter_can_normalize_metadata_and_exclude_members(tmp_path):
    """filter 在 header 写入前运行；返回 None 排除成员，返回 TarInfo 保存修改。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_bytes(b"keep")
    (source / "discard.tmp").write_bytes(b"discard")

    def reproducible(info):
        if info.name.endswith(".tmp"):
            return None
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mtime = 0
        return info

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle", filter=reproducible)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == ["bundle", "bundle/keep.txt"]
        for info in archive.getmembers():
            assert (info.uid, info.gid) == (0, 0)
            assert (info.uname, info.gname) == ("root", "root")
            assert info.mtime == 0


def test_rejecting_a_directory_in_filter_skips_its_entire_subtree(tmp_path):
    """目录返回 None 后不会访问 descendants；可避免先递归再逐文件过滤的成本。"""

    source = tmp_path / "source"
    source.mkdir()
    (source / "keep.txt").write_bytes(b"keep")
    cache = source / "cache"
    cache.mkdir()
    (cache / "hidden.bin").write_bytes(b"hidden")
    seen = []

    def exclude_cache(info):
        seen.append(info.name)
        if info.name == "bundle/cache":
            return None
        return info

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.add(source, arcname="bundle", filter=exclude_cache)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        assert archive.getnames() == ["bundle", "bundle/keep.txt"]
    assert "bundle/cache" in seen
    assert "bundle/cache/hidden.bin" not in seen


def test_gettarinfo_then_addfile_allows_metadata_customization(tmp_path):
    """gettarinfo 只读取 stat；caller 修改 header 后，再提供位于开头的 binary fileobj。"""

    source = tmp_path / "source.txt"
    source.write_bytes(b"content")
    buffer = io.BytesIO()
    with source.open("rb") as payload:
        with tarfile.open(fileobj=buffer, mode="w:") as archive:
            info = archive.gettarinfo(source, arcname="renamed.txt")
            info.mode = 0o640
            info.uid = 123
            archive.addfile(info, payload)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        info = archive.getmember("renamed.txt")
        member = archive.extractfile(info)
        assert info.mode == 0o640
        assert info.uid == 123
        assert member is not None
        assert member.read() == b"content"


def test_addfile_reads_exactly_tarinfo_size_bytes():
    """TarInfo.size 是协议边界；fileobj 的额外 bytes 不属于该成员。"""

    info = tarfile.TarInfo("prefix.bin")
    info.size = 4
    source = io.BytesIO(b"data trailing bytes")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(info, source)

    assert source.tell() == 4
    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        member = archive.extractfile("prefix.bin")
        assert member is not None
        assert member.read() == b"data"


def test_addfile_rejects_payload_shorter_than_declared_size():
    """header 宣称的 size 必须有对应 bytes；短输入是 OSError，而不是自动缩小 metadata。"""

    info = tarfile.TarInfo("truncated.bin")
    info.size = 10

    with tarfile.open(fileobj=io.BytesIO(), mode="w:") as archive:
        with pytest.raises(OSError, match="unexpected end of data"):
            archive.addfile(info, io.BytesIO(b"short"))


def test_dereference_false_archives_a_symbolic_link_itself(tmp_path):
    """默认保留 symlink 类型和相对 linkname，不复制目标 payload。"""

    target = tmp_path / "target.txt"
    target.write_bytes(b"target content")
    link = tmp_path / "link.txt"
    link.symlink_to(target.name)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", dereference=False) as archive:
        archive.add(link, arcname="link.txt")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        info = archive.getmember("link.txt")
        assert info.issym() is True
        assert info.linkname == "target.txt"
        assert info.size == 0


def test_dereference_true_archives_symbolic_link_target_content(tmp_path):
    """dereference=True 把 symlink 当作目标文件采集，读取方不再需要链接目标。"""

    target = tmp_path / "target.txt"
    target.write_bytes(b"target content")
    link = tmp_path / "link.txt"
    link.symlink_to(target.name)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", dereference=True) as archive:
        archive.add(link, arcname="copied.txt")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        info = archive.getmember("copied.txt")
        member = archive.extractfile(info)
        assert info.isfile() is True
        assert member is not None
        assert member.read() == b"target content"


def test_repeated_inode_can_be_stored_as_a_tar_hard_link(tmp_path):
    """dereference=False 的 inode cache 将后续 hard link 写为 LNKTYPE，避免重复 payload。"""

    first = tmp_path / "first.txt"
    first.write_bytes(b"shared content")
    second = tmp_path / "second.txt"
    os.link(first, second)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", dereference=False) as archive:
        archive.add(first, arcname="first.txt")
        archive.add(second, arcname="second.txt")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        first_info, second_info = archive.getmembers()
        assert first_info.isfile() is True
        assert second_info.islnk() is True
        assert second_info.linkname == "first.txt"
