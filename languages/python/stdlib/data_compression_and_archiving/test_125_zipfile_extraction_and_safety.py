"""125｜ZIP 解压、目标路径清理与不可信归档的预检策略。

``extract``/``extractall`` 会创建父目录并清理绝对路径、``.``、``..`` 等组件，但官方
仍要求在解压不可信归档前检查成员。路径穿越只是风险之一：超大展开体积、极端压缩比、
重复覆盖和类 Unix symlink 元数据都需要应用按自身信任边界制定策略。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.zipfile.extract python.zipfile.extract-return-path
# polyglot-covers: python.zipfile.extractall python.zipfile.extract-subset
# polyglot-covers: python.zipfile.extract-create-directories
# polyglot-covers: python.zipfile.extract-path-normalization
# polyglot-covers: python.zipfile.extract-overwrite python.zipfile.untrusted-archive
# polyglot-covers: python.zipfile.preflight python.zipfile.uncompressed-size-budget
# polyglot-covers: python.zipfile.compression-ratio-budget python.zipfile.path-traversal
# polyglot-covers: python.zipfile.symlink-metadata python.zipfile.resource-limits

import io
from pathlib import PurePosixPath
import stat
import zipfile

import pytest


def _inspect_members(
    archive,
    *,
    max_total_size=1_000_000,
    max_member_size=500_000,
    max_ratio=100,
):
    """返回通过示例安全策略的 ZipInfo；真实限额应由业务场景决定。"""

    accepted = []
    total_size = 0
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe member path: {info.filename}")
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"symbolic link is not accepted: {info.filename}")

        total_size += info.file_size
        ratio = info.file_size / max(info.compress_size, 1)
        if info.file_size > max_member_size:
            raise ValueError(f"member is too large: {info.filename}")
        if total_size > max_total_size:
            raise ValueError("archive expands beyond the total size budget")
        if ratio > max_ratio:
            raise ValueError(f"compression ratio is too high: {info.filename}")
        accepted.append(info)
    return accepted


def test_extract_returns_created_path_and_makes_parent_directories(tmp_path):
    """返回值是规范化后的 filesystem path 字符串，可直接交给后续处理。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("nested/report.txt", b"report")

    destination = tmp_path / "output"
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        extracted = archive.extract("nested/report.txt", destination)

    assert extracted == str(destination / "nested" / "report.txt")
    assert (destination / "nested" / "report.txt").read_bytes() == b"report"


def test_extractall_can_select_a_member_subset(tmp_path):
    """members 参数限制本次展开范围；它不是安全过滤器，名称仍应在此前检查。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("keep.txt", b"keep")
        archive.writestr("skip.txt", b"skip")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        archive.extractall(tmp_path, members=["keep.txt"])

    assert (tmp_path / "keep.txt").read_bytes() == b"keep"
    assert not (tmp_path / "skip.txt").exists()


def test_extract_removes_absolute_and_parent_path_components(tmp_path):
    """内建提取器清除危险组件；不要把这项兼容性清理当成完整信任策略。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../../outside.txt", b"parent")
        archive.writestr("/absolute.txt", b"absolute")
        archive.writestr("safe/../flattened.txt", b"flattened")

    destination = tmp_path / "destination"
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        archive.extractall(destination)

    assert (destination / "outside.txt").read_bytes() == b"parent"
    assert (destination / "absolute.txt").read_bytes() == b"absolute"
    assert (destination / "safe" / "flattened.txt").read_bytes() == b"flattened"
    assert not (tmp_path / "outside.txt").exists()


def test_extract_overwrites_an_existing_regular_file(tmp_path):
    """同路径普通文件会被替换内容；若不能接受覆盖，应在 extract 前自行判定冲突。"""

    target = tmp_path / "same.txt"
    target.write_bytes(b"local content")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("same.txt", b"archive content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        archive.extract("same.txt", tmp_path)

    assert target.read_bytes() == b"archive content"


def test_preflight_accepts_members_within_path_and_size_budgets():
    """先检查 infolist，再把返回的 ZipInfo 列表交给 extractall，避免 TOCTOU 式重查名称。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("docs/readme.txt", b"ordinary content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        accepted = _inspect_members(archive)

    assert [info.filename for info in accepted] == ["docs/readme.txt"]


@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "a/../../escape.txt"])
def test_preflight_rejects_absolute_or_parent_paths(name):
    """PurePosixPath 按 ZIP 固定的 slash 语法检查；不能用宿主 OS 路径规则代替。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, b"content")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="unsafe member path"):
            _inspect_members(archive)


def test_preflight_rejects_total_expansion_beyond_budget():
    """累计 file_size 比只看单个成员更重要，大量小成员同样能耗尽磁盘。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("first.bin", b"a" * 60)
        archive.writestr("second.bin", b"b" * 60)

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="total size budget"):
            _inspect_members(
                archive,
                max_total_size=100,
                max_member_size=100,
            )


def test_preflight_can_reject_an_extreme_compression_ratio():
    """小 archive 可能展开为大 payload；ratio 限额只是资源策略，不代表内容可信。"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("repeated.bin", b"0" * 100_000)

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="compression ratio"):
            _inspect_members(
                archive,
                max_total_size=200_000,
                max_member_size=200_000,
                max_ratio=10,
            )


def test_preflight_recognizes_unix_symlink_metadata():
    """ZIP 没有统一的 symlink 类型；Unix creator 通常把 mode 编入 external_attr。"""

    link = zipfile.ZipInfo("link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(link, b"target.txt")

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        with pytest.raises(ValueError, match="symbolic link"):
            _inspect_members(archive)
