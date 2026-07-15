"""097｜手工 event loop 的获取、run/stop、关闭与 batch boundary。

应用入口优先 asyncio.run；framework 才常手工 new/set/run/close。get_running_loop 只在 coroutine
或 callback 内有效。run_until_complete 会把 coroutine 包成 Task。run_forever 遇 stop 时完成
当前 callback batch，但 batch 内新排入的 callback 留到下一次 run。close 不可逆但可重复调用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.get_running_loop
# polyglot-covers: python.asyncio.get-running-loop-outside-error
# polyglot-covers: python.asyncio.get_event_loop
# polyglot-covers: python.asyncio.set_event_loop
# polyglot-covers: python.asyncio.new_event_loop
# polyglot-covers: python.asyncio.loop.run_until_complete
# polyglot-covers: python.asyncio.run-until-complete-wraps-coroutine
# polyglot-covers: python.asyncio.loop.run_forever
# polyglot-covers: python.asyncio.loop.stop
# polyglot-covers: python.asyncio.loop.is_running
# polyglot-covers: python.asyncio.loop.is_closed
# polyglot-covers: python.asyncio.loop.close
# polyglot-covers: python.asyncio.loop-close-idempotent-irreversible
# polyglot-covers: python.asyncio.run-forever-current-batch-boundary




import asyncio
import pytest
import contextvars
from functools import partial
import os
import socket
import signal
import selectors

def test_new_set_and_run_until_complete_bind_the_running_loop():
    with pytest.raises(RuntimeError, match="no running event loop"):
        asyncio.get_running_loop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def main():
        assert asyncio.get_running_loop() is loop
        assert asyncio.get_event_loop() is loop
        assert loop.is_running() is True
        return asyncio.current_task()

    try:
        task = loop.run_until_complete(main())
        assert isinstance(task, asyncio.Task)
        assert loop.is_running() is False
        assert loop.is_closed() is False
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    assert loop.is_closed() is True


def test_stop_finishes_current_callback_batch_and_defers_new_callbacks():
    loop = asyncio.new_event_loop()
    calls = []

    def first_callback():
        calls.append("first")
        loop.call_soon(calls.append, "next batch")
        loop.stop()

    try:
        loop.call_soon(first_callback)
        loop.run_forever()
        assert calls == ["first"]

        loop.call_soon(loop.stop)
        loop.run_forever()
        assert calls == ["first", "next batch"]
    finally:
        loop.close()


def test_close_discards_pending_callbacks_and_is_idempotent_but_irreversible():
    loop = asyncio.new_event_loop()
    calls = []
    loop.call_soon(calls.append, "must not run")

    loop.close()
    assert calls == []
    assert loop.is_closed() is True
    assert loop.close() is None

    with pytest.raises(RuntimeError, match="Event loop is closed"):
        loop.call_soon(calls.append, "too late")


# ``call_soon/call_later/call_at``、Handle cancellation 与 callback Context。
#
# call_soon 以登记顺序在下一轮执行且 exactly once；Handle.cancel 只能阻止尚未执行的 callback。
# delayed callback 使用 loop monotonic time，返回 TimerHandle；同一绝对时刻的相对顺序未定义。
# callback 默认复制当前 Context，也可显式传 context。keyword args 应用 functools.partial 绑定。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.call_soon
# polyglot-covers: python.asyncio.call-soon-registration-order
# polyglot-covers: python.asyncio.call-soon-exactly-once
# polyglot-covers: python.asyncio.Handle
# polyglot-covers: python.asyncio.Handle.cancel
# polyglot-covers: python.asyncio.Handle.cancelled
# polyglot-covers: python.asyncio.callback-context-copy
# polyglot-covers: python.asyncio.callback-explicit-context
# polyglot-covers: python.asyncio.callback-keywords-via-partial
# polyglot-covers: python.asyncio.loop.call_later
# polyglot-covers: python.asyncio.loop.call_at
# polyglot-covers: python.asyncio.loop.time
# polyglot-covers: python.asyncio.TimerHandle
# polyglot-covers: python.asyncio.TimerHandle.when
# polyglot-covers: python.asyncio.equal-time-callback-order-undefined



CALLBACK_VALUE = contextvars.ContextVar("asyncio_callback_value", default="missing")


def test_call_soon_preserves_order_cancels_handle_and_uses_selected_context():
    loop = asyncio.new_event_loop()
    calls = []

    def record(label, *, suffix=""):
        calls.append((label + suffix, CALLBACK_VALUE.get()))

    copied_token = CALLBACK_VALUE.set("copied-at-schedule")
    try:
        first = loop.call_soon(record, "first")
        cancelled = loop.call_soon(record, "cancelled")
        cancelled.cancel()

        explicit = contextvars.Context()
        explicit.run(CALLBACK_VALUE.set, "explicit")
        loop.call_soon(
            partial(record, "with", suffix=" keywords"),
            context=explicit,
        )
        CALLBACK_VALUE.set("changed-after-schedule")
        loop.call_soon(loop.stop)
        loop.run_forever()
    finally:
        CALLBACK_VALUE.reset(copied_token)
        loop.close()
    assert isinstance(first, asyncio.Handle)
    assert first.cancelled() is False
    assert cancelled.cancelled() is True
    assert calls == [
        ("first", "copied-at-schedule"),
        ("with keywords", "explicit"),
    ]


def test_zero_delay_and_current_time_timers_run_without_wall_clock_wait():
    loop = asyncio.new_event_loop()
    calls = []
    try:
        now = loop.time()
        later = loop.call_later(0, calls.append, "relative")
        absolute = loop.call_at(now, calls.append, "absolute")
        cancelled = loop.call_at(now, calls.append, "cancelled")
        cancelled.cancel()
        loop.call_later(0, loop.stop)

        loop.run_forever()

        assert isinstance(later, asyncio.TimerHandle)
        assert isinstance(absolute, asyncio.TimerHandle)
        assert later.when() >= now
        assert absolute.when() == now
        # 两个 deadline 相同或已经到期；规范不承诺它们之间的执行顺序。
        assert sorted(calls) == ["absolute", "relative"]
        assert cancelled.cancelled() is True
    finally:
        loop.close()


# event loop 直接监听文件描述符的可读、可写事件。
#
# add_reader/add_writer 属于 SelectorEventLoop 的低层能力，适合整合已有 fd；普通应用优先
# Streams。注册同一 fd 会替换旧 callback，remove_* 的 bool 能区分“确实移除”和“本来没有”。
# callback 必须主动读取或移除监听，否则 level-triggered fd 会持续就绪并反复触发。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.add_reader
# polyglot-covers: python.asyncio.loop.remove_reader
# polyglot-covers: python.asyncio.add-reader-callback-args
# polyglot-covers: python.asyncio.add-reader-replaces-existing-callback
# polyglot-covers: python.asyncio.reader-callback-must-consume-or-remove
# polyglot-covers: python.asyncio.loop.add_writer
# polyglot-covers: python.asyncio.loop.remove_writer
# polyglot-covers: python.asyncio.remove-fd-watcher-return-value
# polyglot-covers: python.asyncio.fd-watchers-selector-loop



def test_reader_callback_consumes_the_fd_and_replacement_is_observable():
    async def scenario():
        loop = asyncio.get_running_loop()
        read_fd, write_fd = os.pipe()
        received = loop.create_future()
        stale_calls = []

        def stale_callback():
            stale_calls.append("不应执行")

        def consume(prefix):
            # fd 的“可读”只是 readiness 通知；数据仍需调用者自己读取。
            payload = os.read(read_fd, 64)
            assert loop.remove_reader(read_fd) is True
            received.set_result(prefix + payload)

        try:
            loop.add_reader(read_fd, stale_callback)
            loop.add_reader(read_fd, consume, b"prefix:")
            os.write(write_fd, b"ready")

            assert await received == b"prefix:ready"
            assert stale_calls == []
            assert loop.remove_reader(read_fd) is False
        finally:
            loop.remove_reader(read_fd)
            os.close(read_fd)
            os.close(write_fd)

    asyncio.run(scenario())


def test_writer_callback_fires_for_a_writable_socket_and_can_remove_itself():
    async def scenario():
        loop = asyncio.get_running_loop()
        left, right = socket.socketpair()
        writable = loop.create_future()

        def on_writable(label):
            assert loop.remove_writer(left.fileno()) is True
            writable.set_result(label)

        try:
            loop.add_writer(left.fileno(), on_writable, "socket is writable")
            assert await writable == "socket is writable"
            assert loop.remove_writer(left.fileno()) is False
        finally:
            loop.remove_writer(left.fileno())
            left.close()
            right.close()

    asyncio.run(scenario())


# event loop 直接操作非阻塞 stream socket。
#
# sock_recv/sock_recv_into/sock_sendall 是 socket 阻塞 API 的 coroutine 版本；传入的 socket
# 必须先设为 non-blocking。sendall 成功只返回 None，失败时也无法得知对端实际处理了多少字节。
# 直接 socket API 较直观，但大量连接通常由 Transport/Protocol 或 Streams 更高效地管理。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.sock_recv
# polyglot-covers: python.asyncio.sock-recv-up-to-nbytes
# polyglot-covers: python.asyncio.loop.sock_recv_into
# polyglot-covers: python.asyncio.sock-recv-into-buffer-count
# polyglot-covers: python.asyncio.loop.sock_sendall
# polyglot-covers: python.asyncio.sock-sendall-none-on-success
# polyglot-covers: python.asyncio.direct-socket-must-be-nonblocking
# polyglot-covers: python.asyncio.direct-socketpair-local-workflow



def test_sock_sendall_and_recv_exchange_bytes_without_a_transport():
    async def scenario():
        loop = asyncio.get_running_loop()
        left, right = socket.socketpair()
        left.setblocking(False)
        right.setblocking(False)
        try:
            result = await loop.sock_sendall(left, b"abcdef")
            first = await loop.sock_recv(right, 3)
            second = await loop.sock_recv(right, 16)

            assert result is None
            # recv 最多返回 nbytes，并不承诺凑满；socketpair 中这两次读取按边界切开。
            assert first == b"abc"
            assert second == b"def"
        finally:
            left.close()
            right.close()

    asyncio.run(scenario())


def test_sock_recv_into_mutates_a_writable_buffer_and_returns_count():
    async def scenario():
        loop = asyncio.get_running_loop()
        left, right = socket.socketpair()
        left.setblocking(False)
        right.setblocking(False)
        buffer = bytearray(b"........")
        try:
            await loop.sock_sendall(left, b"data")
            count = await loop.sock_recv_into(right, memoryview(buffer)[2:6])

            assert count == 4
            assert buffer == bytearray(b"..data..")
        finally:
            left.close()
            right.close()

    asyncio.run(scenario())


# 用 event loop 在 Unix socket 上直接 connect 与 accept。
#
# sock_connect/sock_accept 要求 non-blocking socket。accept 返回全新的连接 socket，监听 socket
# 仍归调用者。这里使用 pytest 临时目录中的 AF_UNIX 地址，不占用端口，也不依赖 DNS 或外部网络。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.sock_connect
# polyglot-covers: python.asyncio.sock-connect-nonblocking
# polyglot-covers: python.asyncio.loop.sock_accept
# polyglot-covers: python.asyncio.sock-accept-connection-address-pair
# polyglot-covers: python.asyncio.sock-accept-new-socket-ownership
# polyglot-covers: python.asyncio.direct-unix-socket-no-external-network



def test_sock_connect_and_accept_create_two_independently_owned_endpoints(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        path = tmp_path / "direct.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.setblocking(False)
        client.setblocking(False)
        listener.bind(str(path))
        listener.listen(1)
        accepted = None

        try:
            accept_task = asyncio.create_task(loop.sock_accept(listener))
            assert await loop.sock_connect(client, str(path)) is None
            accepted, peer_address = await accept_task
            accepted.setblocking(False)

            # 未命名的 AF_UNIX client 通常给出空 peer address；其类型由平台表示决定，
            # 教学重点是返回二元组和新的 socket，而不是把该表示写死。
            assert isinstance(accepted, socket.socket)
            assert peer_address in ("", None)
            assert accepted.fileno() != listener.fileno()

            await loop.sock_sendall(client, b"hello")
            assert await loop.sock_recv(accepted, 16) == b"hello"
        finally:
            if accepted is not None:
                accepted.close()
            client.close()
            listener.close()

    asyncio.run(scenario())


# loop.sock_sendfile 的零拷贝优先文件传输。
#
# sock_sendfile 尝试 os.sendfile，平台不支持时默认退回普通读取发送；file 必须是二进制模式的
# regular file，socket 必须是 non-blocking SOCK_STREAM。返回实际发送字节数，并更新文件位置。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.sock_sendfile
# polyglot-covers: python.asyncio.sock-sendfile-stream-socket
# polyglot-covers: python.asyncio.sock-sendfile-binary-regular-file
# polyglot-covers: python.asyncio.sock-sendfile-offset-count
# polyglot-covers: python.asyncio.sock-sendfile-return-count
# polyglot-covers: python.asyncio.sock-sendfile-updates-file-position
# polyglot-covers: python.asyncio.sock-sendfile-fallback-default



def test_sock_sendfile_honors_offset_and_count_and_advances_the_file(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        source = tmp_path / "payload.bin"
        source.write_bytes(b"0123456789")
        left, right = socket.socketpair()
        left.setblocking(False)
        right.setblocking(False)
        try:
            with source.open("rb") as file:
                sent = await loop.sock_sendfile(left, file, offset=2, count=4)
                received = await loop.sock_recv(right, 16)

                assert sent == 4
                assert received == b"2345"
                assert file.tell() == 6
        finally:
            left.close()
            right.close()

    asyncio.run(scenario())


# event loop 的异步 getaddrinfo/getnameinfo 桥接。
#
# 这两个 coroutine 对应 socket 模块的同步名称解析函数，event loop 通常把可能阻塞的解析工作
# 放入 executor。案例强制 numeric host/service，只验证地址结构转换，不查询 DNS，也不访问网络。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.getaddrinfo
# polyglot-covers: python.asyncio.getaddrinfo-coroutine
# polyglot-covers: python.asyncio.getaddrinfo-family-type-proto-address-tuples
# polyglot-covers: python.asyncio.getaddrinfo-numeric-no-dns
# polyglot-covers: python.asyncio.loop.getnameinfo
# polyglot-covers: python.asyncio.getnameinfo-coroutine
# polyglot-covers: python.asyncio.getnameinfo-numeric-no-dns



def test_numeric_address_and_name_resolution_are_async_and_network_free():
    async def scenario():
        loop = asyncio.get_running_loop()
        addresses = await loop.getaddrinfo(
            "127.0.0.1",
            "80",
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            flags=socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
        )

        assert addresses
        for family, sock_type, protocol, canonical_name, address in addresses:
            assert family == socket.AF_INET
            assert sock_type == socket.SOCK_STREAM
            assert isinstance(protocol, int)
            assert canonical_name == ""
            assert address == ("127.0.0.1", 80)

        host, service = await loop.getnameinfo(
            ("127.0.0.1", 80),
            socket.NI_NUMERICHOST | socket.NI_NUMERICSERV,
        )
        assert (host, service) == ("127.0.0.1", "80")

    asyncio.run(scenario())


# event loop 安装 Unix signal callback。
#
# add_signal_handler 的 callback 由 loop 像普通 callback 一样调度，因此可以安全地操作 Future；
# 它比 signal.signal 的最小异步信号处理函数更易组合。注册必须在主线程完成。remove 返回 bool，
# 案例始终恢复原 handler，避免向其他测试泄漏进程级状态。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.add_signal_handler
# polyglot-covers: python.asyncio.signal-handler-loop-scheduled-callback
# polyglot-covers: python.asyncio.signal-handler-callback-args
# polyglot-covers: python.asyncio.signal-handler-main-thread-only
# polyglot-covers: python.asyncio.loop.remove_signal_handler
# polyglot-covers: python.asyncio.remove-signal-handler-return-value
# polyglot-covers: python.asyncio.signal-handler-process-state-restoration



def test_signal_handler_can_resolve_a_future_and_is_then_removed():
    async def scenario():
        loop = asyncio.get_running_loop()
        previous = signal.getsignal(signal.SIGUSR1)
        received = loop.create_future()

        try:
            loop.add_signal_handler(
                signal.SIGUSR1,
                received.set_result,
                "SIGUSR1 received",
            )
            os.kill(os.getpid(), signal.SIGUSR1)
            assert await received == "SIGUSR1 received"
            assert loop.remove_signal_handler(signal.SIGUSR1) is True
            assert loop.remove_signal_handler(signal.SIGUSR1) is False
        finally:
            loop.remove_signal_handler(signal.SIGUSR1)
            signal.signal(signal.SIGUSR1, previous)

    asyncio.run(scenario())


# process-wide event loop policy、per-thread current loop 与 Unix child watcher。
#
# Policy 决定 get/set/new_event_loop 的行为；对象本身全进程共享，但默认 current loop 按线程隔离。
# 自定义实现宜继承 DefaultEventLoopPolicy，仅覆写需要改变的方法。Unix child watcher 负责把子进程
# 退出转成 loop callback；不同 watcher 在线程、signal 干扰、复杂度和平台支持之间取舍。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.get_event_loop_policy
# polyglot-covers: python.asyncio.set_event_loop_policy
# polyglot-covers: python.asyncio.AbstractEventLoopPolicy
# polyglot-covers: python.asyncio.DefaultEventLoopPolicy
# polyglot-covers: python.asyncio.policy-process-wide-object
# polyglot-covers: python.asyncio.policy-current-loop-per-thread-default
# polyglot-covers: python.asyncio.policy.get_event_loop
# polyglot-covers: python.asyncio.policy.set_event_loop
# polyglot-covers: python.asyncio.policy.new_event_loop
# polyglot-covers: python.asyncio.custom-policy-subclass-default
# polyglot-covers: python.asyncio.SelectorEventLoop
# polyglot-covers: python.asyncio.selector-event-loop-custom-selector
# polyglot-covers: python.asyncio.AbstractChildWatcher
# polyglot-covers: python.asyncio.get_child_watcher
# polyglot-covers: python.asyncio.ThreadedChildWatcher
# polyglot-covers: python.asyncio.MultiLoopChildWatcher
# polyglot-covers: python.asyncio.SafeChildWatcher
# polyglot-covers: python.asyncio.FastChildWatcher
# polyglot-covers: python.asyncio.PidfdChildWatcher
# polyglot-covers: python.asyncio.child-watcher-strategy-tradeoffs



class CountingSelectorPolicy(asyncio.DefaultEventLoopPolicy):
    def __init__(self):
        super().__init__()
        self.created = 0

    def new_event_loop(self):
        self.created += 1
        # 显式 selector 的写法适合需要可预测 selector 实现的框架或诊断环境。
        return asyncio.SelectorEventLoop(selectors.SelectSelector())


def test_custom_policy_controls_loop_creation_and_current_loop_lookup():
    previous_policy = asyncio.get_event_loop_policy()
    policy = CountingSelectorPolicy()
    loop = None
    try:
        asyncio.set_event_loop_policy(policy)
        assert asyncio.get_event_loop_policy() is policy
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        assert policy.created == 1
        assert asyncio.get_event_loop() is loop
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        asyncio.set_event_loop(None)
        if loop is not None:
            loop.close()
        asyncio.set_event_loop_policy(previous_policy)


def test_default_unix_child_watcher_implements_the_abstract_contract():
    watcher = asyncio.get_child_watcher()
    assert isinstance(watcher, asyncio.AbstractChildWatcher)
    assert watcher.is_active() is True

    # 这些都是 Python 3.10 提供的策略类；不实际替换全局 watcher，以免干扰其他测试。
    implementations = [
        asyncio.ThreadedChildWatcher,
        asyncio.MultiLoopChildWatcher,
        asyncio.SafeChildWatcher,
        asyncio.FastChildWatcher,
        asyncio.PidfdChildWatcher,
    ]
    assert all(issubclass(item, asyncio.AbstractChildWatcher) for item in implementations)
