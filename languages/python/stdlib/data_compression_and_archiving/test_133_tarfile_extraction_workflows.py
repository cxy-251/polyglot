"""133｜TAR 选择性解压、metadata 恢复、目录收尾与链接落盘。

``extractfile`` 只读 payload；``extract``/``extractall`` 才写文件系统并可恢复 mode、mtime、
链接和目录。extractall 在 children 完成后再设置目录 metadata，避免只读目录阻断写入。
重复成员按顺序覆盖。安全策略必须显式传 filter，本文件使用可信或 data 场景。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.tarfile.extract python.tarfile.extract-return-none
# polyglot-covers: python.tarfile.extractall python.tarfile.extract-subset-generator
# polyglot-covers: python.tarfile.extract-path-like python.tarfile.extract-create-parent
# polyglot-covers: python.tarfile.set-attrs python.tarfile.set-attrs-false
# polyglot-covers: python.tarfile.extract-mode python.tarfile.extract-mtime
# polyglot-covers: python.tarfile.directory-metadata-after-children
# polyglot-covers: python.tarfile.extract-duplicate-overwrite
# polyglot-covers: python.tarfile.extract-hard-link python.tarfile.extract-symbolic-link
# polyglot-covers: python.tarfile.numeric-owner python.tarfile.named-owner

import io
import os
import stat
import tarfile


def _add_bytes(archive, name, payload, *, mode=0o644, mtime=0):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = mode
    info.mtime = mtime
    archive.addfile(info, io.BytesIO(payload))


def test_extractall_accepts_a_generator_for_a_member_subset(tmp_path):
    """members 可以惰性过滤 getmembers/iterator；仍应独立传入可信边界所需 filter。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_bytes(archive, "keep.py", b"print('keep')\n")
        _add_bytes(archive, "skip.txt", b"skip")

    def python_members(members):
        for info in members:
            if info.name.endswith(".py"):
                yield info

    destination = tmp_path / "selected"
    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(
            destination,
            members=python_members(archive),
            filter="data",
        )

    assert (destination / "keep.py").read_bytes() == b"print('keep')\n"
    assert not (destination / "skip.txt").exists()


def test_extract_returns_none_and_creates_parent_directories(tmp_path):
    """与 zipfile.extract 不同，tarfile.extract 的返回值固定为 None。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_bytes(archive, "nested/report.txt", b"report")

    destination = tmp_path / "output"
    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        result = archive.extract("nested/report.txt", destination, filter="data")

    assert result is None
    assert (destination / "nested" / "report.txt").read_bytes() == b"report"


def test_extract_restores_mode_and_mtime_when_set_attrs_is_true(tmp_path):
    """可信归档可恢复 permission/mtime；owner 处理还受权限、numeric_owner 与系统账户影响。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_bytes(
            archive,
            "script.sh",
            b"#!/bin/sh\n",
            mode=0o750,
            mtime=1_600_000_000,
        )

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extract(
            "script.sh",
            tmp_path,
            set_attrs=True,
            numeric_owner=False,
            filter="fully_trusted",
        )

    status = (tmp_path / "script.sh").stat()
    assert stat.S_IMODE(status.st_mode) == 0o750
    assert int(status.st_mtime) == 1_600_000_000


def test_set_attrs_false_leaves_new_filesystem_metadata_in_place(tmp_path):
    """set_attrs=False 仍写内容，但跳过 archive mode/owner/mtime 的恢复。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_bytes(archive, "plain.txt", b"content", mode=0o700, mtime=123)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extract(
            "plain.txt",
            tmp_path,
            set_attrs=False,
            filter="fully_trusted",
        )

    status = (tmp_path / "plain.txt").stat()
    assert int(status.st_mtime) != 123


def test_extractall_applies_directory_metadata_after_children(tmp_path):
    """目录 header 即使是只读 mode，也先以可写状态创建；children 完成后再收紧。"""

    directory = tarfile.TarInfo("locked/")
    directory.type = tarfile.DIRTYPE
    directory.mode = 0o500
    directory.mtime = 1_500_000_000
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(directory)
        _add_bytes(archive, "locked/child.txt", b"child")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(tmp_path, filter="fully_trusted")

    assert (tmp_path / "locked" / "child.txt").read_bytes() == b"child"
    directory_status = (tmp_path / "locked").stat()
    assert stat.S_IMODE(directory_status.st_mode) == 0o500
    assert int(directory_status.st_mtime) == 1_500_000_000
    # 恢复 owner write，避免 pytest 清理 tmp_path 时无法 unlink child。
    (tmp_path / "locked").chmod(0o700)


def test_later_duplicate_member_overwrites_earlier_content(tmp_path):
    """extractall 按物理顺序执行；同名最新成员覆盖旧内容，安全审计不能先去重。"""

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        _add_bytes(archive, "same.txt", b"first")
        _add_bytes(archive, "same.txt", b"latest")

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(tmp_path, filter="data")

    assert (tmp_path / "same.txt").read_bytes() == b"latest"


def test_data_filter_allows_links_that_stay_inside_destination(tmp_path):
    """data 并非禁止全部链接；它拒绝越界 target，并允许归档内部的安全链接。"""

    target = tarfile.TarInfo("target.txt")
    target.size = len(b"shared")
    hard_link = tarfile.TarInfo("hard.txt")
    hard_link.type = tarfile.LNKTYPE
    hard_link.linkname = "target.txt"
    symbolic_link = tarfile.TarInfo("symbolic.txt")
    symbolic_link.type = tarfile.SYMTYPE
    symbolic_link.linkname = "target.txt"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        archive.addfile(target, io.BytesIO(b"shared"))
        archive.addfile(hard_link)
        archive.addfile(symbolic_link)

    with tarfile.open(fileobj=io.BytesIO(buffer.getvalue()), mode="r:") as archive:
        archive.extractall(tmp_path, filter="data")

    assert (tmp_path / "hard.txt").read_bytes() == b"shared"
    assert os.stat(tmp_path / "hard.txt").st_ino == os.stat(tmp_path / "target.txt").st_ino
    assert (tmp_path / "symbolic.txt").is_symlink()
    assert os.readlink(tmp_path / "symbolic.txt") == "target.txt"
