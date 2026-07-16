"""096｜``StreamReader`` buffer、EOF、精确读取和 separator limit。

read(n>0) 有至少一个 byte 即可返回，并不保证填满；readexactly 才要求指定长度。
readuntil 成功时包含 separator，超过 limit 时数据仍留在 buffer；EOF 前数据不足则用
IncompleteReadError.partial 暴露残片。案例直接 feed protocol 数据以消除真实 I/O 时序。

这些案例面向 Python 3.10 当前补丁系列。
"""

# polyglot-covers: python.asyncio.StreamReader
# polyglot-covers: python.asyncio.StreamReader.read
# polyglot-covers: python.asyncio.StreamReader.read-zero
# polyglot-covers: python.asyncio.StreamReader.read-until-eof
# polyglot-covers: python.asyncio.StreamReader.readline
# polyglot-covers: python.asyncio.StreamReader.readline-partial-eof
# polyglot-covers: python.asyncio.StreamReader.readexactly
# polyglot-covers: python.asyncio.StreamReader.readuntil
# polyglot-covers: python.asyncio.StreamReader.at_eof
# polyglot-covers: python.asyncio.StreamReader-async-iteration
# polyglot-covers: python.asyncio.StreamReader-limit
# polyglot-covers: python.asyncio.IncompleteReadError
# polyglot-covers: python.asyncio.IncompleteReadError.partial
# polyglot-covers: python.asyncio.IncompleteReadError.expected
# polyglot-covers: python.asyncio.LimitOverrunError
# polyglot-covers: python.asyncio.LimitOverrunError.consumed
# polyglot-covers: python.asyncio.readuntil-limit-data-retained
# polyglot-covers: python.asyncio.readuntil-eof-buffer-reset




import asyncio
import pytest
import socket
import os
import sys
import shlex
import signal

def test_read_readline_and_eof_consume_buffer_with_distinct_guarantees():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"abcdef\nlast")

        assert await reader.read(0) == b""
        assert await reader.read(3) == b"abc"
        assert await reader.readline() == b"def\n"
        assert reader.at_eof() is False

        reader.feed_eof()
        assert await reader.readline() == b"last"
        assert await reader.read() == b""
        assert reader.at_eof() is True

    asyncio.run(scenario())


def test_readexactly_reports_partial_bytes_and_expected_count_at_eof():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"abc")
        reader.feed_eof()

        with pytest.raises(asyncio.IncompleteReadError) as raised:
            await reader.readexactly(5)

        assert isinstance(raised.value, EOFError)
        assert raised.value.partial == b"abc"
        assert raised.value.expected == 5
        assert reader.at_eof() is True

    asyncio.run(scenario())


def test_readuntil_limit_error_retains_data_for_a_different_recovery_read():
    async def scenario():
        reader = asyncio.StreamReader(limit=4)
        reader.feed_data(b"abcdef\nrest")
        reader.feed_eof()

        with pytest.raises(asyncio.LimitOverrunError) as raised:
            await reader.readuntil(b"\n")
        assert raised.value.consumed == 6

        # LimitOverrunError 不消费 buffer；caller 可丢弃 consumed bytes 或改用 read。
        assert await reader.read(7) == b"abcdef\n"
        assert await reader.read() == b"rest"

    asyncio.run(scenario())


def test_readuntil_eof_reports_partial_separator_and_resets_buffer():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"header\r")
        reader.feed_eof()

        with pytest.raises(asyncio.IncompleteReadError) as raised:
            await reader.readuntil(b"\r\n")
        assert raised.value.partial == b"header\r"
        assert raised.value.expected is None
        assert await reader.read() == b""

    asyncio.run(scenario())


def test_stream_reader_async_iteration_yields_lines_until_eof():
    async def scenario():
        reader = asyncio.StreamReader()
        reader.feed_data(b"first\nsecond\npartial")
        reader.feed_eof()

        return [line async for line in reader]

    assert asyncio.run(scenario()) == [b"first\n", b"second\n", b"partial"]


# ``open_connection(sock=...)``、StreamWriter flow control 与 half-close。
#
# 传入 sock 会把 ownership 转交给 StreamWriter；caller 只能关闭 writer，不能再独立管理该
# socket。write/writelines 只写入 transport buffer，drain 才实施 high/low watermark backpressure。
# close 后应 await wait_closed。案例只使用 socketpair，不访问网络或固定机器端口。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.open_connection
# polyglot-covers: python.asyncio.open-connection-sock
# polyglot-covers: python.asyncio.open-connection-socket-ownership
# polyglot-covers: python.asyncio.open-connection-limit
# polyglot-covers: python.asyncio.StreamWriter
# polyglot-covers: python.asyncio.StreamWriter.write
# polyglot-covers: python.asyncio.StreamWriter.writelines
# polyglot-covers: python.asyncio.StreamWriter.drain
# polyglot-covers: python.asyncio.StreamWriter.transport
# polyglot-covers: python.asyncio.StreamWriter.get_extra_info
# polyglot-covers: python.asyncio.StreamWriter.can_write_eof
# polyglot-covers: python.asyncio.StreamWriter.write_eof
# polyglot-covers: python.asyncio.StreamWriter.close
# polyglot-covers: python.asyncio.StreamWriter.is_closing
# polyglot-covers: python.asyncio.StreamWriter.wait_closed



async def _receive_exactly(loop, sock, amount):
    chunks = []
    remaining = amount
    while remaining:
        chunk = await loop.sock_recv(sock, remaining)
        if not chunk:
            raise EOFError("socket closed before requested bytes arrived")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def test_stream_writer_round_trip_half_close_and_socket_ownership():
    async def scenario():
        stream_socket, peer_socket = socket.socketpair()
        peer_socket.setblocking(False)
        writer = None
        try:
            reader, writer = await asyncio.open_connection(
                sock=stream_socket,
                limit=32,
            )
            loop = asyncio.get_running_loop()

            assert isinstance(reader, asyncio.StreamReader)
            assert isinstance(writer, asyncio.StreamWriter)
            assert writer.transport is not None
            assert writer.get_extra_info("socket") is not None
            assert writer.get_extra_info("missing", "fallback") == "fallback"

            writer.write(b"one|")
            writer.writelines([b"two|", b"three"])
            await writer.drain()
            assert await _receive_exactly(loop, peer_socket, 13) == b"one|two|three"

            await loop.sock_sendall(peer_socket, b"reply")
            assert await reader.readexactly(5) == b"reply"

            assert writer.can_write_eof() is True
            writer.write_eof()
            await writer.drain()
            assert await loop.sock_recv(peer_socket, 1) == b""

            writer.close()
            assert writer.is_closing() is True
            await writer.wait_closed()
            # sock ownership 已转移；writer close 使原对象也变成 closed descriptor。
            assert stream_socket.fileno() == -1
        finally:
            if writer is not None and not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            peer_socket.close()

    asyncio.run(scenario())


# 临时 Unix socket 的 ``start_unix_server/open_unix_connection`` workflow。
#
# stream server 为每个连接把 client callback 调度为 Task，并交付 reader/writer。start_serving
# 可把 bind/listen 与开始 accept 分开；Server async context 退出时 close 并 wait_closed。
# Unix socket path 使用 pytest 临时目录，无公网、固定端口或持久机器状态。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.start_unix_server
# polyglot-covers: python.asyncio.open_unix_connection
# polyglot-covers: python.asyncio.unix-stream-path-like
# polyglot-covers: python.asyncio.stream-server-coroutine-callback-task
# polyglot-covers: python.asyncio.stream-server-limit
# polyglot-covers: python.asyncio.Server.start_serving
# polyglot-covers: python.asyncio.Server.is_serving
# polyglot-covers: python.asyncio.Server.sockets
# polyglot-covers: python.asyncio.Server-async-context-manager
# polyglot-covers: python.asyncio.Server.close
# polyglot-covers: python.asyncio.Server.wait_closed




_section_281_pytestmark = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="案例使用临时 Unix-domain stream socket",
)


@_section_281_pytestmark
def test_unix_stream_server_echoes_lines_and_context_closes_listener(tmp_path):
    socket_path = tmp_path / "asyncio-echo.sock"

    async def scenario():
        handled = asyncio.Event()
        handler_tasks = []

        async def handle(reader, writer):
            handler_tasks.append(asyncio.current_task())
            try:
                request = await reader.readline()
                writer.write(b"echo:" + request)
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
                handled.set()

        server = await asyncio.start_unix_server(
            handle,
            path=socket_path,
            limit=128,
            start_serving=False,
        )
        assert server.is_serving() is False
        assert len(server.sockets) == 1
        assert os.fspath(server.sockets[0].getsockname()) == os.fspath(socket_path)

        async with server:
            await server.start_serving()
            assert server.is_serving() is True

            reader, writer = await asyncio.open_unix_connection(path=socket_path)
            writer.write(b"request\n")
            await writer.drain()
            assert await reader.readline() == b"echo:request\n"
            writer.close()
            await writer.wait_closed()
            await asyncio.wait_for(handled.wait(), timeout=2)

        assert server.is_serving() is False
        await server.wait_closed()
        assert len(handler_tasks) == 1
        assert isinstance(handler_tasks[0], asyncio.Task)

    asyncio.run(scenario())


# asyncio Lock fairness、async context 与 Event level-triggered broadcast。
#
# Lock 只协调同一 event loop 的 Task，不是 OS-thread lock；排队 acquire 按先到先得公平唤醒。
# async with 保证异常路径 release。Event 是可重复读取的 level flag：set 唤醒全部当前 waiter，
# 后来 wait 也立即成功，直到 clear。原语本身没有 timeout 参数，应外包 wait_for。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.Lock
# polyglot-covers: python.asyncio.Lock.acquire
# polyglot-covers: python.asyncio.Lock.release
# polyglot-covers: python.asyncio.Lock.locked
# polyglot-covers: python.asyncio.Lock-fifo-fairness
# polyglot-covers: python.asyncio.Lock-async-context-manager
# polyglot-covers: python.asyncio.Lock-unlocked-release-error
# polyglot-covers: python.asyncio.Event
# polyglot-covers: python.asyncio.Event.wait
# polyglot-covers: python.asyncio.Event.set
# polyglot-covers: python.asyncio.Event.clear
# polyglot-covers: python.asyncio.Event.is_set
# polyglot-covers: python.asyncio.Event-wake-all
# polyglot-covers: python.asyncio.Event-level-triggered
# polyglot-covers: python.asyncio.sync-primitives-no-timeout-parameter
# polyglot-covers: python.asyncio.sync-primitives-not-thread-safe




def test_lock_waiters_acquire_in_arrival_order_and_context_releases():
    async def scenario():
        lock = asyncio.Lock()
        assert await lock.acquire() is True
        assert lock.locked() is True
        arrived = [asyncio.Event(), asyncio.Event()]
        order = []

        async def waiter(index):
            arrived[index].set()
            async with lock:
                order.append(index)

        tasks = [asyncio.create_task(waiter(index)) for index in range(2)]
        await asyncio.gather(*(event.wait() for event in arrived))
        lock.release()
        await asyncio.gather(*tasks)

        assert order == [0, 1]
        assert lock.locked() is False

        with pytest.raises(LookupError):
            async with lock:
                raise LookupError("body failed")
        assert lock.locked() is False
        with pytest.raises(RuntimeError, match="Lock is not acquired"):
            lock.release()

    asyncio.run(scenario())

def test_event_set_wakes_all_and_stays_set_until_clear():
    async def scenario():
        event = asyncio.Event()
        entered = [asyncio.Event(), asyncio.Event()]

        async def waiter(index):
            entered[index].set()
            return await event.wait()

        tasks = [asyncio.create_task(waiter(index)) for index in range(2)]
        await asyncio.gather(*(marker.wait() for marker in entered))
        assert event.is_set() is False

        event.set()
        assert await asyncio.gather(*tasks) == [True, True]
        assert await event.wait() is True
        event.clear()
        assert event.is_set() is False

        pending = asyncio.create_task(event.wait())
        done, _ = await asyncio.wait({pending}, timeout=0)
        assert done == set()
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)

    asyncio.run(scenario())


def test_sync_primitive_methods_reject_direct_timeout_keyword():
    async def scenario():
        lock = asyncio.Lock()
        event = asyncio.Event()

        with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
            lock.acquire(timeout=1)
        with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
            event.wait(timeout=1)

    asyncio.run(scenario())


# asyncio Condition 的共享 Lock、predicate loop 与 notification ownership。
#
# Condition 把 Event-style 通知与 Lock-style exclusive state access 合并。wait 会原子释放底层
# lock，唤醒后再 acquire 才返回；因此状态检查必须在 lock 内用 wait_for predicate 循环。
# notify/notify_all 只唤醒 waiter，不释放 lock，而且未持锁调用会抛 RuntimeError。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.Condition
# polyglot-covers: python.asyncio.Condition-shared-lock
# polyglot-covers: python.asyncio.Condition.acquire
# polyglot-covers: python.asyncio.Condition.release
# polyglot-covers: python.asyncio.Condition.locked
# polyglot-covers: python.asyncio.Condition.wait
# polyglot-covers: python.asyncio.Condition.wait_for
# polyglot-covers: python.asyncio.Condition.notify
# polyglot-covers: python.asyncio.Condition.notify_all
# polyglot-covers: python.asyncio.Condition-wait-releases-reacquires
# polyglot-covers: python.asyncio.Condition-predicate-final-value
# polyglot-covers: python.asyncio.Condition-notify-does-not-release
# polyglot-covers: python.asyncio.Condition-lock-required




def test_wait_for_releases_then_reacquires_shared_lock_and_returns_predicate_value():
    async def scenario():
        lock = asyncio.Lock()
        condition = asyncio.Condition(lock)
        sibling_condition = asyncio.Condition(lock)
        waiter_ready = asyncio.Event()
        state = {"value": ""}

        async def waiter():
            async with condition:
                waiter_ready.set()
                result = await condition.wait_for(lambda: state["value"])
                assert condition.locked() is True
                assert sibling_condition.locked() is True
                return result

        task = asyncio.create_task(waiter())
        await waiter_ready.wait()
        # waiter 只有进入 condition.wait 并释放 lock 后，producer 才能获得同一把 lock。
        async with condition:
            state["value"] = "ready"
            condition.notify(1)
            assert task.done() is False

        assert await task == "ready"

    asyncio.run(scenario())

def test_notify_all_wakes_every_waiter_after_notifier_releases_lock():
    async def scenario():
        condition = asyncio.Condition()
        all_waiting = asyncio.Event()
        ready_count = 0
        resumed = []

        async def waiter(label):
            nonlocal ready_count
            async with condition:
                ready_count += 1
                if ready_count == 2:
                    all_waiting.set()
                assert await condition.wait() is True
                resumed.append(label)

        tasks = [asyncio.create_task(waiter(label)) for label in ("a", "b")]
        await all_waiting.wait()
        async with condition:
            condition.notify_all()
            assert resumed == []

        await asyncio.gather(*tasks)
        assert sorted(resumed) == ["a", "b"]

    asyncio.run(scenario())


def test_wait_and_notify_require_condition_lock_ownership():
    async def scenario():
        condition = asyncio.Condition()

        with pytest.raises(RuntimeError, match="cannot notify on un-acquired lock"):
            condition.notify()
        with pytest.raises(RuntimeError, match="cannot wait on un-acquired lock"):
            await condition.wait()
        with pytest.raises(RuntimeError, match="Lock is not acquired"):
            condition.release()

    asyncio.run(scenario())


# asyncio Semaphore capacity、async context 与 BoundedSemaphore invariant。
#
# Semaphore counter 为零时 acquire suspend，release 可超过初始容量；BoundedSemaphore 则把
# over-release 当作配对错误。locked 表示当前不能立即 acquire，并不授予未来执行保证。
# 案例用 Event gate 同时占满两个 permit，不依靠 wall-clock delay 判断并发上限。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.Semaphore
# polyglot-covers: python.asyncio.Semaphore.acquire
# polyglot-covers: python.asyncio.Semaphore.release
# polyglot-covers: python.asyncio.Semaphore.locked
# polyglot-covers: python.asyncio.Semaphore-negative-initial-error
# polyglot-covers: python.asyncio.Semaphore-over-release-allowed
# polyglot-covers: python.asyncio.Semaphore-async-context-manager
# polyglot-covers: python.asyncio.Semaphore-concurrency-limit
# polyglot-covers: python.asyncio.BoundedSemaphore
# polyglot-covers: python.asyncio.BoundedSemaphore-over-release




def test_semaphore_limits_simultaneous_sections_without_real_time_waits():
    async def scenario():
        semaphore = asyncio.Semaphore(2)
        started = [asyncio.Event() for _ in range(3)]
        two_inside = asyncio.Event()
        release = asyncio.Event()
        active = 0
        maximum = 0

        async def worker(index):
            nonlocal active, maximum
            started[index].set()
            async with semaphore:
                active += 1
                maximum = max(maximum, active)
                if active == 2:
                    two_inside.set()
                await release.wait()
                active -= 1

        tasks = [asyncio.create_task(worker(index)) for index in range(3)]
        await asyncio.gather(*(event.wait() for event in started))
        await two_inside.wait()
        assert semaphore.locked() is True
        assert active == 2

        release.set()
        await asyncio.gather(*tasks)
        assert maximum == 2
        assert active == 0
        assert semaphore.locked() is False

    asyncio.run(scenario())


def test_plain_semaphore_allows_extra_release_but_bounded_variant_rejects_it():
    async def scenario():
        semaphore = asyncio.Semaphore(0)
        assert semaphore.locked() is True
        semaphore.release()
        semaphore.release()
        assert await semaphore.acquire() is True
        assert await semaphore.acquire() is True
        assert semaphore.locked() is True

        bounded = asyncio.BoundedSemaphore(1)
        assert await bounded.acquire() is True
        bounded.release()
        with pytest.raises(ValueError, match="BoundedSemaphore released too many times"):
            bounded.release()

    asyncio.run(scenario())


def test_negative_initial_semaphore_value_is_rejected():
    with pytest.raises(ValueError, match="Semaphore initial value must be >= 0"):
        asyncio.Semaphore(-1)


# ``create_subprocess_exec``、Process streams、communicate 与 async wait。
#
# asyncio Process 类似 Popen，但没有 poll，wait/communicate 是 coroutine 且不接受 timeout；
# 需要用 wait_for 包装。PIPE 对 stdin 生成 StreamWriter，对 stdout/stderr 生成 StreamReader。
# 使用 PIPE 时 communicate 会并发排空，避免先 wait 造成 pipe capacity deadlock。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.create_subprocess_exec
# polyglot-covers: python.asyncio.subprocess.Process
# polyglot-covers: python.asyncio.subprocess.Process.pid
# polyglot-covers: python.asyncio.subprocess.Process.returncode
# polyglot-covers: python.asyncio.subprocess.Process.stdin
# polyglot-covers: python.asyncio.subprocess.Process.stdout
# polyglot-covers: python.asyncio.subprocess.Process.stderr
# polyglot-covers: python.asyncio.subprocess.Process.wait
# polyglot-covers: python.asyncio.subprocess.Process.communicate
# polyglot-covers: python.asyncio.subprocess.Process-no-poll
# polyglot-covers: python.asyncio.subprocess.Process-no-timeout-parameter
# polyglot-covers: python.asyncio.subprocess.PIPE
# polyglot-covers: python.asyncio.subprocess.STDOUT
# polyglot-covers: python.asyncio.subprocess.DEVNULL
# polyglot-covers: python.asyncio.subprocess.communicate-drains-pipes
# polyglot-covers: python.asyncio.subprocess.communicate-memory-buffering




def test_exec_process_communicate_maps_pipe_stream_types_and_attributes():
    async def scenario():
        source = (
            "import sys; data = sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(data[::-1]); "
            "sys.stderr.write(str(len(data)))"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            source,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=32,
        )

        assert process.pid > 0
        assert process.returncode is None
        assert isinstance(process.stdin, asyncio.StreamWriter)
        assert isinstance(process.stdout, asyncio.StreamReader)
        assert isinstance(process.stderr, asyncio.StreamReader)
        assert hasattr(process, "poll") is False

        stdout, stderr = await process.communicate(b"abcdef")
        assert stdout == b"fedcba"
        assert stderr == b"6"
        assert process.returncode == 0

    asyncio.run(scenario())

def test_stdout_merge_and_devnull_use_same_constants_as_sync_subprocess():
    async def scenario():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import os; os.write(1, b'out|'); os.write(2, b'err')",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, stderr = await process.communicate()

        assert stdout == b"out|err"
        assert stderr is None
        assert process.stdin is None

    asyncio.run(scenario())


def test_process_wait_uses_outer_wait_for_and_can_be_retried_after_timeout():
    async def scenario():
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import sys; sys.stdin.buffer.read()",
            stdin=asyncio.subprocess.PIPE,
        )
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=0)
            assert process.returncode is None

            with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
                process.wait(timeout=1)

            process.stdin.close()
            assert await process.wait() == 0
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

    asyncio.run(scenario())


def test_communicate_drains_two_outputs_larger_than_typical_pipe_capacity():
    async def scenario():
        amount = 100_000
        source = (
            f"import os; os.write(1, b'o' * {amount}); "
            f"os.write(2, b'e' * {amount})"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            source,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        assert process.returncode == 0
        assert stdout == b"o" * amount
        assert stderr == b"e" * amount

    asyncio.run(scenario())


# asyncio shell quoting 与 POSIX Process signal control。
#
# create_subprocess_shell 明确启用 shell，调用者必须用 shlex.quote 保护不可信字符串；exec
# 形式更适合普通 argv。Process 的 send_signal/terminate/kill 是同步发请求，随后 await wait
# 观察退出。POSIX 信号退出码仍为负 signal number。child 以 Event 阻塞，不使用 sleep。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.create_subprocess_shell
# polyglot-covers: python.asyncio.subprocess-shell-quoting
# polyglot-covers: python.asyncio.subprocess-shell-injection-responsibility
# polyglot-covers: python.asyncio.subprocess.Process.send_signal
# polyglot-covers: python.asyncio.subprocess.Process.terminate
# polyglot-covers: python.asyncio.subprocess.Process.kill
# polyglot-covers: python.asyncio.subprocess-signal-negative-returncode




_section_286_pytestmark = pytest.mark.skipif(os.name != "posix", reason="案例使用 POSIX shell 与 signal")


async def _blocking_process():
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "import sys, threading; print('ready', flush=True); threading.Event().wait()",
        stdout=asyncio.subprocess.PIPE,
    )
    line = await asyncio.wait_for(process.stdout.readline(), timeout=2)
    if line != b"ready\n":
        process.kill()
        await process.wait()
        raise AssertionError(f"invalid child readiness record: {line!r}")
    return process


@_section_286_pytestmark
def test_shell_command_uses_explicit_quoting_for_data_with_metacharacters():
    async def scenario():
        value = "literal; $(not-executed)"
        command = f"printf '%s' {shlex.quote(value)}"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        assert process.returncode == 0
        assert stdout.decode() == value
        assert stderr == b""

    asyncio.run(scenario())

@_section_286_pytestmark
def test_send_signal_terminate_and_kill_set_negative_posix_returncodes():
    async def scenario():
        signalled = await _blocking_process()
        signalled.send_signal(signal.SIGTERM)
        assert await signalled.wait() == -signal.SIGTERM

        terminated = await _blocking_process()
        terminated.terminate()
        assert await terminated.wait() == -signal.SIGTERM

        killed = await _blocking_process()
        killed.kill()
        assert await killed.wait() == -signal.SIGKILL

    asyncio.run(scenario())


# asyncio Queue/LifoQueue/PriorityQueue、精确 size 与 bounded backpressure。
#
# asyncio Queue 仅服务同一 event loop，因此 qsize 是精确值；bounded put 在满时 suspend，get
# 释放一个 slot。get/put 自身没有 timeout 参数，应用应以 wait_for 包装。nowait 版本用
# QueueEmpty/QueueFull 表达不能立即完成，三种 Queue 仅改变 retrieval order。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.Queue
# polyglot-covers: python.asyncio.Queue.maxsize
# polyglot-covers: python.asyncio.Queue.qsize
# polyglot-covers: python.asyncio.Queue.empty
# polyglot-covers: python.asyncio.Queue.full
# polyglot-covers: python.asyncio.Queue.put
# polyglot-covers: python.asyncio.Queue.put_nowait
# polyglot-covers: python.asyncio.Queue.get
# polyglot-covers: python.asyncio.Queue.get_nowait
# polyglot-covers: python.asyncio.QueueFull
# polyglot-covers: python.asyncio.QueueEmpty
# polyglot-covers: python.asyncio.Queue-bounded-backpressure
# polyglot-covers: python.asyncio.Queue-exact-size
# polyglot-covers: python.asyncio.Queue-no-timeout-parameter
# polyglot-covers: python.asyncio.Queue-wait-for-timeout
# polyglot-covers: python.asyncio.PriorityQueue
# polyglot-covers: python.asyncio.LifoQueue




async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_queue_variants_retrieve_fifo_lifo_and_lowest_priority_first():
    async def scenario():
        fifo = asyncio.Queue()
        lifo = asyncio.LifoQueue()
        priority = asyncio.PriorityQueue()
        for container in (fifo, lifo):
            container.put_nowait("first")
            await container.put("second")
        priority.put_nowait((20, "later"))
        await priority.put((10, "earlier"))

        assert [fifo.get_nowait(), fifo.get_nowait()] == ["first", "second"]
        assert [lifo.get_nowait(), lifo.get_nowait()] == ["second", "first"]
        assert [priority.get_nowait(), priority.get_nowait()] == [
            (10, "earlier"),
            (20, "later"),
        ]

    asyncio.run(scenario())

def test_bounded_put_suspends_until_get_releases_capacity():
    async def scenario():
        work = asyncio.Queue(maxsize=1)
        assert work.maxsize == 1
        await work.put("first")
        assert work.qsize() == 1
        assert work.full() is True

        blocked_put = asyncio.create_task(work.put("second"))
        await _next_loop_turn()
        assert blocked_put.done() is False
        with pytest.raises(asyncio.QueueFull):
            work.put_nowait("third")

        assert await work.get() == "first"
        await blocked_put
        assert work.qsize() == 1
        assert work.get_nowait() == "second"
        assert work.empty() is True
        with pytest.raises(asyncio.QueueEmpty):
            work.get_nowait()

    asyncio.run(scenario())


def test_queue_timeout_is_composed_with_wait_for_not_a_method_keyword():
    async def scenario():
        work = asyncio.Queue()
        with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
            work.get(timeout=1)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(work.get(), timeout=0)

        work.put_nowait("still usable")
        assert await work.get() == "still usable"

    asyncio.run(scenario())


# asyncio Queue ``task_done/join`` 与 cancellable worker workflow。
#
# get 让 Queue 变空并不等于 work 已处理；每个 put 增加 unfinished count，每个 consumer 必须
# 恰好一次 task_done。join 只等计数归零。长驻 worker 常在 queue.join 后 cancel，并用 gather
# 回收取消异常；task_done 应置于 finally，防止业务异常把 join 永久卡住。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.asyncio.Queue.task_done
# polyglot-covers: python.asyncio.Queue.join
# polyglot-covers: python.asyncio.Queue-unfinished-task-counter
# polyglot-covers: python.asyncio.Queue-get-does-not-finish-task
# polyglot-covers: python.asyncio.Queue-join-processing-not-emptiness
# polyglot-covers: python.asyncio.Queue-task-done-exactly-once
# polyglot-covers: python.asyncio.Queue-task-done-overcall
# polyglot-covers: python.asyncio.Queue-worker-task-done-finally
# polyglot-covers: python.asyncio.Queue-cancel-workers-after-join




async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_workers_acknowledge_each_item_then_are_cancelled_after_join():
    async def scenario():
        work = asyncio.Queue()
        processed = []

        async def worker():
            while True:
                item = await work.get()
                try:
                    processed.append(item * item)
                finally:
                    work.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(2)]
        for item in (2, 3, 4):
            work.put_nowait(item)

        await work.join()
        for task in workers:
            task.cancel()
        results = await asyncio.gather(*workers, return_exceptions=True)

        assert sorted(processed) == [4, 9, 16]
        assert all(isinstance(result, asyncio.CancelledError) for result in results)

    asyncio.run(scenario())

def test_join_waits_for_task_done_even_after_item_has_been_removed():
    async def scenario():
        work = asyncio.Queue()
        work.put_nowait("retrieved")
        assert work.get_nowait() == "retrieved"
        assert work.empty() is True

        joined = asyncio.create_task(work.join())
        await _next_loop_turn()
        assert joined.done() is False

        work.task_done()
        await joined
        with pytest.raises(ValueError, match=r"task_done\(\) called too many times"):
            work.task_done()

    asyncio.run(scenario())
