"""155｜``dir_fd``、fd-as-path、capability sets 与 ``fwalk``。

基于 directory descriptor 的相对操作避免依赖 process cwd，也减少拼接绝对路径。
这些能力并非所有平台都有，必须先查询 ``supports_dir_fd``、``supports_fd`` 与
``supports_follow_symlinks``；仅检查函数是否存在并不足够。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.supports-dir-fd python.os.supports-fd
# polyglot-covers: python.os.supports-follow-symlinks python.os.supports-effective-ids
# polyglot-covers: python.os.dir-fd python.os.open-dir-fd
# polyglot-covers: python.os.mkdir-dir-fd python.os.stat-dir-fd
# polyglot-covers: python.os.rename-dir-fd python.os.unlink-dir-fd
# polyglot-covers: python.os.fd-as-path python.os.absolute-path-ignores-dir-fd
# polyglot-covers: python.os.fwalk python.os.fwalk-directory-descriptor
# polyglot-covers: python.os.access python.os.F_OK python.os.access-eafp-trap

import os

import pytest


def test_capability_sets_contain_callables_not_function_names():
    """集合元素是 function objects；不能硬编码不同 OS 的完整成员列表。"""

    capability_sets = (
        os.supports_dir_fd,
        os.supports_effective_ids,
        os.supports_fd,
        os.supports_follow_symlinks,
    )

    assert all(isinstance(group, set) for group in capability_sets)
    assert all(callable(item) for group in capability_sets for item in group)
    assert (os.stat in os.supports_fd) is bool(os.stat in os.supports_fd)


@pytest.mark.skipif(
    not {os.mkdir, os.open, os.rename, os.stat, os.unlink} <= os.supports_dir_fd,
    reason="平台缺少本案例需要的 dir_fd 操作",
)
def test_dir_fd_workflow_resolves_relative_names_without_changing_cwd(tmp_path):
    """同一目录 fd 可供创建、打开、查询、重命名和删除 API 使用。"""

    root = tmp_path / "sandbox"
    root.mkdir()
    root_fd = os.open(root, os.O_RDONLY)
    try:
        os.mkdir("data", dir_fd=root_fd)
        data_fd = os.open("data", os.O_RDONLY, dir_fd=root_fd)
        try:
            file_fd = os.open(
                "item.bin",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=data_fd,
            )
            try:
                os.write(file_fd, b"payload")
            finally:
                os.close(file_fd)

            assert os.stat("item.bin", dir_fd=data_fd).st_size == 7
            os.rename(
                "item.bin",
                "renamed.bin",
                src_dir_fd=data_fd,
                dst_dir_fd=data_fd,
            )
            os.unlink("renamed.bin", dir_fd=data_fd)
        finally:
            os.close(data_fd)
    finally:
        os.close(root_fd)

    assert list((root / "data").iterdir()) == []


@pytest.mark.skipif(os.stat not in os.supports_fd, reason="stat 不接受 fd-as-path")
def test_path_parameter_can_be_an_fd_but_cannot_also_use_dir_fd(tmp_path):
    """fd-as-path 直接引用已打开对象；与 dir_fd/follow_symlinks 组合属于歧义。"""

    path = tmp_path / "item.bin"
    path.write_bytes(b"abc")
    fd = os.open(path, os.O_RDONLY)
    directory_fd = os.open(tmp_path, os.O_RDONLY)
    try:
        assert os.stat(fd).st_size == 3
        with pytest.raises(ValueError):
            os.stat(fd, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
        os.close(fd)


@pytest.mark.skipif(os.stat not in os.supports_dir_fd, reason="stat 不支持 dir_fd")
def test_absolute_path_ignores_dir_fd(tmp_path):
    """dir_fd 只为相对路径提供起点；绝对路径仍从 filesystem root 解析。"""

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    target = second / "item.bin"
    target.write_bytes(b"absolute")
    first_fd = os.open(first, os.O_RDONLY)
    try:
        assert os.stat(target, dir_fd=first_fd).st_size == len(b"absolute")
    finally:
        os.close(first_fd)


@pytest.mark.skipif(not hasattr(os, "fwalk"), reason="平台不提供 fwalk")
def test_fwalk_uses_each_yielded_dir_fd_before_advancing_iterator(tmp_path):
    """yielded dirfd 仅保证当前迭代有效；需要长期保存时应立即 dup。"""

    (tmp_path / "nested").mkdir()
    (tmp_path / "root.bin").write_bytes(b"12")
    (tmp_path / "nested" / "child.bin").write_bytes(b"345")
    observed = {}

    for directory, dirnames, filenames, directory_fd in os.fwalk(tmp_path):
        dirnames.sort()
        filenames.sort()
        observed[os.path.relpath(directory, tmp_path)] = sum(
            os.stat(name, dir_fd=directory_fd).st_size for name in filenames
        )

    assert observed == {".": 2, "nested": 3}


def test_access_is_a_snapshot_not_authorization_for_a_later_open(tmp_path):
    """access 只返回检查时的 bool；真实操作仍应采用 EAFP 并处理 OSError。"""

    present = tmp_path / "present.bin"
    missing = tmp_path / "missing.bin"
    present.write_bytes(b"data")

    assert os.access(present, os.F_OK) is True
    assert os.access(missing, os.F_OK) is False
    with pytest.raises(FileNotFoundError):
        os.open(missing, os.O_RDONLY)
