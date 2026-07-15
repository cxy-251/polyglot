"""348｜信号、处理动作与 mask 常量的枚举接口。

Python 3.5 起，常见 SIG*、SIG_DFL/SIG_IGN 和 SIG_BLOCK 等常量分别属于 IntEnum；它们仍可作为
整数传给系统 API，同时具备可读名称。可用信号是平台能力，valid_signals 比假定 ``1..NSIG``
更可靠，实时信号或系统保留号尤其不能靠硬编码清单判断。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.signal.Signals
# polyglot-covers: python.signal.Handlers
# polyglot-covers: python.signal.Sigmasks
# polyglot-covers: python.signal.SIG_DFL
# polyglot-covers: python.signal.SIG_IGN
# polyglot-covers: python.signal.SIG_BLOCK
# polyglot-covers: python.signal.SIG_UNBLOCK
# polyglot-covers: python.signal.SIG_SETMASK
# polyglot-covers: python.signal.NSIG
# polyglot-covers: python.signal.valid_signals
# polyglot-covers: python.signal.strsignal
# polyglot-covers: python.signal.platform-dependent-signal-set



import signal
import pytest
import queue
import threading
import os

def test_signal_related_constants_are_integer_compatible_enums():
    assert isinstance(signal.SIGINT, signal.Signals)
    assert signal.Signals(int(signal.SIGINT)) is signal.Signals.SIGINT
    assert isinstance(signal.SIG_DFL, signal.Handlers)
    assert isinstance(signal.SIG_IGN, signal.Handlers)
    assert {
        signal.SIG_BLOCK,
        signal.SIG_UNBLOCK,
        signal.SIG_SETMASK,
    } == set(signal.Sigmasks)

    # IntEnum 与 int 相等且可直接索引，但日志与 repr 会保留语义名称。
    handlers = {int(signal.SIGINT): "interrupt"}
    assert handlers[signal.SIGINT] == "interrupt"
    assert signal.SIGINT.name == "SIGINT"


def test_valid_signals_and_system_descriptions_are_discovered_at_runtime():
    available = signal.valid_signals()
    assert signal.SIGINT in available
    assert signal.SIGTERM in available
    assert all(isinstance(signum, int) for signum in available)
    assert all(0 < int(signum) < signal.NSIG for signum in available)

    description = signal.strsignal(signal.SIGINT)
    # 描述由操作系统提供且可能本地化，所以只断言类型与非空，不比较英文文本。
    assert isinstance(description, str)
    assert description


def test_optional_signal_names_must_be_feature_detected():
    # Windows 有 SIGBREAK；Unix 常有 SIGUSR1。跨平台库应探测名称而非无条件导入。
    optional = {
        name: getattr(signal, name)
        for name in ("SIGBREAK", "SIGUSR1", "SIGWINCH")
        if hasattr(signal, name)
    }
    assert optional
    assert set(optional.values()) <= signal.valid_signals()


# 349｜安装、查询、恢复处理器以及 raise_signal。
#
# signal.signal 返回旧处理器，getsignal 返回当前处理器。Python 模拟 BSD 语义：自定义处理器执行后
# 仍保持安装（SIGCHLD 的具体行为依平台）；临时修改全局处理器必须放在 try/finally 中恢复。
# 处理器接收信号号与当时主线程的栈帧，不能把它写成无参数回调。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.signal
# polyglot-covers: python.signal.signal-returns-previous-handler
# polyglot-covers: python.signal.getsignal
# polyglot-covers: python.signal.python-handler-two-arguments
# polyglot-covers: python.signal.python-handler-frame
# polyglot-covers: python.signal.handler-remains-installed
# polyglot-covers: python.signal.raise_signal
# polyglot-covers: python.signal.SIG_IGN-behavior
# polyglot-covers: python.signal.restore-global-handler-workflow




_section_349_pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1"),
    reason="案例使用 Unix 用户自定义信号，避免改变 SIGINT/SIGTERM 语义",
)


@_section_349_pytestmark
def test_custom_handler_receives_signum_and_frame_and_remains_installed():
    received = []

    def handler(signum, frame):
        received.append((signum, frame))

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        assert signal.signal(signal.SIGUSR1, handler) is previous
        assert signal.getsignal(signal.SIGUSR1) is handler

        assert signal.raise_signal(signal.SIGUSR1) is None
        signal.raise_signal(signal.SIGUSR1)
        assert [item[0] for item in received] == [signal.SIGUSR1, signal.SIGUSR1]
        assert all(item[1] is not None for item in received)
        assert signal.getsignal(signal.SIGUSR1) is handler
    finally:
        signal.signal(signal.SIGUSR1, previous)


@_section_349_pytestmark
def test_ignore_action_discards_the_signal_and_signal_returns_custom_handler():
    called = []

    def handler(signum, frame):
        called.append(signum)

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, handler)
        assert signal.signal(signal.SIGUSR1, signal.SIG_IGN) is handler
        signal.raise_signal(signal.SIGUSR1)
        assert called == []
        assert signal.getsignal(signal.SIGUSR1) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGUSR1, previous)


# 350｜信号处理器的主线程约束与跨线程投递。
#
# 只有主解释器的主线程可以安装处理器或 wakeup fd。信号即使由 worker 线程触发，Python 回调也在
# 主线程运行；因此 signal 不是线程间通信机制，worker 间协调应使用 Event、Queue 等同步原语。
# pthread_kill 的 signalnum=0 只校验线程标识，不实际投递信号。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.only-main-thread-installs-handler
# polyglot-covers: python.signal.signal-worker-thread-valueerror
# polyglot-covers: python.signal.only-main-thread-sets-wakeup-fd
# polyglot-covers: python.signal.set-wakeup-fd-worker-thread-valueerror
# polyglot-covers: python.signal.handler-runs-in-main-thread
# polyglot-covers: python.signal.signal-not-thread-communication
# polyglot-covers: python.signal.pthread_kill
# polyglot-covers: python.signal.pthread-kill-zero-validation
# polyglot-covers: python.signal.raise-signal-from-worker




_section_350_pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1") or not hasattr(signal, "pthread_kill"),
    reason="线程信号 API 只在支持 pthread 的 Unix 平台提供",
)


@_section_350_pytestmark
def test_worker_cannot_install_a_handler_or_change_the_wakeup_fd():
    results = queue.Queue()

    def worker():
        for operation in (
            lambda: signal.signal(signal.SIGUSR1, signal.SIG_IGN),
            lambda: signal.set_wakeup_fd(-1),
        ):
            try:
                operation()
            except Exception as error:  # noqa: BLE001 - 案例需要把线程异常交回主线程
                results.put(error)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    errors = [results.get_nowait(), results.get_nowait()]
    assert all(isinstance(error, ValueError) for error in errors)


@_section_350_pytestmark
def test_signal_raised_by_worker_still_dispatches_handler_in_main_thread():
    main_ident = threading.get_ident()
    handled_in = []

    def handler(signum, frame):
        handled_in.append(threading.get_ident())

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, handler)
        thread = threading.Thread(target=signal.raise_signal, args=(signal.SIGUSR1,))
        thread.start()
        thread.join()
        assert handled_in == [main_ident]
    finally:
        signal.signal(signal.SIGUSR1, previous)


@_section_350_pytestmark
def test_pthread_kill_zero_checks_the_current_thread_without_delivery():
    assert signal.pthread_kill(threading.get_ident(), 0) is None


# 351｜pthread signal mask、pending 集合与同步 sigwait。
#
# 阻塞信号不会丢弃它，而是让它进入当前线程的 pending 集合。sigwait 可同步消费其中一个信号，且
# 不会调用该信号的 Python handler；这比异步回调更适合专用信号线程。mask 是线程局部状态，测试和
# 库代码都必须保存旧集合并用 SIG_SETMASK 恢复。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.pthread_sigmask
# polyglot-covers: python.signal.pthread-sigmask-returns-old-mask
# polyglot-covers: python.signal.pthread-sigmask-empty-query
# polyglot-covers: python.signal.blocked-signal-becomes-pending
# polyglot-covers: python.signal.sigpending
# polyglot-covers: python.signal.sigwait
# polyglot-covers: python.signal.sigwait-consumes-pending
# polyglot-covers: python.signal.sigwait-bypasses-handler
# polyglot-covers: python.signal.thread-mask-save-restore-workflow
# polyglot-covers: python.signal.sigkill-sigstop-cannot-be-blocked




REQUIRED_351 = ("pthread_sigmask", "sigpending", "sigwait", "SIGUSR1")
_section_351_pytestmark = pytest.mark.skipif(
    any(not hasattr(signal, name) for name in REQUIRED_351),
    reason="POSIX pthread signal mask API 在此平台不可用",
)


@_section_351_pytestmark
def test_blocked_signal_is_pending_until_sigwait_consumes_it_without_handler():
    handled = []
    previous_handler = signal.getsignal(signal.SIGUSR1)
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.signal(signal.SIGUSR1, lambda signum, frame: handled.append(signum))
        returned_old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1})
        assert returned_old == previous_mask
        assert signal.SIGUSR1 in signal.pthread_sigmask(signal.SIG_BLOCK, [])

        signal.raise_signal(signal.SIGUSR1)
        assert signal.SIGUSR1 in signal.sigpending()
        assert handled == []

        accepted = signal.sigwait({signal.SIGUSR1})
        assert accepted == signal.SIGUSR1
        assert signal.SIGUSR1 not in signal.sigpending()
        assert handled == []
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        signal.signal(signal.SIGUSR1, previous_handler)


@_section_351_pytestmark
def test_sigkill_and_sigstop_are_silently_excluded_from_a_requested_mask():
    if not hasattr(signal, "SIGKILL") or not hasattr(signal, "SIGSTOP"):
        pytest.skip("平台没有 POSIX 的不可阻塞信号")

    previous = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGKILL, signal.SIGSTOP})
        current = signal.pthread_sigmask(signal.SIG_BLOCK, [])
        assert signal.SIGKILL not in current
        assert signal.SIGSTOP not in current
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


# 352｜sigwaitinfo 的发送者元数据与 sigtimedwait 的零超时轮询。
#
# sigwaitinfo 与 sigtimedwait 同步接收已阻塞信号并返回 siginfo_t 视图；前者等待，后者可用
# timeout=0 只检查当前 pending 集合。要先 block 再产生信号，否则默认动作或异步 handler 可能先
# 执行，这是采用同步信号模型时最关键的顺序。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.sigwaitinfo
# polyglot-covers: python.signal.sigwaitinfo.si_signo
# polyglot-covers: python.signal.sigwaitinfo.si_pid
# polyglot-covers: python.signal.sigwaitinfo.si_uid
# polyglot-covers: python.signal.sigwaitinfo.si_code
# polyglot-covers: python.signal.sigtimedwait
# polyglot-covers: python.signal.sigtimedwait-timeout-zero-poll
# polyglot-covers: python.signal.sigtimedwait-timeout-none-result
# polyglot-covers: python.signal.block-before-synchronous-wait-workflow




REQUIRED_352 = ("pthread_sigmask", "sigwaitinfo", "sigtimedwait", "SIGUSR2")
_section_352_pytestmark = pytest.mark.skipif(
    any(not hasattr(signal, name) for name in REQUIRED_352),
    reason="POSIX siginfo 同步等待 API 在此平台不可用",
)


@_section_352_pytestmark
def test_pending_signal_produces_sender_information_and_is_consumed():
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR2})
        signal.raise_signal(signal.SIGUSR2)

        info = signal.sigwaitinfo({signal.SIGUSR2})
        assert info.si_signo == signal.SIGUSR2
        assert info.si_pid == os.getpid()
        assert info.si_uid == os.getuid()
        assert isinstance(info.si_code, int)

        # 第一次 wait 已消费 pending 信号，零超时不会等待未来事件。
        assert signal.sigtimedwait({signal.SIGUSR2}, 0) is None
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


@_section_352_pytestmark
def test_timed_wait_with_zero_timeout_still_consumes_an_already_pending_signal():
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    try:
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR2})
        signal.raise_signal(signal.SIGUSR2)
        info = signal.sigtimedwait({signal.SIGUSR2}, 0)
        assert info is not None
        assert info.si_signo == signal.SIGUSR2
        assert signal.sigtimedwait({signal.SIGUSR2}, 0) is None
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


# 353｜set_wakeup_fd 把异步信号桥接到 I/O 事件循环。
#
# 收到信号时，运行时向非阻塞 wakeup fd 写入一个值为信号号低 8 位的字节，使 select/selector
# 立即醒来；Python handler 仍按正常规则在主线程执行。应用必须主动排空 fd，并根据用途决定缓冲区
# 满时是否警告。set_wakeup_fd 返回旧 fd，因此嵌入式库要保存并恢复它。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.set_wakeup_fd
# polyglot-covers: python.signal.set-wakeup-fd-returns-old-fd
# polyglot-covers: python.signal.set-wakeup-fd-minus-one-disables
# polyglot-covers: python.signal.wakeup-fd-must-be-nonblocking
# polyglot-covers: python.signal.wakeup-fd-writes-signum-byte
# polyglot-covers: python.signal.wakeup-fd-must-be-drained
# polyglot-covers: python.signal.wakeup-fd-warn-on-full-buffer
# polyglot-covers: python.signal.wakeup-fd-save-restore-workflow




_section_353_pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1"),
    reason="案例使用 Unix 用户自定义信号，避免干扰进程控制信号",
)


@_section_353_pytestmark
def test_signal_writes_one_byte_to_a_nonblocking_wakeup_pipe():
    read_fd, write_fd = os.pipe()
    os.set_blocking(read_fd, False)
    os.set_blocking(write_fd, False)
    handled = []
    previous_handler = signal.getsignal(signal.SIGUSR1)
    previous_wakeup_fd = signal.set_wakeup_fd(-1)
    try:
        signal.signal(signal.SIGUSR1, lambda signum, frame: handled.append(signum))
        assert signal.set_wakeup_fd(write_fd, warn_on_full_buffer=False) == -1

        signal.raise_signal(signal.SIGUSR1)
        assert handled == [signal.SIGUSR1]
        assert os.read(read_fd, 1) == bytes([int(signal.SIGUSR1) & 0xFF])
        with pytest.raises(BlockingIOError):
            os.read(read_fd, 1)

        assert signal.set_wakeup_fd(-1) == write_fd
    finally:
        signal.set_wakeup_fd(previous_wakeup_fd)
        signal.signal(signal.SIGUSR1, previous_handler)
        os.close(read_fd)
        os.close(write_fd)


@_section_353_pytestmark
def test_blocking_descriptor_is_rejected_before_it_can_be_installed():
    read_fd, write_fd = os.pipe()
    previous_wakeup_fd = signal.set_wakeup_fd(-1)
    try:
        assert os.get_blocking(write_fd) is True
        with pytest.raises(ValueError, match="non-blocking"):
            signal.set_wakeup_fd(write_fd, warn_on_full_buffer=True)
    finally:
        signal.set_wakeup_fd(previous_wakeup_fd)
        os.close(read_fd)
        os.close(write_fd)


# 354｜alarm 与 setitimer 的调度、取消和旧值恢复。
#
# alarm 只有整数秒且同一进程只有一个；再次调用会替换旧闹钟并返回其剩余整秒数。setitimer 支持
# 浮点延时、重复 interval 和三种计时来源，返回 ``(delay, interval)`` 旧值。测试只安排远期计时器
# 并立即取消，不依赖真实等待；finally 恢复调用前的全局计时器。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.alarm
# polyglot-covers: python.signal.alarm-replaces-previous
# polyglot-covers: python.signal.alarm-zero-cancels
# polyglot-covers: python.signal.alarm-integer-seconds
# polyglot-covers: python.signal.setitimer
# polyglot-covers: python.signal.getitimer
# polyglot-covers: python.signal.setitimer-float-seconds
# polyglot-covers: python.signal.setitimer-repeat-interval
# polyglot-covers: python.signal.setitimer-zero-cancels
# polyglot-covers: python.signal.setitimer-returns-old-values
# polyglot-covers: python.signal.ItimerError
# polyglot-covers: python.signal.ITIMER_REAL
# polyglot-covers: python.signal.ITIMER_VIRTUAL
# polyglot-covers: python.signal.ITIMER_PROF




_section_354_pytestmark = pytest.mark.skipif(
    not hasattr(signal, "setitimer") or not hasattr(signal, "alarm"),
    reason="POSIX interval timer 在此平台不可用",
)


@_section_354_pytestmark
def test_alarm_replaces_one_process_wide_integer_timer_and_zero_cancels_it():
    previous_remaining = signal.alarm(0)
    try:
        assert signal.alarm(60) == 0
        remaining = signal.alarm(0)
        assert 1 <= remaining <= 60
        with pytest.raises(TypeError):
            signal.alarm(0.5)
    finally:
        if previous_remaining:
            signal.alarm(previous_remaining)


@_section_354_pytestmark
def test_interval_timer_exposes_float_delay_interval_and_previous_values():
    previous = signal.setitimer(signal.ITIMER_REAL, 0)
    try:
        assert signal.setitimer(signal.ITIMER_REAL, 60.5, 2.25) == (0.0, 0.0)
        delay, interval = signal.getitimer(signal.ITIMER_REAL)
        assert 0 < delay <= 60.5
        assert interval == pytest.approx(2.25)

        old_delay, old_interval = signal.setitimer(signal.ITIMER_REAL, 0)
        assert 0 < old_delay <= delay
        assert old_interval == pytest.approx(2.25)
        assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous)


@_section_354_pytestmark
def test_timer_kinds_and_invalid_kind_error_are_explicit():
    assert {
        signal.ITIMER_REAL,
        signal.ITIMER_VIRTUAL,
        signal.ITIMER_PROF,
    } == {0, 1, 2}
    with pytest.raises(signal.ItimerError):
        signal.getitimer(-1)
    assert issubclass(signal.ItimerError, OSError)


# 355｜处理器异常的主线程传播与 siginterrupt restart 模式。
#
# 底层 C handler 只设置标记；Python 回调稍后在主线程字节码边界执行。若回调抛异常，该异常会像
# “凭空”出现在主线程任意字节码处，可能打断尚未建立好的不变量。高可靠服务通常让 handler 只写
# wakeup fd/设置标志，而不直接抛异常。siginterrupt 控制被信号打断的系统调用是否自动重启。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.handler-exception-propagates-main-thread
# polyglot-covers: python.signal.handler-exception-bytecode-boundary-trap
# polyglot-covers: python.signal.siginterrupt
# polyglot-covers: python.signal.siginterrupt-false-restarts-syscalls
# polyglot-covers: python.signal.siginterrupt-true-interrupts-syscalls
# polyglot-covers: python.signal.installing-handler-resets-interrupt-mode




_section_355_pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGUSR1") or not hasattr(signal, "siginterrupt"),
    reason="siginterrupt 是 Unix API",
)


class HandlerRaised(RuntimeError):
    pass


@_section_355_pytestmark
def test_exception_raised_by_handler_propagates_from_raise_signal():
    def handler(signum, frame):
        raise HandlerRaised(signum)

    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, handler)
        with pytest.raises(HandlerRaised) as raised:
            signal.raise_signal(signal.SIGUSR1)
        assert raised.value.args == (signal.SIGUSR1,)
    finally:
        signal.signal(signal.SIGUSR1, previous)


@_section_355_pytestmark
def test_siginterrupt_switches_restart_policy_without_a_query_api():
    previous = signal.getsignal(signal.SIGUSR1)
    try:
        signal.signal(signal.SIGUSR1, lambda signum, frame: None)
        # signal() 隐式把该信号设成 interruptible；False 改为自动重启，True 再改回来。
        assert signal.siginterrupt(signal.SIGUSR1, False) is None
        assert signal.siginterrupt(signal.SIGUSR1, True) is None
    finally:
        # 重新安装旧 handler 也会重置 restart 策略；模块没有对应 getter 可保存该隐式状态。
        signal.signal(signal.SIGUSR1, previous)


# 356｜Python 的 SIGPIPE 策略与 BrokenPipeError。
#
# Python 默认忽略 SIGPIPE，让向无 reader 的 pipe/socket 写入以 BrokenPipeError 报告，调用者因此有
# 机会清理资源并决定退出码。不能为了消除异常把 SIGPIPE 改成 SIG_DFL：任何断开的网络连接都可能
# 直接终止整个进程。本例显式安装 SIG_IGN，避免依赖测试进程启动时的外部配置。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.SIGPIPE
# polyglot-covers: python.signal.python-ignores-sigpipe-policy
# polyglot-covers: python.signal.broken-pipe-error-instead-of-process-exit
# polyglot-covers: python.signal.sigpipe-default-action-trap




_section_356_pytestmark = pytest.mark.skipif(
    not hasattr(signal, "SIGPIPE"),
    reason="SIGPIPE 是 POSIX 信号",
)


@_section_356_pytestmark
def test_ignored_sigpipe_turns_a_write_to_a_closed_pipe_into_an_exception():
    read_fd, write_fd = os.pipe()
    previous = signal.getsignal(signal.SIGPIPE)
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        os.close(read_fd)
        read_fd = -1
        with pytest.raises(BrokenPipeError):
            os.write(write_fd, b"cannot be delivered")
        assert signal.getsignal(signal.SIGPIPE) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGPIPE, previous)
        if read_fd >= 0:
            os.close(read_fd)
        os.close(write_fd)


# 357｜Linux pidfd_send_signal 使用稳定的进程引用。
#
# 传统 pid 可能在目标退出后被系统复用；pidfd 是指向某个进程实例的文件描述符，配合
# pidfd_send_signal 可避免“检查后再发送”期间命中另一个进程。signal=0 只做目标与权限校验，不
# 实际投递信号，适合安全展示该接口；siginfo 在 Python 3.10 必须为 None，flags 必须为 0。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.signal.pidfd_send_signal
# polyglot-covers: python.signal.pidfd-process-identity
# polyglot-covers: python.signal.pidfd-send-signal-zero-validation
# polyglot-covers: python.signal.pidfd-send-signal-siginfo-none
# polyglot-covers: python.signal.pidfd-send-signal-flags-zero




_section_357_pytestmark = pytest.mark.skipif(
    not hasattr(signal, "pidfd_send_signal") or not hasattr(os, "pidfd_open"),
    reason="pidfd 需要 Linux 5.1+ 与对应 Python 构建支持",
)


@_section_357_pytestmark
def test_pidfd_signal_zero_validates_this_process_without_delivering_a_signal():
    pidfd = os.pidfd_open(os.getpid())
    try:
        assert os.get_inheritable(pidfd) is False
        assert signal.pidfd_send_signal(pidfd, 0, None, 0) is None

        with pytest.raises(TypeError):
            signal.pidfd_send_signal(pidfd, 0, object(), 0)
        with pytest.raises(OSError):
            signal.pidfd_send_signal(pidfd, 0, None, 1)
    finally:
        os.close(pidfd)
