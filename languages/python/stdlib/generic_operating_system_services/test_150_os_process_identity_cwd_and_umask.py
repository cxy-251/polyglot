"""150｜``os`` process identity、cwd、fchdir、umask 与 Unix identity queries。

当前目录和 umask 都是 process-global 状态，不是 thread-local；临时修改必须用
``try/finally`` 恢复。PID/UID/group/process-group 查询是 read-only introspection；
会改变身份、session 或 scheduler 的 privileged setters 不适合普通测试进程演示。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import errno
import os

import pytest


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
