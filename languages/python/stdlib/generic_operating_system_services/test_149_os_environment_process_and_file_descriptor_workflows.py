"""149｜``os.environ``/``environb``、getenv、putenv trap 与 executable PATH。

``os.environ`` 是导入时捕获、与 C environment 同步的 mutable mapping。应修改
这个 mapping，而不是直接调用 ``putenv``：后者会影响 future child process，却不会
反向更新 Python mapping。Unix 的 ``environb`` 与 text view 双向同步，并使用
filesystem codec。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.environ python.os.environment-mapping
# polyglot-covers: python.os.getenv python.os.environment-default
# polyglot-covers: python.os.environment-set-delete python.os.environment-process-global
# polyglot-covers: python.os.environment-merge python.os.environment-update-merge
# polyglot-covers: python.os.putenv python.os.putenv-mapping-trap
# polyglot-covers: python.os.unsetenv python.os.environb
# polyglot-covers: python.os.getenvb python.os.supports-bytes-environ
# polyglot-covers: python.os.text-bytes-environ-sync python.os.get-exec-path
# polyglot-covers: python.os.PATH python.os.pathsep




import os
import pytest
import errno
import stat

def test_environ_mutation_is_visible_to_getenv_and_deletion_removes_it(monkeypatch):
    """修改 mapping 会自动调用 putenv/unsetenv；fixture 负责恢复全局状态。"""

    key = "POLYGLOT_OS_ENVIRON_CASE"
    monkeypatch.setitem(os.environ, key, "中文-value")

    assert os.environ[key] == "中文-value"
    assert os.getenv(key) == "中文-value"
    assert os.getenv("POLYGLOT_DEFINITELY_MISSING", "fallback") == "fallback"

    monkeypatch.delitem(os.environ, key)
    assert os.getenv(key) is None


def test_environ_merge_returns_copy_while_inplace_merge_updates_process():
    """PEP 584 的 | 不修改左侧；|= 会通过 _Environ 写入真实 process environment。"""

    key = "POLYGLOT_OS_ENVIRON_MERGE"
    merged = os.environ | {key: "copy-only"}

    assert merged[key] == "copy-only"
    assert key not in os.environ

    try:
        os.environ |= {key: "process-value"}
        assert os.getenv(key) == "process-value"
    finally:
        # 直接 |= 不在 monkeypatch 的 mutation log 中，所以本案例自己清理。
        os.environ.pop(key, None)


def test_direct_putenv_does_not_update_python_mapping():
    """getenv 读取 os.environ，而非 C environment；这是直接 putenv 的常见陷阱。"""

    key = "POLYGLOT_OS_DIRECT_PUTENV"
    os.environ.pop(key, None)
    os.putenv(key, "c-environment-only")
    try:
        assert key not in os.environ
        assert os.getenv(key) is None
    finally:
        os.unsetenv(key)


@pytest.mark.skipif(not os.supports_bytes_environ, reason="平台没有 bytes environment")
def test_environb_and_environ_are_synchronized_views(monkeypatch):
    """Unix bytes view 可无损表达非 text protocol；ASCII 案例展示双向同步。"""

    bytes_key = b"POLYGLOT_OS_BYTES_ENV"
    monkeypatch.setitem(os.environb, bytes_key, b"raw-value")

    assert os.getenvb(bytes_key) == b"raw-value"
    assert os.environ[bytes_key.decode()] == "raw-value"

    os.environ[bytes_key.decode()] = "changed"
    assert os.environb[bytes_key] == b"changed"


def test_get_exec_path_splits_explicit_path_without_searching_filesystem():
    """返回 search directories；空 component 也保留，shell 将其视作 current dir。"""

    supplied = os.pathsep.join(["/opt/tools", "", "/usr/local/bin"])

    assert os.get_exec_path({"PATH": supplied}) == [
        "/opt/tools",
        "",
        "/usr/local/bin",
    ]
    assert os.get_exec_path({}) == os.defpath.split(os.pathsep)


@pytest.mark.skipif(not os.supports_bytes_environ, reason="bytes PATH 只在部分平台存在")
def test_get_exec_path_rejects_ambiguous_text_and_bytes_path_keys():
    """env 同时给 'PATH' 与 b'PATH' 时没有可靠优先级，因此显式报 ValueError。"""

    with pytest.raises(ValueError, match="PATH"):
        os.get_exec_path({"PATH": "/text", b"PATH": b"/bytes"})


# 150｜``os`` process identity、cwd、fchdir、umask 与 Unix identity queries。
#
# 当前目录和 umask 都是 process-global 状态，不是 thread-local；临时修改必须用
# ``try/finally`` 恢复。PID/UID/group/process-group 查询是 read-only introspection；
# 会改变身份、session 或 scheduler 的 privileged setters 不适合普通测试进程演示。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.os.getpid python.os.getppid
# polyglot-covers: python.os.getcwd python.os.getcwdb
# polyglot-covers: python.os.chdir python.os.cwd-process-global
# polyglot-covers: python.os.fchdir python.os.cwd-restore
# polyglot-covers: python.os.umask python.os.umask-return-previous
# polyglot-covers: python.os.getuid python.os.geteuid
# polyglot-covers: python.os.getgid python.os.getegid
# polyglot-covers: python.os.getgroups python.os.getresuid
# polyglot-covers: python.os.getresgid python.os.getgrouplist
# polyglot-covers: python.os.getpgrp python.os.getpgid python.os.getsid
# polyglot-covers: python.os.getpriority python.os.strerror
# polyglot-covers: python.os.PRIO_PROCESS python.os.process-identity-readonly




def test_pid_and_parent_pid_are_non_negative_process_identifiers():
    """getpid 是当前进程 identity；父进程退出后 getppid 的平台语义不同。"""

    assert type(os.getpid()) is int
    assert os.getpid() > 0
    assert type(os.getppid()) is int
    assert os.getppid() >= 0


def test_chdir_changes_process_cwd_and_must_be_restored(tmp_path):
    """相对路径、open 和很多 higher-level API 都观察同一个 process cwd。"""

    original = os.getcwd()
    try:
        os.chdir(tmp_path)
        assert os.getcwd() == str(tmp_path)
        assert os.getcwdb() == os.fsencode(tmp_path)
    finally:
        os.chdir(original)

    assert os.getcwd() == original


@pytest.mark.skipif(not hasattr(os, "fchdir"), reason="平台不支持 directory fd chdir")
def test_fchdir_can_restore_directory_by_open_descriptor(tmp_path):
    """directory fd 不受 path rename 影响；这里用它可靠保存并恢复原 cwd。"""

    original_fd = os.open(".", os.O_RDONLY)
    original = os.getcwd()
    try:
        os.chdir(tmp_path)
        assert os.getcwd() != original
        os.fchdir(original_fd)
        assert os.getcwd() == original
    finally:
        os.fchdir(original_fd)
        os.close(original_fd)


def test_umask_returns_previous_value_and_is_restored():
    """umask 没有纯 getter；setter 返回旧值，所以读取也需要短暂 mutation。"""

    original = os.umask(0o077)
    try:
        observed = os.umask(original)
        assert observed == 0o077
    finally:
        os.umask(original)


@pytest.mark.skipif(os.name != "posix", reason="UID/GID API 属于 Unix")
def test_unix_real_effective_and_saved_ids_are_integer_queries():
    """real/effective 可因 set-id 不同；案例不假设容器以哪种用户运行。"""

    assert all(type(value) is int for value in (os.getuid(), os.geteuid()))
    assert all(type(value) is int for value in (os.getgid(), os.getegid()))
    assert all(type(value) is int for value in os.getgroups())

    if hasattr(os, "getresuid"):
        assert len(os.getresuid()) == 3
    if hasattr(os, "getresgid"):
        assert len(os.getresgid()) == 3


@pytest.mark.skipif(not hasattr(os, "getgrouplist"), reason="平台不提供 group database query")
def test_getgrouplist_includes_supplied_base_group_for_current_user():
    """supplemental database lookup 与 getgroups 的 process snapshot 不是同一问题。"""

    pwd = pytest.importorskip("pwd")
    username = pwd.getpwuid(os.getuid()).pw_name
    groups = os.getgrouplist(username, os.getgid())

    assert os.getgid() in groups
    assert all(type(group) is int for group in groups)


@pytest.mark.skipif(os.name != "posix", reason="process group API 属于 Unix")
def test_process_group_queries_agree_for_the_current_process():
    """getpgid 的 pid=0 表示 caller；查询不会改变 process group/session 拓扑。"""

    assert os.getpgid(0) == os.getpgrp()
    assert os.getpgid(os.getpid()) == os.getpgrp()
    if hasattr(os, "getsid"):
        assert os.getsid(0) == os.getsid(os.getpid())


@pytest.mark.skipif(not hasattr(os, "getpriority"), reason="平台不提供 scheduler priority")
def test_getpriority_reads_current_process_niceness_without_mutating_it():
    """PRIO_PROCESS + who=0 指 caller；权限和 OS policy 决定具体值。"""

    priority = os.getpriority(os.PRIO_PROCESS, 0)

    assert type(priority) is int
    assert -20 <= priority <= 19


def test_strerror_maps_errno_number_to_human_readable_platform_message():
    """message 会本地化且由 OS 决定；逻辑判断应比较 errno。"""

    message = os.strerror(errno.ENOENT)

    assert isinstance(message, str)
    assert message


# 151｜``os.open/read/write/lseek``、fdopen、fstat、truncate 与 buffering 边界。
#
# file descriptor 是无 buffering 的小整数 handle；``os`` 的低层 API 只收发 bytes。
# Python file object 另有 userspace buffer，混用前必须 flush/seek。``fdopen`` 可把现有 fd
# 包装成 file object，并由 ``closefd`` 决定 wrapper 是否取得 descriptor ownership。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.os.open python.os.open-flags
# polyglot-covers: python.os.O_CREAT python.os.O_EXCL
# polyglot-covers: python.os.O_TRUNC python.os.O_APPEND
# polyglot-covers: python.os.read python.os.write
# polyglot-covers: python.os.lseek python.os.SEEK_SET
# polyglot-covers: python.os.SEEK_CUR python.os.SEEK_END
# polyglot-covers: python.os.close python.os.fdopen
# polyglot-covers: python.os.fdopen-ownership python.os.closefd
# polyglot-covers: python.os.fstat python.os.ftruncate
# polyglot-covers: python.os.fsync python.os.buffer-flush-before-fsync
# polyglot-covers: python.os.isatty python.os.device-encoding
# polyglot-covers: python.os.fchmod python.os.low-level-bytes
# polyglot-covers: python.os.closerange python.os.closerange-half-open




def test_open_flags_create_exclusively_then_append_without_truncating(tmp_path):
    """O_EXCL 防止 race-prone overwrite；O_APPEND 保证每次 write 定位到文件尾。"""

    path = tmp_path / "events.bin"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        assert os.write(fd, b"first") == 5
    finally:
        os.close(fd)

    with pytest.raises(FileExistsError):
        os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)

    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        assert os.write(fd, b"-second") == 7
    finally:
        os.close(fd)

    assert path.read_bytes() == b"first-second"


def test_read_write_and_lseek_share_a_byte_offset(tmp_path):
    """lseek 单位是 bytes；EOF 返回 b''，不是 None 或异常。"""

    path = tmp_path / "random-access.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        assert os.write(fd, b"abcdef") == 6
        assert os.lseek(fd, 0, os.SEEK_SET) == 0
        assert os.read(fd, 2) == b"ab"
        assert os.lseek(fd, 1, os.SEEK_CUR) == 3
        assert os.read(fd, 2) == b"de"
        assert os.lseek(fd, 0, os.SEEK_END) == 6
        assert os.read(fd, 10) == b""
    finally:
        os.close(fd)


def test_fstat_and_ftruncate_operate_without_re_resolving_a_path(tmp_path):
    """descriptor 仍指向已打开对象；ftruncate 缩短数据并反映在 fstat size。"""

    path = tmp_path / "truncate.bin"
    path.write_bytes(b"0123456789")
    fd = os.open(path, os.O_RDWR)
    try:
        assert os.fstat(fd).st_size == 10
        assert os.ftruncate(fd, 4) is None
        assert os.fstat(fd).st_size == 4
    finally:
        os.close(fd)

    assert path.read_bytes() == b"0123"


def test_fdopen_closefd_controls_descriptor_ownership(tmp_path):
    """默认 wrapper close 一并关闭 fd；closefd=False 由调用方继续负责 close。"""

    owned_path = tmp_path / "owned.bin"
    owned_fd = os.open(owned_path, os.O_WRONLY | os.O_CREAT, 0o600)
    with os.fdopen(owned_fd, "wb") as stream:
        stream.write(b"owned")
    with pytest.raises(OSError):
        os.close(owned_fd)

    borrowed_path = tmp_path / "borrowed.bin"
    borrowed_fd = os.open(borrowed_path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        with os.fdopen(borrowed_fd, "wb", closefd=False) as stream:
            stream.write(b"borrowed")
        assert os.write(borrowed_fd, b"-still-open") == 11
    finally:
        os.close(borrowed_fd)

    assert borrowed_path.read_bytes() == b"borrowed-still-open"


def test_buffered_file_must_flush_before_fstat_and_fsync_see_bytes(tmp_path):
    """write 可只改 userspace buffer；flush 后 kernel size 才可靠，再 fsync。"""

    path = tmp_path / "buffered.bin"
    with path.open("wb") as stream:
        stream.write(b"buffered payload")
        assert os.fstat(stream.fileno()).st_size == 0

        stream.flush()
        assert os.fstat(stream.fileno()).st_size == len(b"buffered payload")
        assert os.fsync(stream.fileno()) is None


def test_regular_file_is_not_a_tty_and_has_no_device_encoding(tmp_path):
    """device_encoding 只描述 terminal device；普通 binary file 返回 None。"""

    path = tmp_path / "plain.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        assert os.isatty(fd) is False
        assert os.device_encoding(fd) is None
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "fchmod"), reason="平台不支持 fchmod")
def test_fchmod_changes_mode_through_descriptor(tmp_path):
    """权限变化不重新查找 path；只比较 permission bits，忽略 file type bits。"""

    path = tmp_path / "mode.bin"
    path.write_bytes(b"data")
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fchmod(fd, 0o640)
        assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o640
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="用 child 隔离 closerange 的 fd 影响")
def test_closerange_closes_half_open_interval_and_ignores_invalid_fds(tmp_path):
    """child 隔离避免误关 pytest fd；upper bound 不包含在关闭区间。"""

    report_read, report_write = os.pipe()
    base = os.open(tmp_path / "range.bin", os.O_RDWR | os.O_CREAT, 0o600)
    first = os.dup(base)
    upper = os.dup(base)
    pid = os.fork()
    if pid == 0:
        os.close(report_read)
        os.closerange(base, upper)
        try:
            closed = all(
                _descriptor_is_closed(fd)
                for fd in (base, first)
            )
            upper_open = not _descriptor_is_closed(upper)
            os.write(report_write, b"ok" if closed and upper_open else b"bad")
        finally:
            os.close(upper)
            os.close(report_write)
        os._exit(0)

    os.close(report_write)
    try:
        report = os.read(report_read, 10)
    finally:
        os.close(report_read)
        os.close(upper)
        os.close(first)
        os.close(base)
        _, status = os.waitpid(pid, 0)

    assert report == b"ok"
    assert os.waitstatus_to_exitcode(status) == 0


def _descriptor_is_closed(fd):
    try:
        os.fstat(fd)
    except OSError:
        return True
    return False


# 152｜``os.pipe``、dup/dup2、shared offset、blocking mode 与 inheritable flag。
#
# pipe 是单向 byte stream；关闭所有 write ends 后 reader 才观察 EOF。``dup`` 产生新的
# fd，但两个 fd 指向同一个 open file description，所以共享 cursor。Python 3.4+
# 创建的 fd 默认不可继承；若确需跨 exec 继承，必须显式设置并及时恢复。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.os.pipe python.os.pipe-eof
# polyglot-covers: python.os.pipe-non-inheritable python.os.dup
# polyglot-covers: python.os.dup-shared-offset python.os.dup-non-inheritable
# polyglot-covers: python.os.dup2 python.os.dup2-return-fd
# polyglot-covers: python.os.get-inheritable python.os.set-inheritable
# polyglot-covers: python.os.fd-inheritance python.os.get-blocking
# polyglot-covers: python.os.set-blocking python.os.nonblocking-read
# polyglot-covers: python.os.pipe2 python.os.O_NONBLOCK
# polyglot-covers: python.os.O_CLOEXEC python.os.openpty
# polyglot-covers: python.os.ttyname python.os.terminal-size
# polyglot-covers: python.os.get-terminal-size python.os.non-tty-error




def test_pipe_transfers_bytes_and_close_of_writer_produces_eof():
    """read end 不知道消息边界；关闭 write end 后，第二次 read 得到 EOF。"""

    read_fd, write_fd = os.pipe()
    try:
        assert os.get_inheritable(read_fd) is False
        assert os.get_inheritable(write_fd) is False
        assert os.write(write_fd, b"pipe payload") == len(b"pipe payload")
        os.close(write_fd)
        write_fd = None

        assert os.read(read_fd, 100) == b"pipe payload"
        assert os.read(read_fd, 1) == b""
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)


def test_dup_descriptors_share_the_same_open_file_offset(tmp_path):
    """dup 不 clone kernel cursor；任一 fd read 都推进 shared offset。"""

    path = tmp_path / "shared-offset.bin"
    path.write_bytes(b"abcdef")
    original = os.open(path, os.O_RDONLY)
    duplicate = os.dup(original)
    try:
        assert duplicate != original
        assert os.get_inheritable(duplicate) is False
        assert os.read(original, 2) == b"ab"
        assert os.read(duplicate, 2) == b"cd"
    finally:
        os.close(duplicate)
        os.close(original)


def test_dup2_retargets_an_existing_fd_and_controls_inheritability(tmp_path):
    """dup2 先关闭 target 所指对象，再令该 fd 指向 source open description。"""

    source_path = tmp_path / "source.bin"
    target_path = tmp_path / "target.bin"
    source_path.write_bytes(b"source")
    target_path.write_bytes(b"target")
    source = os.open(source_path, os.O_RDONLY)
    target = os.open(target_path, os.O_RDONLY)
    try:
        assert os.dup2(source, target, inheritable=False) == target
        assert os.get_inheritable(target) is False
        assert os.read(target, 6) == b"source"
    finally:
        os.close(target)
        os.close(source)


def test_inheritable_flag_can_be_toggled_and_restored(tmp_path):
    """flag 只影响 future child exec；它不会自动把 fd 内容复制到 child。"""

    fd = os.open(tmp_path / "inherit.bin", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        assert os.get_inheritable(fd) is False
        os.set_inheritable(fd, True)
        assert os.get_inheritable(fd) is True
        os.set_inheritable(fd, False)
        assert os.get_inheritable(fd) is False
    finally:
        os.close(fd)


@pytest.mark.skipif(not hasattr(os, "set_blocking"), reason="平台不支持 fd blocking flag")
def test_nonblocking_empty_pipe_raises_instead_of_waiting():
    """writer 打开时 empty pipe 不是 EOF；nonblocking read 会表示 would-block。"""

    read_fd, write_fd = os.pipe()
    try:
        assert os.get_blocking(read_fd) is True
        os.set_blocking(read_fd, False)
        assert os.get_blocking(read_fd) is False
        with pytest.raises(BlockingIOError):
            os.read(read_fd, 1)

        os.set_blocking(read_fd, True)
        assert os.get_blocking(read_fd) is True
    finally:
        os.close(write_fd)
        os.close(read_fd)


@pytest.mark.skipif(not hasattr(os, "pipe2"), reason="平台不支持 atomic pipe flags")
def test_pipe2_applies_nonblocking_and_close_on_exec_atomically():
    """O_NONBLOCK 与 O_CLOEXEC 在 fd 暴露给其他 threads 前由 kernel 一次设置。"""

    read_fd, write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        assert os.get_blocking(read_fd) is False
        assert os.get_blocking(write_fd) is False
        assert os.get_inheritable(read_fd) is False
        assert os.get_inheritable(write_fd) is False
    finally:
        os.close(write_fd)
        os.close(read_fd)


@pytest.mark.skipif(not hasattr(os, "openpty"), reason="平台不支持 pseudo-terminal")
def test_openpty_returns_non_inheritable_tty_descriptors():
    """slave 是 tty device，master/slave 均遵循 Python 的 non-inheritable default。"""

    master, slave = os.openpty()
    try:
        assert os.isatty(slave) is True
        assert os.ttyname(slave)
        assert os.get_inheritable(master) is False
        assert os.get_inheritable(slave) is False
    finally:
        os.close(slave)
        os.close(master)


def test_terminal_size_is_named_tuple_and_regular_file_query_fails(tmp_path):
    """low-level query 需要 tty；shutil.get_terminal_size 才提供 environment/fallback。"""

    size = os.terminal_size((80, 24))
    assert tuple(size) == (80, 24)
    assert size.columns == 80
    assert size.lines == 24

    fd = os.open(tmp_path / "not-a-terminal", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with pytest.raises(OSError):
            os.get_terminal_size(fd)
    finally:
        os.close(fd)


# 153｜``os.pread/pwrite``、readv/writev、preadv/pwritev 与 kernel-side copy。
#
# positioned I/O 显式给 offset 且不改变 shared file cursor，适合并发读取固定区段。
# vectored I/O 一次 syscall 处理多个 buffers，但返回值仍可能短于总长度。
# ``copy_file_range`` 和 ``splice`` 让 kernel 搬运数据；可用性还取决于 kernel 与当前
# filesystem。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.os.pread python.os.pwrite
# polyglot-covers: python.os.positioned-io-offset python.os.positioned-io-shared-cursor
# polyglot-covers: python.os.readv python.os.writev
# polyglot-covers: python.os.vectored-buffer-order python.os.vectored-short-count
# polyglot-covers: python.os.preadv python.os.pwritev
# polyglot-covers: python.os.copy-file-range python.os.kernel-side-copy
# polyglot-covers: python.os.copy-file-range-short-copy python.os.splice
# polyglot-covers: python.os.splice-pipe python.os.platform-capability-guard




@pytest.mark.skipif(not hasattr(os, "pread"), reason="平台不支持 positioned I/O")
def test_pread_and_pwrite_leave_shared_cursor_unchanged(tmp_path):
    """offset 参数独立于 open description cursor；返回 count 仍应由调用方检查。"""

    path = tmp_path / "positioned.bin"
    path.write_bytes(b"0123456789")
    fd = os.open(path, os.O_RDWR)
    try:
        assert os.lseek(fd, 3, os.SEEK_SET) == 3
        assert os.pread(fd, 4, 5) == b"5678"
        assert os.lseek(fd, 0, os.SEEK_CUR) == 3

        assert os.pwrite(fd, b"AB", 0) == 2
        assert os.lseek(fd, 0, os.SEEK_CUR) == 3
    finally:
        os.close(fd)

    assert path.read_bytes() == b"AB23456789"


@pytest.mark.skipif(not hasattr(os, "writev"), reason="平台不支持 vectored I/O")
def test_writev_processes_buffers_in_order(tmp_path):
    """small regular-file write 通常一次完成；通用代码仍须消费实际 count。"""

    path = tmp_path / "writev.bin"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        written = os.writev(fd, [b"header:", memoryview(b"body"), b":tail"])
    finally:
        os.close(fd)

    assert written == len(b"header:body:tail")
    assert path.read_bytes() == b"header:body:tail"


@pytest.mark.skipif(not hasattr(os, "readv"), reason="平台不支持 vectored I/O")
def test_readv_fills_mutable_buffers_in_sequence_and_can_stop_partway():
    """总 capacity 大于输入时，末尾 buffer 只有 prefix 被覆盖。"""

    read_fd, write_fd = os.pipe()
    first = bytearray(2)
    second = bytearray(b"xxxxx")
    try:
        os.write(write_fd, b"abcdef")
        os.close(write_fd)
        write_fd = None

        count = os.readv(read_fd, [first, second])
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)

    assert count == 6
    assert first == b"ab"
    assert second == b"cdefx"


@pytest.mark.skipif(not hasattr(os, "preadv"), reason="平台不支持 positioned vectors")
def test_preadv_and_pwritev_combine_positioned_and_vectored_semantics(tmp_path):
    """多个 buffers 按序映射到显式 offset，且不会推进当前 cursor。"""

    path = tmp_path / "positioned-vectors.bin"
    path.write_bytes(b"0123456789")
    fd = os.open(path, os.O_RDWR)
    first = bytearray(2)
    second = bytearray(3)
    try:
        os.lseek(fd, 7, os.SEEK_SET)
        assert os.preadv(fd, [first, second], 2) == 5
        assert (first, second) == (b"23", b"456")
        assert os.lseek(fd, 0, os.SEEK_CUR) == 7

        assert os.pwritev(fd, [b"AB", b"CD"], 0) == 4
        assert os.lseek(fd, 0, os.SEEK_CUR) == 7
    finally:
        os.close(fd)

    assert path.read_bytes() == b"ABCD456789"


@pytest.mark.skipif(not hasattr(os, "copy_file_range"), reason="平台不支持 kernel copy")
def test_copy_file_range_loops_because_one_call_may_copy_less(tmp_path):
    """API 返回实际 count；filesystem 不实现 syscall 时按 capability skip。"""

    source_path = tmp_path / "source.bin"
    target_path = tmp_path / "target.bin"
    payload = b"kernel-copy" * 100
    source_path.write_bytes(payload)
    source = os.open(source_path, os.O_RDONLY)
    target = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        total = 0
        try:
            while total < len(payload):
                copied = os.copy_file_range(source, target, len(payload) - total)
                if copied == 0:
                    break
                total += copied
        except OSError as error:
            if error.errno in {errno.ENOSYS, errno.EXDEV, errno.EINVAL, errno.EOPNOTSUPP}:
                pytest.skip(f"filesystem 不支持 copy_file_range: {error}")
            raise
    finally:
        os.close(target)
        os.close(source)

    assert total == len(payload)
    assert target_path.read_bytes() == payload


@pytest.mark.skipif(not hasattr(os, "splice"), reason="平台不支持 splice")
def test_splice_moves_bytes_from_pipe_to_file_without_userspace_buffer(tmp_path):
    """至少一端必须是 pipe；关闭 writer 后 source 不会等待更多输入。"""

    read_fd, write_fd = os.pipe()
    target_path = tmp_path / "spliced.bin"
    target = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(write_fd, b"through-kernel")
        os.close(write_fd)
        write_fd = None

        assert os.splice(read_fd, target, len(b"through-kernel")) == len(
            b"through-kernel"
        )
    finally:
        os.close(target)
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)

    assert target_path.read_bytes() == b"through-kernel"


# 154｜``os`` 的预分配、访问建议、record lock 与 ``sendfile``。
#
# 这些接口把文件系统和 kernel 能力直接暴露给 Python。它们仍以 file descriptor
# 和 bytes 为边界。“函数存在”不等于当前 filesystem 一定实现；能力差异
# 应显式 skip，而不能误判为业务断言失败。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.os.posix-fallocate python.os.file-preallocation
# polyglot-covers: python.os.posix-fadvise python.os.POSIX_FADV_SEQUENTIAL
# polyglot-covers: python.os.lockf python.os.F_LOCK python.os.F_ULOCK
# polyglot-covers: python.os.sendfile python.os.sendfile-offset
# polyglot-covers: python.os.sendfile-short-count python.os.kernel-side-transfer




_CAPABILITY_ERRNOS = {
    errno.ENOSYS,
    errno.EINVAL,
    errno.EOPNOTSUPP,
}


@pytest.mark.skipif(
    not hasattr(os, "posix_fallocate"),
    reason="平台不提供 POSIX file allocation",
)
def test_posix_fallocate_reserves_space_and_extends_logical_size(tmp_path):
    """预分配可减少以后写入时的 ENOSPC 风险，并把文件扩展到给定范围。"""

    path = tmp_path / "allocated.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        try:
            assert os.posix_fallocate(fd, 0, 4096) is None
        except OSError as error:
            if error.errno in _CAPABILITY_ERRNOS:
                pytest.skip(f"filesystem 不支持 posix_fallocate: {error}")
            raise

        assert os.fstat(fd).st_size == 4096
        assert os.pwrite(fd, b"tail", 4092) == 4
    finally:
        os.close(fd)

    assert path.read_bytes().endswith(b"tail")


@pytest.mark.skipif(
    not hasattr(os, "posix_fadvise"),
    reason="平台不提供 POSIX file advice",
)
def test_posix_fadvise_is_a_hint_not_a_data_operation(tmp_path):
    """advice 只给 kernel 优化提示；成功返回 None，内容和 cursor 均不改变。"""

    path = tmp_path / "advice.bin"
    path.write_bytes(b"abcdef")
    fd = os.open(path, os.O_RDONLY)
    try:
        before = os.lseek(fd, 2, os.SEEK_SET)
        try:
            result = os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_SEQUENTIAL)
        except OSError as error:
            if error.errno in _CAPABILITY_ERRNOS:
                pytest.skip(f"filesystem 不支持 posix_fadvise: {error}")
            raise

        assert result is None
        assert os.lseek(fd, 0, os.SEEK_CUR) == before
    finally:
        os.close(fd)

    assert path.read_bytes() == b"abcdef"


@pytest.mark.skipif(not hasattr(os, "lockf"), reason="平台不提供 POSIX record locks")
def test_lockf_lock_and_unlock_wrap_a_descriptor_critical_section(tmp_path):
    """lockf 锁由进程和 byte range 定义；正常路径也必须在 finally 中解锁。"""

    path = tmp_path / "locked.bin"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.lockf(fd, os.F_LOCK, 0)
        try:
            assert os.write(fd, b"protected") == 9
        finally:
            os.lockf(fd, os.F_ULOCK, 0)
    finally:
        os.close(fd)

    assert path.read_bytes() == b"protected"


@pytest.mark.skipif(not hasattr(os, "sendfile"), reason="平台不提供 sendfile")
def test_sendfile_uses_explicit_input_offset_and_returns_actual_count(tmp_path):
    """显式 offset 不推进 input fd cursor；output cursor 仍按实际传输量前进。"""

    source_path = tmp_path / "source.bin"
    target_path = tmp_path / "target.bin"
    source_path.write_bytes(b"0123456789")
    source = os.open(source_path, os.O_RDONLY)
    target = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.lseek(source, 8, os.SEEK_SET)
        sent = 0
        try:
            while sent < 5:
                count = os.sendfile(target, source, 2 + sent, 5 - sent)
                if count == 0:
                    break
                sent += count
        except OSError as error:
            if error.errno in _CAPABILITY_ERRNOS:
                pytest.skip(f"kernel/filesystem 不支持此 sendfile: {error}")
            raise

        assert sent == 5
        assert os.lseek(source, 0, os.SEEK_CUR) == 8
        assert os.lseek(target, 0, os.SEEK_CUR) == 5
    finally:
        os.close(target)
        os.close(source)

    assert target_path.read_bytes() == b"23456"
