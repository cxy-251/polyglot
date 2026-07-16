"""079｜``fork``、child-only ``_exit``、``waitpid`` 与 nonblocking wait。

``fork`` 复制进程状态，并在 parent/child 返回不同值。child 分支必须尽快
进入明确路径；发生错误也要以 ``_exit`` 终止，避免继续跑 pytest runner。
parent 必须 reap child，否则会留下 zombie process。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.os.fork python.os.fork-parent-child-return
# polyglot-covers: python.os._exit python.os.child-exit-without-cleanup
# polyglot-covers: python.os.waitpid python.os.WIFEXITED
# polyglot-covers: python.os.WEXITSTATUS python.os.waitstatus-to-exitcode
# polyglot-covers: python.os.WNOHANG python.os.waitpid-nohang-zero
# polyglot-covers: python.os.fork-pipe-synchronization python.os.zombie-reaping




import os
import pytest
import sys
import signal

def _read_fork_pipe(fd):
    chunks = []
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork")
def test_fork_child_writes_pipe_and_parent_decodes_wait_status():
    """pipe 传业务数据；wait status 是编码值，不能直接当 child exit code。"""

    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        try:
            os.write(write_fd, b"child-payload")
        finally:
            os.close(write_fd)
        os._exit(7)

    os.close(write_fd)
    try:
        payload = _read_fork_pipe(read_fd)
    finally:
        os.close(read_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert payload == b"child-payload"
    assert waited_pid == pid
    assert os.WIFEXITED(status) is True
    assert os.WEXITSTATUS(status) == 7
    assert os.waitstatus_to_exitcode(status) == 7


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork")
def test_waitpid_wnohang_returns_zero_while_child_is_blocked_on_pipe():
    """(0, 0) 表示还没有可回收状态，不表示 pid=0 的 child 已完成。"""

    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(write_fd)
        try:
            os.read(read_fd, 1)
        finally:
            os.close(read_fd)
        os._exit(0)

    os.close(read_fd)
    try:
        assert os.waitpid(pid, os.WNOHANG) == (0, 0)
    finally:
        # EOF 解除 child 的阻塞，然后无条件 reap，避免断言失败时留下 zombie。
        os.close(write_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 0


# ``execv``/``execvpe`` 的 process replacement、argv 与 environment。
#
# exec family 不创建新进程，而是替换 caller image；成功时永不返回。因此案例先
# fork 隔离 pytest parent，再把 child stdout 接到 pipe。``v`` 接受 argv sequence，
# ``p`` 搜索 PATH，末尾 ``e`` 则用传入 mapping 完全替换 inherited environment。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.execv python.os.exec-process-replacement
# polyglot-covers: python.os.exec-argv-zero python.os.exec-never-returns
# polyglot-covers: python.os.execvpe python.os.exec-path-search
# polyglot-covers: python.os.exec-explicit-environment python.os.exec-environment-replacement
# polyglot-covers: python.os.exec-descriptors-not-flushed python.os.exec-fork-isolation




def _read_exec_pipe(fd):
    chunks = []
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _fork_exec_and_capture(operation):
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        os.dup2(write_fd, 1, inheritable=True)
        os.close(write_fd)
        try:
            operation()
        except BaseException:
            os._exit(120)
        os._exit(121)

    os.close(write_fd)
    try:
        output = _read_exec_pipe(read_fd)
    finally:
        os.close(read_fd)
        _, status = os.waitpid(pid, 0)
    return output, os.waitstatus_to_exitcode(status)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork/exec 隔离")
def test_execv_replaces_child_and_uses_explicit_executable_path():
    """argv[0] 按约定放 program name；API 不会替调用方自动补上它。"""

    code = "import os; os.write(1, b'execv-ok')"

    def execute():
        os.execv(sys.executable, [sys.executable, "-c", code])

    output, exit_code = _fork_exec_and_capture(execute)

    assert output == b"execv-ok"
    assert exit_code == 0


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork/exec 隔离")
def test_execvpe_searches_supplied_path_and_replaces_environment():
    """p/e variant 搜索新 environment 的 PATH，而不是 parent 当前 PATH。"""

    executable_name = os.path.basename(sys.executable)
    environment = {
        "PATH": os.path.dirname(sys.executable),
        "POLYGLOT_CHILD_VALUE": "explicit-only",
    }
    code = (
        "import os; "
        "os.write(1, os.environ['POLYGLOT_CHILD_VALUE'].encode('ascii'))"
    )

    def execute():
        os.execvpe(
            executable_name,
            [executable_name, "-c", code],
            environment,
        )

    output, exit_code = _fork_exec_and_capture(execute)

    assert output == b"explicit-only"
    assert exit_code == 0

    # exec 不会替 caller flush file-object buffers；进入前应自行 flush/fsync。


# ``posix_spawn`` file actions、legacy ``spawn*``、popen 与 system status。
#
# ``posix_spawn`` 可在启动 child 前安排 fd open/close/dup2，避免 Python child 分支。
# 旧 ``spawn*``、``popen`` 和 ``system`` 仍需理解，但新代码通常应使用
# ``subprocess``；尤其 shell string 会引入 quoting/injection 和平台差异。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.posix-spawn python.os.posix-spawn-file-actions
# polyglot-covers: python.os.POSIX_SPAWN_DUP2 python.os.POSIX_SPAWN_CLOSE
# polyglot-covers: python.os.posix-spawn-environment python.os.posix-spawn-waitpid
# polyglot-covers: python.os.spawnv python.os.P_WAIT
# polyglot-covers: python.os.spawnv-nowait python.os.P_NOWAIT
# polyglot-covers: python.os.popen python.os.popen-close-status
# polyglot-covers: python.os.system python.os.system-wait-status
# polyglot-covers: python.os.legacy-process-launcher-trap




def _read_spawn_pipe(fd):
    chunks = []
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


@pytest.mark.skipif(not hasattr(os, "posix_spawn"), reason="平台不提供 posix_spawn")
def test_posix_spawn_file_actions_redirect_stdout_without_python_child_code():
    """actions 在 exec 前执行；parent 仍须关闭 write end 才能读到 EOF。"""

    read_fd, write_fd = os.pipe()
    code = "import os; os.write(1, b'spawn-output')"
    actions = [
        (os.POSIX_SPAWN_DUP2, write_fd, 1),
        (os.POSIX_SPAWN_CLOSE, read_fd),
        (os.POSIX_SPAWN_CLOSE, write_fd),
    ]
    pid = os.posix_spawn(
        sys.executable,
        [sys.executable, "-c", code],
        os.environ.copy(),
        file_actions=actions,
    )

    os.close(write_fd)
    try:
        output = _read_spawn_pipe(read_fd)
    finally:
        os.close(read_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert output == b"spawn-output"
    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 0


@pytest.mark.skipif(not hasattr(os, "spawnv"), reason="平台不提供 legacy spawnv")
def test_spawnv_wait_returns_code_while_nowait_returns_pid():
    """P_WAIT 直接给 decoded code；P_NOWAIT 给 pid，caller 必须另行 wait。"""

    waited_code = os.spawnv(
        os.P_WAIT,
        sys.executable,
        [sys.executable, "-c", "raise SystemExit(6)"],
    )
    assert waited_code == 6

    pid = os.spawnv(
        os.P_NOWAIT,
        sys.executable,
        [sys.executable, "-c", "raise SystemExit(4)"],
    )
    waited_pid, status = os.waitpid(pid, 0)
    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 4


@pytest.mark.skipif(os.name != "posix", reason="本例依赖 POSIX shell 与 wait status")
def test_popen_and_system_expose_legacy_shell_status_conventions():
    """成功 popen close 返回 None；system 返回 encoded status，而非裸 code。"""

    stream = os.popen("printf polyglot", mode="r")
    assert stream.read() == "polyglot"
    assert stream.close() is None

    status = os.system("exit 7")
    assert os.WIFEXITED(status)
    assert os.waitstatus_to_exitcode(status) == 7


# ``kill`` signal status、``waitid`` peek、``wait4`` 与 Linux pidfd。
#
# signal termination 的 wait status 与正常 exit 不同；先用 ``WIFSIGNALED`` 再读
# ``WTERMSIG``。``WNOWAIT`` 可以观察 child 而不 reap，pidfd 则用稳定 descriptor 引用
# process，避免 PID reuse race。案例用 pipe handshake，不依赖 sleep。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.kill python.os.WIFSIGNALED
# polyglot-covers: python.os.WTERMSIG python.os.signal-negative-exitcode
# polyglot-covers: python.os.waitid python.os.P_PID
# polyglot-covers: python.os.WEXITED python.os.WNOWAIT python.os.CLD_EXITED
# polyglot-covers: python.os.wait4 python.os.wait4-resource-usage
# polyglot-covers: python.os.pidfd-open python.os.pidfd-non-inheritable




def _fork_blocked_child():
    ready_read, ready_write = os.pipe()
    block_read, block_write = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(ready_read)
        os.close(block_write)
        os.write(ready_write, b"R")
        os.close(ready_write)
        os.read(block_read, 1)
        os.close(block_read)
        os._exit(0)

    os.close(ready_write)
    os.close(block_read)
    assert os.read(ready_read, 1) == b"R"
    os.close(ready_read)
    return pid, block_write


@pytest.mark.skipif(not hasattr(os, "fork"), reason="平台不提供 fork")
def test_kill_termination_is_decoded_as_negative_signal_exit_code():
    """pipe handshake 证明 child 已启动；SIGTERM 后 parent 负责 waitpid 回收。"""

    pid, unblock_fd = _fork_blocked_child()
    try:
        os.kill(pid, signal.SIGTERM)
    finally:
        os.close(unblock_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert waited_pid == pid
    assert os.WIFSIGNALED(status) is True
    assert os.WTERMSIG(status) == signal.SIGTERM
    assert os.waitstatus_to_exitcode(status) == -signal.SIGTERM


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("fork", "waitid", "WNOWAIT")),
    reason="平台不提供 waitid WNOWAIT",
)
def test_waitid_wnowait_observes_child_then_waitpid_reaps_it():
    """siginfo 是 named result；WNOWAIT 留下 waitable status 供随后 waitpid 消费。"""

    pid = os.fork()
    if pid == 0:
        os._exit(9)

    info = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
    waited_pid, status = os.waitpid(pid, 0)

    assert info.si_pid == pid
    assert info.si_code == os.CLD_EXITED
    assert info.si_status == 9
    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 9


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("fork", "wait4")),
    reason="平台不提供 wait4",
)
def test_wait4_returns_wait_status_and_child_resource_usage():
    """rusage 与 encoded status 分开返回；不要把三元组第二项当裸 code。"""

    pid = os.fork()
    if pid == 0:
        os._exit(3)

    waited_pid, status, usage = os.wait4(pid, 0)

    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 3
    assert usage.ru_utime >= 0
    assert usage.ru_stime >= 0


@pytest.mark.skipif(
    not all(hasattr(os, name) for name in ("fork", "pidfd_open")),
    reason="kernel/Python 不提供 pidfd",
)
def test_pidfd_open_returns_non_inheritable_process_descriptor():
    """pidfd 稳定引用特定 process；flags 在 3.10 必须为零。"""

    pid, unblock_fd = _fork_blocked_child()
    process_fd = None
    try:
        try:
            process_fd = os.pidfd_open(pid, 0)
        except OSError as error:
            pytest.skip(f"running kernel 不支持 pidfd_open: {error}")
        assert os.get_inheritable(process_fd) is False
    finally:
        if process_fd is not None:
            os.close(process_fd)
        os.close(unblock_fd)
        waited_pid, status = os.waitpid(pid, 0)

    assert waited_pid == pid
    assert os.waitstatus_to_exitcode(status) == 0


# ``os`` scheduler 的 read-only introspection、affinity 与 process times。
#
# scheduler setters 会改变测试进程并可能需要 privilege，本文件只查询 policy、
# priority、CPU affinity 和 timing。``sched_yield`` 是无返回值的调度提示，不保证
# 另一 thread/process 一定立即获得 CPU。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.sched-getscheduler python.os.sched-getparam
# polyglot-covers: python.os.sched-param python.os.sched-priority-range
# polyglot-covers: python.os.sched-get-priority-min python.os.sched-get-priority-max
# polyglot-covers: python.os.sched-getaffinity python.os.cpu-affinity
# polyglot-covers: python.os.sched-yield python.os.scheduler-readonly-introspection
# polyglot-covers: python.os.times python.os.times-result




@pytest.mark.skipif(
    not all(
        hasattr(os, name)
        for name in (
            "sched_getscheduler",
            "sched_getparam",
            "sched_get_priority_min",
            "sched_get_priority_max",
        )
    ),
    reason="平台不提供 scheduler introspection",
)
def test_scheduler_policy_parameter_and_priority_range_are_consistent():
    """pid=0 表示 caller；sched_param 是带 named field 的 immutable tuple-like。"""

    policy = os.sched_getscheduler(0)
    parameter = os.sched_getparam(0)
    minimum = os.sched_get_priority_min(policy)
    maximum = os.sched_get_priority_max(policy)

    assert isinstance(parameter, os.sched_param)
    assert tuple(parameter) == (parameter.sched_priority,)
    assert minimum <= parameter.sched_priority <= maximum


@pytest.mark.skipif(
    not hasattr(os, "sched_getaffinity"),
    reason="平台不提供 CPU affinity query",
)
def test_affinity_is_usable_cpu_set_not_machine_cpu_count():
    """container/cgroup 可限制 usable CPUs，所以 affinity 可能小于 cpu_count。"""

    affinity = os.sched_getaffinity(0)
    machine_count = os.cpu_count()

    assert isinstance(affinity, set)
    assert affinity
    assert all(type(cpu) is int and cpu >= 0 for cpu in affinity)
    if machine_count is not None:
        assert len(affinity) <= machine_count


@pytest.mark.skipif(not hasattr(os, "sched_yield"), reason="平台不提供 sched_yield")
def test_sched_yield_returns_none_without_promising_execution_order():
    """yield 只主动放弃当前 time slice；没有可调度 peer 时可以立即继续。"""

    assert os.sched_yield() is None


def test_times_result_has_named_fields_and_legacy_five_tuple_view():
    """CPU time 与 elapsed real time 不是同一时钟，不能彼此替代。"""

    measured = os.times()

    assert len(measured) == 5
    assert tuple(measured) == (
        measured.user,
        measured.system,
        measured.children_user,
        measured.children_system,
        measured.elapsed,
    )
    assert all(value >= 0 for value in measured)


# system configuration、platform constants、``urandom`` 与 ``getrandom``。
#
# ``cpu_count`` 描述机器 CPU 数而非当前 process affinity；confstr/sysconf 的已知
# 名称来自 mapping，值仍由 host 决定。OS randomness 可用于加密，但应用层 token
# 通常应优先使用 ``secrets``；``getrandom`` 还允许 short read，caller 必须累计。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.os.uname python.os.uname-result
# polyglot-covers: python.os.confstr python.os.confstr-names
# polyglot-covers: python.os.sysconf python.os.sysconf-names
# polyglot-covers: python.os.cpu-count python.os.getloadavg
# polyglot-covers: python.os.curdir python.os.pardir python.os.sep python.os.altsep
# polyglot-covers: python.os.extsep python.os.linesep python.os.devnull
# polyglot-covers: python.os.urandom python.os.os-random-bytes
# polyglot-covers: python.os.getrandom python.os.getrandom-short-read
# polyglot-covers: python.os.GRND_NONBLOCK python.os.randomness-layer-choice




@pytest.mark.skipif(not hasattr(os, "uname"), reason="平台不提供 uname")
def test_uname_is_named_tuple_without_assuming_specific_host_values():
    """测试结构和非空字段，不把 container/host 的 identity 固化成 fixture。"""

    info = os.uname()

    assert len(info) == 5
    assert tuple(info) == (
        info.sysname,
        info.nodename,
        info.release,
        info.version,
        info.machine,
    )
    assert info.sysname
    assert info.machine


@pytest.mark.skipif(not hasattr(os, "sysconf"), reason="平台不提供 sysconf")
def test_sysconf_uses_discoverable_names_and_rejects_unknown_string():
    """known mapping 只保证名称可传；具体值可为 -1，表示 host 未定义。"""

    name = "SC_OPEN_MAX"
    if name not in os.sysconf_names:
        pytest.skip(f"host 不认识 {name}")

    value = os.sysconf(name)
    assert type(value) is int
    assert os.sysconf_names[name] == os.sysconf_names.get(name)
    with pytest.raises(ValueError):
        os.sysconf("POLYGLOT_UNKNOWN_SYSCONF")


@pytest.mark.skipif(not hasattr(os, "confstr"), reason="平台不提供 confstr")
def test_confstr_returns_string_or_none_for_a_known_name():
    """known name 的配置也可能未定义，此时返回 None 而非空字符串。"""

    name = "CS_PATH"
    if name not in os.confstr_names:
        pytest.skip(f"host 不认识 {name}")

    value = os.confstr(name)
    assert value is None or isinstance(value, str)
    with pytest.raises(ValueError):
        os.confstr("POLYGLOT_UNKNOWN_CONFSTR")


def test_cpu_load_and_path_constants_are_queries_not_path_parsers():
    """separator constants 用于显示/底层互操作；拼接和拆分仍应交给 os.path。"""

    count = os.cpu_count()
    assert count is None or count >= 1
    assert os.curdir
    assert os.pardir
    assert os.sep
    assert os.altsep is None or isinstance(os.altsep, str)
    assert os.extsep
    assert os.linesep

    with open(os.devnull, "wb") as sink:
        assert sink.write(b"discarded") == 9

    if hasattr(os, "getloadavg"):
        load = os.getloadavg()
        assert len(load) == 3
        assert all(value >= 0 for value in load)


def test_urandom_returns_exact_length_bytes_without_text_encoding():
    """随机 bytes 不应断言具体值；零长度请求也合法并精确返回 b''。"""

    first = os.urandom(16)
    second = os.urandom(16)

    assert type(first) is bytes
    assert len(first) == 16
    assert len(second) == 16
    assert os.urandom(0) == b""

    # “通常不同”不是可证明契约，不能作为 correctness assertion。


@pytest.mark.skipif(not hasattr(os, "getrandom"), reason="平台不提供 getrandom")
def test_getrandom_loop_handles_short_reads_without_requesting_random_pool():
    """默认 pool 适合本例；不调用可能消耗稀缺 entropy 的 GRND_RANDOM。"""

    chunks = []
    remaining = 32
    while remaining:
        try:
            chunk = os.getrandom(remaining, os.GRND_NONBLOCK)
        except BlockingIOError:
            pytest.skip("kernel entropy pool 尚未初始化，nonblocking read 暂不可用")
        if not chunk:
            pytest.fail("getrandom 在未满足请求时返回空 bytes")
        chunks.append(chunk)
        remaining -= len(chunk)

    result = b"".join(chunks)
    assert len(result) == 32
    assert type(result) is bytes
