"""078｜``dir_fd``、fd-as-path、capability sets 与 ``fwalk``。

基于 directory descriptor 的相对操作避免依赖 process cwd，也减少拼接绝对路径。
这些能力并非所有平台都有，必须先查询 ``supports_dir_fd``、``supports_fd`` 与
``supports_follow_symlinks``；仅检查函数是否存在并不足够。

这些案例面向 Python 3.10 当前补丁系列。
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
import stat
import errno

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


# ``stat`` metadata、hard/symbolic links、``utime`` 与 ``truncate``。
#
# ``stat`` 默认跟随 symlink，``lstat`` 和 ``follow_symlinks=False`` 查询目录项本身。
# hard link 是同一 inode 的另一个名称，symlink 保存目标路径文本。时间戳应优先
# 使用 ``*_ns`` 整数成员，避免 float 丢失 filesystem 提供的精度。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.stat python.os.stat-result
# polyglot-covers: python.os.stat-tuple python.os.stat-nanosecond-fields
# polyglot-covers: python.os.lstat python.os.stat-follow-symlinks
# polyglot-covers: python.os.symlink python.os.readlink
# polyglot-covers: python.os.link python.os.hard-link-inode
# polyglot-covers: python.os.utime python.os.utime-ns
# polyglot-covers: python.os.utime-times-ns-exclusive python.os.truncate
# polyglot-covers: python.os.chmod python.os.permission-bits




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


# ``mkdir/rmdir``、remove/unlink、rename/replace 与 recursive renames。
#
# 目录和名称变更通常返回 ``None``，失败通过精确的 ``OSError`` subclass 表达。
# ``replace`` 明确允许覆盖现有文件；``renames`` 还会创建新父目录并尝试清理
# 旧父目录，因此失败时可能留下部分结构，不适合作为事务接口。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.mkdir python.os.mkdir-existing-error
# polyglot-covers: python.os.rmdir python.os.rmdir-nonempty-error
# polyglot-covers: python.os.remove python.os.unlink python.os.remove-directory-error
# polyglot-covers: python.os.rename python.os.replace
# polyglot-covers: python.os.replace-overwrite python.os.renames
# polyglot-covers: python.os.renames-parent-creation python.os.renames-parent-pruning
# polyglot-covers: python.os.mkfifo python.os.named-pipe-filesystem-node




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


# ``statvfs``、path configuration、device numbers 与 descriptor traversal。
#
# 这些查询描述当前 host/filesystem 能力，不应把某台机器的具体数值写死。
# ``pathconf_names``/``sysconf_names`` mapping 用于发现已知名称，而不是保证 kernel
# 支持每一个值；未知名称与已知但不可用的名称会以不同异常表达。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.statvfs python.os.statvfs-result
# polyglot-covers: python.os.ST_RDONLY python.os.ST_NOSUID
# polyglot-covers: python.os.pathconf python.os.pathconf-names
# polyglot-covers: python.os.fpathconf python.os.pathconf-unknown-name
# polyglot-covers: python.os.major python.os.minor python.os.makedev
# polyglot-covers: python.os.device-number-roundtrip python.os.filesystem-capability-query




@pytest.mark.skipif(not hasattr(os, "statvfs"), reason="平台不提供 statvfs")
def test_statvfs_reports_capacity_units_and_mount_flags(tmp_path):
    """block counts 必须乘 fragment size 才是 bytes；free 与 available 含义不同。"""

    info = os.statvfs(tmp_path)

    assert info.f_bsize > 0
    assert info.f_frsize > 0
    assert info.f_blocks >= info.f_bfree >= 0
    assert info.f_blocks >= info.f_bavail >= 0
    assert info.f_namemax > 0
    assert isinstance(info.f_flag & os.ST_RDONLY, int)
    assert isinstance(info.f_flag & os.ST_NOSUID, int)


@pytest.mark.skipif(not hasattr(os, "pathconf"), reason="平台不提供 pathconf")
def test_pathconf_accepts_symbolic_name_and_fd_and_rejects_unknown_name(tmp_path):
    """symbolic key 来自 pathconf_names；fd variant 避免再次解析路径。"""

    name = "PC_NAME_MAX"
    if name not in os.pathconf_names:
        pytest.skip(f"host 不认识 {name}")

    path_value = os.pathconf(tmp_path, name)
    fd = os.open(tmp_path, os.O_RDONLY)
    try:
        fd_value = os.fpathconf(fd, name)
    finally:
        os.close(fd)

    assert path_value == fd_value
    assert path_value > 0
    assert os.pathconf_names[name] == os.pathconf_names.get(name)
    with pytest.raises(ValueError):
        os.pathconf(tmp_path, "POLYGLOT_UNKNOWN_PATHCONF")


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("major", "minor", "makedev")),
    reason="平台不暴露 Unix device number helpers",
)
def test_major_minor_and_makedev_round_trip_stat_device_number(tmp_path):
    """raw st_dev 不应自行按位拆分；布局由平台和三个 helper 定义。"""

    device = os.stat(tmp_path).st_dev
    major = os.major(device)
    minor = os.minor(device)

    assert major >= 0
    assert minor >= 0
    assert os.makedev(major, minor) == device


# Linux ``memfd_create`` 与 ``eventfd`` descriptor 工作流。
#
# ``memfd`` 是没有普通 pathname 的匿名内存文件；``eventfd`` 是 kernel 维护的
# 64-bit counter，常用于线程/进程或 event loop 通知。二者都返回普通 fd，必须
# 关闭，且 Python 创建的 descriptor 默认不可跨 exec 继承。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.memfd-create python.os.MFD_CLOEXEC
# polyglot-covers: python.os.memory-file-descriptor python.os.memfd-no-pathname
# polyglot-covers: python.os.eventfd python.os.eventfd-read python.os.eventfd-write
# polyglot-covers: python.os.EFD_CLOEXEC python.os.EFD_NONBLOCK
# polyglot-covers: python.os.EFD_SEMAPHORE python.os.eventfd-counter-reset
# polyglot-covers: python.os.eventfd-semaphore-decrement python.os.eventfd-would-block




@pytest.mark.skipif(not hasattr(os, "memfd_create"), reason="host 不提供 Linux memfd")
def test_memfd_behaves_like_an_anonymous_seekable_file():
    """name 只用于诊断，不创建目录项；fd 仍支持常规 read/write/seek。"""

    fd = os.memfd_create("polyglot-example", os.MFD_CLOEXEC)
    try:
        assert os.get_inheritable(fd) is False
        assert os.write(fd, b"in-memory") == 9
        assert os.lseek(fd, 0, os.SEEK_SET) == 0
        assert os.read(fd, 20) == b"in-memory"
        assert os.fstat(fd).st_size == 9
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "eventfd"), reason="host 不提供 Linux eventfd")
def test_eventfd_read_returns_counter_and_resets_it_to_zero():
    """非 semaphore 模式一次读出累计值；zero counter 的 nonblocking read 会失败。"""

    fd = os.eventfd(2, os.EFD_CLOEXEC | os.EFD_NONBLOCK)
    try:
        assert os.get_inheritable(fd) is False
        os.eventfd_write(fd, 3)
        assert os.eventfd_read(fd) == 5
        with pytest.raises(BlockingIOError):
            os.eventfd_read(fd)
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "eventfd"), reason="host 不提供 Linux eventfd")
def test_eventfd_semaphore_mode_returns_one_and_decrements_counter():
    """EFD_SEMAPHORE 把 counter 当 permit count，而不是一次清零的累计通知。"""

    flags = os.EFD_CLOEXEC | os.EFD_NONBLOCK | os.EFD_SEMAPHORE
    fd = os.eventfd(2, flags)
    try:
        assert os.eventfd_read(fd) == 1
        assert os.eventfd_read(fd) == 1
        with pytest.raises(BlockingIOError):
            os.eventfd_read(fd)
    finally:
        os.close(fd)


# Linux extended attributes 的 create/get/list/replace/remove lifecycle。
#
# extended attribute 是附在 inode 上的 named bytes value。``user.*`` namespace
# 通常可由普通用户使用，但仍取决于 filesystem policy；本文件只对明确的能力型
# 错误 skip，并严格检查 create-only 与 replace-only flags 的原子语义。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.setxattr python.os.getxattr
# polyglot-covers: python.os.listxattr python.os.removexattr
# polyglot-covers: python.os.XATTR_CREATE python.os.XATTR_REPLACE
# polyglot-covers: python.os.XATTR_SIZE_MAX python.os.extended-attribute-bytes
# polyglot-covers: python.os.xattr-create-existing-error
# polyglot-covers: python.os.xattr-replace-missing-error python.os.xattr-capability-guard




_UNSUPPORTED_ERRNOS = {
    errno.EACCES,
    errno.EPERM,
    errno.EOPNOTSUPP,
}


@pytest.mark.skipif(not hasattr(os, "setxattr"), reason="平台不提供 extended attributes")
def test_xattr_create_replace_list_and_remove_lifecycle(tmp_path):
    """flags 让 kernel 原子检查“必须不存在/已存在”，避免先查后改竞态。"""

    path = tmp_path / "item.bin"
    path.write_bytes(b"content")
    attribute = "user.polyglot-example"
    created = False
    try:
        try:
            os.setxattr(path, attribute, b"v1", os.XATTR_CREATE)
            created = True
        except OSError as error:
            if error.errno in _UNSUPPORTED_ERRNOS:
                pytest.skip(f"filesystem policy 不支持 user xattr: {error}")
            raise

        assert os.getxattr(path, attribute) == b"v1"
        assert attribute in os.listxattr(path)
        assert os.XATTR_SIZE_MAX >= len(b"v1")

        with pytest.raises(OSError) as duplicate:
            os.setxattr(path, attribute, b"again", os.XATTR_CREATE)
        assert duplicate.value.errno == errno.EEXIST

        os.setxattr(path, attribute, b"v2", os.XATTR_REPLACE)
        assert os.getxattr(path, attribute) == b"v2"

        os.removexattr(path, attribute)
        created = False
        with pytest.raises(OSError) as missing:
            os.setxattr(path, attribute, b"v3", os.XATTR_REPLACE)
        assert missing.value.errno in {errno.ENODATA, getattr(errno, "ENOATTR", -1)}
    finally:
        if created:
            os.removexattr(path, attribute)
