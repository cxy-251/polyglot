"""172｜fcntl、resource 与 syslog：描述符控制、资源边界和日志策略。

fcntl 直接映射平台相关的 fcntl/ioctl/锁协议；resource 查询或设置进程资源；
syslog 则管理进程级日志设施与优先级。
本套只操作临时文件、pipe、pty 和当前
进程的可恢复状态，不向真实系统日志写消息，也不永久降低资源上限。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.stdlib.fcntl python.fcntl.fcntl
# polyglot-covers: python.fcntl.file-status-flags python.fcntl.descriptor-flags
# polyglot-covers: python.fcntl.ioctl python.fcntl.mutable-buffer
# polyglot-covers: python.fcntl.readonly-buffer python.fcntl.buffer-limit
# polyglot-covers: python.fcntl.flock python.fcntl.lockf python.fcntl.nonblocking-lock
# polyglot-covers: python.fcntl.pipe-size-3.10 python.fcntl.memfd-seals
# polyglot-covers: python.stdlib.resource python.resource.getrlimit
# polyglot-covers: python.resource.setrlimit python.resource.soft-hard-limits
# polyglot-covers: python.resource.rlim-infinity python.resource.prlimit
# polyglot-covers: python.resource.getrusage python.resource.struct-rusage
# polyglot-covers: python.resource.getpagesize python.resource.platform-constants
# polyglot-covers: python.stdlib.syslog python.syslog.openlog-closelog
# polyglot-covers: python.syslog.priorities python.syslog.facilities
# polyglot-covers: python.syslog.log-mask python.syslog.log-upto
# polyglot-covers: python.syslog.external-side-effect

import errno
import os
import struct

import pytest


pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="fcntl、resource 和 syslog 仅在 Unix 平台提供",
)

if os.name == "posix":
    import fcntl
    import pty
    import resource
    import syslog
    import termios
else:
    fcntl = None
    pty = None
    resource = None
    syslog = None
    termios = None


def test_fcntl_getfl_and_setfl_toggle_nonblocking_pipe_reads():
    read_fd, write_fd = os.pipe()
    try:
        original = fcntl.fcntl(read_fd, fcntl.F_GETFL)
        assert isinstance(original, int)

        assert fcntl.fcntl(
            read_fd,
            fcntl.F_SETFL,
            original | os.O_NONBLOCK,
        ) == 0
        assert fcntl.fcntl(read_fd, fcntl.F_GETFL) & os.O_NONBLOCK
        with pytest.raises(BlockingIOError):
            os.read(read_fd, 1)
    finally:
        fcntl.fcntl(read_fd, fcntl.F_SETFL, original)
        os.close(read_fd)
        os.close(write_fd)


def test_fcntl_descriptor_flags_and_duplication_are_separate_from_status_flags(
    tmp_path,
):
    path = tmp_path / "descriptor.txt"
    with path.open("w+b") as file_object:
        descriptor = file_object.fileno()
        original = fcntl.fcntl(descriptor, fcntl.F_GETFD)
        try:
            assert fcntl.fcntl(
                descriptor,
                fcntl.F_SETFD,
                original | fcntl.FD_CLOEXEC,
            ) == 0
            assert fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC

            duplicate = fcntl.fcntl(descriptor, fcntl.F_DUPFD, 50)
            try:
                assert duplicate >= 50
                assert os.fstat(duplicate).st_ino == os.fstat(descriptor).st_ino
            finally:
                os.close(duplicate)
        finally:
            fcntl.fcntl(descriptor, fcntl.F_SETFD, original)
    # F_GETFD 管描述符自身的 close-on-exec，F_GETFL 管共享 open file description。


def test_ioctl_returns_bytes_for_readonly_input_and_mutates_writable_buffers():
    master, slave = pty.openpty()
    try:
        packed = struct.pack("HHHH", 0, 0, 0, 0)
        returned = fcntl.ioctl(slave, termios.TIOCGWINSZ, packed)
        assert isinstance(returned, bytes)
        assert len(returned) == len(packed)
        assert len(struct.unpack("HHHH", returned)) == 4

        mutable = bytearray(packed)
        result = fcntl.ioctl(
            slave,
            termios.TIOCGWINSZ,
            mutable,
            True,
        )
        assert result == 0
        assert bytes(mutable) == returned
    finally:
        os.close(master)
        os.close(slave)
    # bytes 模式复制并返回同长度结果且受 1024 字节限制；
    # bytearray 默认原地更新。


def test_flock_nonblocking_mode_reports_contention_with_portable_errnos(tmp_path):
    path = tmp_path / "flock.bin"
    path.write_bytes(b"lock target")
    with path.open("r+b") as first, path.open("r+b") as second:
        fcntl.flock(first, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(OSError) as caught:
                fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
            assert caught.value.errno in {errno.EACCES, errno.EAGAIN}
        finally:
            fcntl.flock(first, fcntl.LOCK_UN)

        assert fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB) is None
        fcntl.flock(second, fcntl.LOCK_UN)


def test_lockf_uses_explicit_region_length_start_and_whence(tmp_path):
    path = tmp_path / "regions.bin"
    path.write_bytes(b"0123456789")
    with path.open("r+b") as file_object:
        assert fcntl.lockf(
            file_object,
            fcntl.LOCK_EX | fcntl.LOCK_NB,
            4,
            2,
            os.SEEK_SET,
        ) is None
        assert fcntl.lockf(
            file_object,
            fcntl.LOCK_UN,
            4,
            2,
            os.SEEK_SET,
        ) is None
    # len=0 才表示直到文件尾；结构化 F_SETLK 的 struct 布局跨平台不稳定。


def test_linux_pipe_size_constants_are_feature_detected_not_assumed():
    if not hasattr(fcntl, "F_GETPIPE_SZ"):
        pytest.skip("当前 Unix 不提供 Linux pipe size fcntl")

    read_fd, write_fd = os.pipe()
    try:
        size = fcntl.fcntl(read_fd, fcntl.F_GETPIPE_SZ)
    finally:
        os.close(read_fd)
        os.close(write_fd)

    assert isinstance(size, int)
    assert size > 0
    assert hasattr(fcntl, "F_SETPIPE_SZ")


def test_linux_memfd_seals_prevent_resize_without_named_files():
    required = (
        "F_ADD_SEALS",
        "F_GET_SEALS",
        "F_SEAL_GROW",
        "F_SEAL_SHRINK",
    )
    supports_memfd = hasattr(os, "memfd_create")
    supports_sealing_flag = hasattr(os, "MFD_ALLOW_SEALING")
    supports_seals = all(hasattr(fcntl, name) for name in required)
    if not (supports_memfd and supports_sealing_flag and supports_seals):
        pytest.skip("当前 Unix 不支持 Linux memfd seals")

    descriptor = os.memfd_create("polyglot", os.MFD_ALLOW_SEALING)
    try:
        os.ftruncate(descriptor, 8)
        seals = fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK
        assert fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, seals) == 0
        assert fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) & seals == seals

        with pytest.raises(PermissionError):
            os.ftruncate(descriptor, 4)
        with pytest.raises(PermissionError):
            os.ftruncate(descriptor, 16)
    finally:
        os.close(descriptor)


def test_resource_limits_are_soft_hard_pairs_and_same_value_is_reversible():
    limits = resource.getrlimit(resource.RLIMIT_NOFILE)

    assert isinstance(limits, tuple)
    assert len(limits) == 2
    soft, hard = limits
    assert soft == resource.RLIM_INFINITY or soft >= 0
    assert hard == resource.RLIM_INFINITY or hard >= soft

    try:
        assert resource.setrlimit(resource.RLIMIT_NOFILE, limits) is None
        assert resource.getrlimit(resource.RLIMIT_NOFILE) == limits
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, limits)

    assert resource.error is OSError


def test_resource_rejects_invalid_ids_and_soft_limits_above_hard_limits():
    with pytest.raises(ValueError):
        resource.getrlimit(10**9)

    with pytest.raises(ValueError):
        resource.setrlimit(resource.RLIMIT_NOFILE, (2, 1))


def test_prlimit_queries_the_current_process_when_platform_supports_it():
    if not hasattr(resource, "prlimit"):
        pytest.skip("当前 Unix 不提供 Linux prlimit")

    by_pid_zero = resource.prlimit(0, resource.RLIMIT_NOFILE)
    by_getrlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
    assert by_pid_zero == by_getrlimit


def test_getrusage_returns_named_fields_and_cpu_time_is_monotonic():
    before = resource.getrusage(resource.RUSAGE_SELF)
    sum(number * number for number in range(20_000))
    after = resource.getrusage(resource.RUSAGE_SELF)

    assert type(after).__name__ == "struct_rusage"
    assert after.ru_utime >= before.ru_utime
    assert after.ru_stime >= before.ru_stime
    assert after.ru_maxrss >= 0
    assert len(after) == 16
    # ru_maxrss 的单位在 Linux 与 macOS 不同，跨平台代码不要直接假定是字节。


def test_getpagesize_and_resource_constants_remain_platform_specific():
    page_size = resource.getpagesize()
    assert page_size > 0
    assert page_size & (page_size - 1) == 0
    assert hasattr(resource, "RLIMIT_CORE")
    assert hasattr(resource, "RLIMIT_CPU")
    # RLIMIT_* 集合由操作系统决定；使用某个可选上限前应先 hasattr。


def test_syslog_constants_build_facilities_priorities_and_masks():
    priorities = [
        syslog.LOG_EMERG,
        syslog.LOG_ALERT,
        syslog.LOG_CRIT,
        syslog.LOG_ERR,
        syslog.LOG_WARNING,
        syslog.LOG_NOTICE,
        syslog.LOG_INFO,
        syslog.LOG_DEBUG,
    ]
    assert priorities == sorted(priorities)
    assert syslog.LOG_MASK(syslog.LOG_ERR) == 1 << syslog.LOG_ERR
    assert syslog.LOG_UPTO(syslog.LOG_WARNING) & syslog.LOG_MASK(
        syslog.LOG_EMERG
    )
    assert syslog.LOG_USER != syslog.LOG_LOCAL0


def test_syslog_setlogmask_returns_previous_mask_and_can_be_restored():
    original = syslog.setlogmask(0)
    warning_or_higher = syslog.LOG_UPTO(syslog.LOG_WARNING)
    try:
        previous = syslog.setlogmask(warning_or_higher)
        assert previous == original
        assert syslog.setlogmask(0) == warning_or_higher
    finally:
        syslog.setlogmask(original)


def test_syslog_openlog_configures_process_state_without_emitting_messages():
    options = syslog.LOG_PID | syslog.LOG_NDELAY
    assert syslog.openlog("polyglot-test", options, syslog.LOG_USER) is None
    try:
        assert callable(syslog.syslog)
        # syslog.syslog 会写入真实系统日志；
        # 本仓库只展示调用入口，不制造外部记录。
    finally:
        assert syslog.closelog() is None
