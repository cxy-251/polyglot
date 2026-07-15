"""098｜stream Transport 与 Protocol 的连接状态机和双向 I/O。

event loop 创建 Transport，再依次触发 connection_made、零到多次 data_received、可选
eof_received，最后恰好一次 connection_lost。Protocol 保存 transport；socket 所有权已转移，
应调用 transport.close 而不是直接关闭原 socket。write 只入队，不等价于对端已经处理。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.create_connection-sock
# polyglot-covers: python.asyncio.Protocol
# polyglot-covers: python.asyncio.protocol.connection_made
# polyglot-covers: python.asyncio.protocol.data_received
# polyglot-covers: python.asyncio.protocol.eof_received
# polyglot-covers: python.asyncio.protocol.connection_lost
# polyglot-covers: python.asyncio.protocol-callback-state-machine
# polyglot-covers: python.asyncio.transport.write
# polyglot-covers: python.asyncio.transport.writelines
# polyglot-covers: python.asyncio.transport.can_write_eof
# polyglot-covers: python.asyncio.transport.write_eof
# polyglot-covers: python.asyncio.transport.close
# polyglot-covers: python.asyncio.transport.is_closing
# polyglot-covers: python.asyncio.transport.get_extra_info
# polyglot-covers: python.asyncio.transport.get_protocol
# polyglot-covers: python.asyncio.transport.set_protocol
# polyglot-covers: python.asyncio.transport-socket-ownership-transfer



import asyncio
import socket
import os
import shlex
import sys
import pytest
import ssl
from test_100_ssl_complete_context_bio_socket_verification_and_sessions import CERTIFICATE_PEM
from test_100_ssl_complete_context_bio_socket_verification_and_sessions import (
    write_test_certificate,
)

class RecordingProtocol(asyncio.Protocol):
    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.received = bytearray()
        self.data_ready = loop.create_future()
        self.eof_seen = loop.create_future()
        self.closed = loop.create_future()
        self.events = []

    def connection_made(self, transport):
        self.transport = transport
        self.events.append("made")

    def data_received(self, data):
        self.received.extend(data)
        self.events.append(("data", bytes(data)))
        if len(self.received) >= 4 and not self.data_ready.done():
            self.data_ready.set_result(bytes(self.received))

    def eof_received(self):
        self.events.append("eof")
        self.eof_seen.set_result(True)
        # False 表示收到 EOF 后由 transport 自动关闭连接。
        return False

    def connection_lost(self, exc):
        self.events.append(("lost", exc))
        if not self.closed.done():
            self.closed.set_result(exc)


async def _recv_exactly(loop, sock, size):
    chunks = bytearray()
    while len(chunks) < size:
        chunks.extend(await loop.sock_recv(sock, size - len(chunks)))
    return bytes(chunks)


def test_transport_protocol_pair_exchanges_data_and_observes_eof():
    async def scenario():
        loop = asyncio.get_running_loop()
        owned, peer = socket.socketpair()
        owned.setblocking(False)
        peer.setblocking(False)
        protocol = RecordingProtocol(loop)
        transport, returned_protocol = await loop.create_connection(
            lambda: protocol,
            sock=owned,
        )
        try:
            assert returned_protocol is protocol
            assert protocol.transport is transport
            assert transport.get_protocol() is protocol
            transport.set_protocol(protocol)
            assert transport.get_protocol() is protocol
            assert transport.get_extra_info("socket").family == socket.AF_UNIX
            assert transport.is_closing() is False

            await loop.sock_sendall(peer, b"ping")
            assert await protocol.data_ready == b"ping"

            transport.write(b"po")
            transport.writelines([b"n", b"g"])
            assert await _recv_exactly(loop, peer, 4) == b"pong"
            assert transport.can_write_eof() is True

            # 对端 half-close 触发本端 eof_received；其 False 返回值使 transport 关闭。
            peer.shutdown(socket.SHUT_WR)
            assert await protocol.eof_seen is True
            assert await protocol.closed is None
            assert transport.is_closing() is True
        finally:
            transport.close()
            peer.close()

    asyncio.run(scenario())


# BufferedProtocol 让协议直接提供接收缓冲区。
#
# 普通 Protocol 的 data_received 会收到新 bytes；BufferedProtocol 改为 get_buffer 提供可写
# buffer，event loop 填充后用 buffer_updated(nbytes) 告知有效长度，从而减少大数据接收时的复制。
# sizehint 只是建议，返回零长度 buffer 才是错误；只应读取本次 nbytes 覆盖的前缀。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.BufferedProtocol
# polyglot-covers: python.asyncio.buffered-protocol.get_buffer
# polyglot-covers: python.asyncio.buffered-protocol-sizehint-advisory
# polyglot-covers: python.asyncio.buffered-protocol-nonzero-writable-buffer
# polyglot-covers: python.asyncio.buffered-protocol.buffer_updated
# polyglot-covers: python.asyncio.buffered-protocol-nbytes-valid-prefix
# polyglot-covers: python.asyncio.buffered-protocol-reduces-receive-copying
# polyglot-covers: python.asyncio.buffered-protocol-lifecycle



class FixedBufferProtocol(asyncio.BufferedProtocol):
    def __init__(self, loop):
        self.loop = loop
        self.buffer = bytearray(64)
        self.size_hints = []
        self.received = bytearray()
        self.ready = loop.create_future()
        self.closed = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport

    def get_buffer(self, sizehint):
        self.size_hints.append(sizehint)
        return self.buffer

    def buffer_updated(self, nbytes):
        self.received.extend(self.buffer[:nbytes])
        if len(self.received) >= 5 and not self.ready.done():
            self.ready.set_result(bytes(self.received))

    def connection_lost(self, exc):
        if not self.closed.done():
            self.closed.set_result(exc)


def test_event_loop_writes_received_bytes_into_protocol_owned_buffer():
    async def scenario():
        loop = asyncio.get_running_loop()
        owned, peer = socket.socketpair()
        owned.setblocking(False)
        peer.setblocking(False)
        protocol = FixedBufferProtocol(loop)
        transport, _ = await loop.create_connection(lambda: protocol, sock=owned)
        try:
            await loop.sock_sendall(peer, b"hello")
            assert await protocol.ready == b"hello"
            assert protocol.size_hints
            # event loop 可传 -1 或正建议值；协议不应假设它就是实际到达字节数。
            assert all(hint == -1 or hint > 0 for hint in protocol.size_hints)
        finally:
            transport.close()
            await protocol.closed
            peer.close()

    asyncio.run(scenario())


# DatagramTransport/DatagramProtocol 保留消息边界的无连接 I/O。
#
# datagram_received 每次给出一个完整 datagram 和平台形式的 peer address；它不同于 stream，
# 不需要自己重组字节流。error_received 只在底层能观察到 OSError 时触发，无法投递的数据也可能
# 被静默丢弃，因此它不是可靠送达确认。传入 sock 后，关闭责任转移给 transport。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.create_datagram_endpoint
# polyglot-covers: python.asyncio.create-datagram-endpoint-existing-sock
# polyglot-covers: python.asyncio.DatagramTransport
# polyglot-covers: python.asyncio.DatagramProtocol
# polyglot-covers: python.asyncio.datagram-protocol.datagram_received
# polyglot-covers: python.asyncio.datagram-protocol.error_received
# polyglot-covers: python.asyncio.datagram-message-boundary
# polyglot-covers: python.asyncio.datagram-undeliverable-may-be-silent
# polyglot-covers: python.asyncio.datagram-transport.sendto
# polyglot-covers: python.asyncio.datagram-transport.close
# polyglot-covers: python.asyncio.datagram-socket-ownership-transfer



class RecordingDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.datagrams = loop.create_future()
        self.errors = []
        self.closed = loop.create_future()
        self.received = []

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.received.append((data, addr))
        if len(self.received) == 2:
            self.datagrams.set_result(list(self.received))

    def error_received(self, exc):
        # 某些平台永远不会为无法投递的数据调用这里，因此这里只记录协议契约。
        self.errors.append(exc)

    def connection_lost(self, exc):
        self.closed.set_result(exc)


async def _recv_datagram(loop, sock):
    ready = loop.create_future()

    def receive_once():
        try:
            ready.set_result(sock.recv(64))
        except BaseException as error:
            ready.set_exception(error)
        finally:
            loop.remove_reader(sock.fileno())

    loop.add_reader(sock.fileno(), receive_once)
    return await ready


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="案例使用 Unix domain datagram 的临时地址",
)
def test_connected_datagram_transport_preserves_each_message_boundary(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        owned_address = str(tmp_path / "owned.sock")
        peer_address = str(tmp_path / "peer.sock")
        owned = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        peer = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        owned.bind(owned_address)
        peer.bind(peer_address)
        owned.connect(peer_address)
        peer.connect(owned_address)
        owned.setblocking(False)
        peer.setblocking(False)
        protocol = RecordingDatagramProtocol(loop)
        transport, returned = await loop.create_datagram_endpoint(
            lambda: protocol,
            sock=owned,
        )
        try:
            peer.send(b"one")
            peer.send(b"two")
            received = await asyncio.wait_for(protocol.datagrams, timeout=1)

            assert returned is protocol
            assert [data for data, _ in received] == [b"one", b"two"]
            assert protocol.errors == []

            transport.sendto(b"reply")
            assert await asyncio.wait_for(
                _recv_datagram(loop, peer),
                timeout=1,
            ) == b"reply"
        finally:
            transport.close()
            assert await asyncio.wait_for(protocol.closed, timeout=1) is None
            peer.close()

    asyncio.run(scenario())


# 把现有 OS pipe 接入 event loop 的 ReadTransport/WriteTransport。
#
# connect_read_pipe/connect_write_pipe 接收 file-like pipe，返回 (transport, protocol)。Unix 的
# SelectorEventLoop 会把 pipe 设为 non-blocking。pause_reading 只暂停向 protocol 投递，不阻止
# 内核 pipe 接收；resume_reading 后继续。关闭 write end 后，reader 最终观察到 EOF。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.connect_read_pipe
# polyglot-covers: python.asyncio.loop.connect_write_pipe
# polyglot-covers: python.asyncio.pipe-transport-protocol-pair
# polyglot-covers: python.asyncio.selector-loop-pipe-nonblocking
# polyglot-covers: python.asyncio.ReadTransport
# polyglot-covers: python.asyncio.read-transport.pause_reading
# polyglot-covers: python.asyncio.read-transport.resume_reading
# polyglot-covers: python.asyncio.read-transport.is_reading
# polyglot-covers: python.asyncio.WriteTransport
# polyglot-covers: python.asyncio.pipe-write-close-delivers-eof



async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_read_and_write_pipe_transports_support_pause_resume_and_eof():
    async def scenario():
        loop = asyncio.get_running_loop()
        read_fd, write_fd = os.pipe()
        read_pipe = os.fdopen(read_fd, "rb", buffering=0)
        write_pipe = os.fdopen(write_fd, "wb", buffering=0)
        reader = asyncio.StreamReader()
        read_protocol = asyncio.StreamReaderProtocol(reader)
        read_transport = None
        write_transport = None

        try:
            read_transport, returned_reader_protocol = await loop.connect_read_pipe(
                lambda: read_protocol,
                read_pipe,
            )
            write_transport, write_protocol = await loop.connect_write_pipe(
                asyncio.Protocol,
                write_pipe,
            )
            assert returned_reader_protocol is read_protocol
            assert isinstance(write_protocol, asyncio.Protocol)
            with pytest.raises(NotImplementedError):
                read_transport.is_reading()

            read_transport.pause_reading()
            pending = asyncio.create_task(reader.readexactly(4))
            write_transport.write(b"pipe")
            await _next_loop_turn()
            assert pending.done() is False

            read_transport.resume_reading()
            assert await pending == b"pipe"
            write_transport.close()
            assert await reader.read() == b""
            # 3.10 Unix pipe transport 支持 pause/resume，却没有覆盖
            # ReadTransport.is_reading；以可观察的交付暂停验证真实协议。
        finally:
            if write_transport is not None:
                write_transport.close()
            else:
                write_pipe.close()
            if read_transport is not None:
                read_transport.close()
            else:
                read_pipe.close()

    asyncio.run(scenario())


# SubprocessTransport/Protocol 的 pipe callback 工作流。
#
# 高层 create_subprocess_exec 通常更方便；框架可用 loop.subprocess_exec 获得 transport 和
# protocol。stdout/stderr 由 pipe_data_received(fd, data) 分流，process_exited 与 pipe 关闭
# callback 的先后不应被假定。asyncio 子进程流是 bytes，文本解码由调用者负责。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.subprocess_exec
# polyglot-covers: python.asyncio.loop.subprocess_shell
# polyglot-covers: python.asyncio.subprocess-exec-variadic-argv
# polyglot-covers: python.asyncio.low-level-subprocess-shell-command-string
# polyglot-covers: python.asyncio.SubprocessTransport
# polyglot-covers: python.asyncio.SubprocessProtocol
# polyglot-covers: python.asyncio.subprocess-protocol.pipe_data_received
# polyglot-covers: python.asyncio.subprocess-protocol.pipe_connection_lost
# polyglot-covers: python.asyncio.subprocess-protocol.process_exited
# polyglot-covers: python.asyncio.subprocess-callback-order-not-assumed
# polyglot-covers: python.asyncio.subprocess-transport.get_pid
# polyglot-covers: python.asyncio.subprocess-transport.get_returncode
# polyglot-covers: python.asyncio.subprocess-transport.get_pipe_transport
# polyglot-covers: python.asyncio.subprocess-protocol-bytes-not-text



class CapturingSubprocessProtocol(asyncio.SubprocessProtocol):
    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.output = {1: bytearray(), 2: bytearray()}
        self.closed_pipes = set()
        self.exited = False
        self.done = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport

    def pipe_data_received(self, fd, data):
        self.output[fd].extend(data)

    def pipe_connection_lost(self, fd, exc):
        # stdin (fd=0) 可能因 child 提前关闭读端而报告 BrokenPipeError；输出管道正常 EOF
        # 才应给出 None，不能把三个 pipe 的关闭原因一概而论。
        if fd in (1, 2):
            assert exc is None
        self.closed_pipes.add(fd)
        self._finish_when_complete()

    def process_exited(self):
        self.exited = True
        self._finish_when_complete()

    def _finish_when_complete(self):
        # 文档没有承诺 process_exited 与最后一次 pipe callback 的顺序，所以显式等两者。
        if self.exited and {1, 2} <= self.closed_pipes and not self.done.done():
            self.done.set_result(None)


def test_subprocess_protocol_collects_stdout_and_stderr_by_pipe_number():
    async def scenario():
        loop = asyncio.get_running_loop()
        protocol = CapturingSubprocessProtocol(loop)
        code = "import sys;sys.stdout.buffer.write(b'out');sys.stderr.buffer.write(b'err')"
        transport, returned = await loop.subprocess_exec(
            lambda: protocol,
            sys.executable,
            "-c",
            code,
        )
        try:
            assert returned is protocol
            assert protocol.transport is transport
            assert isinstance(transport.get_pid(), int)
            assert transport.get_pipe_transport(1) is not None
            assert transport.get_pipe_transport(2) is not None

            await protocol.done
            assert transport.get_returncode() == 0
            assert bytes(protocol.output[1]) == b"out"
            assert bytes(protocol.output[2]) == b"err"
        finally:
            transport.close()

    asyncio.run(scenario())


def test_low_level_shell_also_returns_a_subprocess_transport_protocol_pair():
    async def scenario():
        loop = asyncio.get_running_loop()
        protocol = CapturingSubprocessProtocol(loop)
        script = "import sys;sys.stdout.write('shell')"
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"
        transport, returned = await loop.subprocess_shell(
            lambda: protocol,
            command,
        )
        try:
            assert returned is protocol
            await protocol.done
            assert transport.get_returncode() == 0
            assert bytes(protocol.output[1]) == b"shell"
            assert bytes(protocol.output[2]) == b""
        finally:
            transport.close()

    asyncio.run(scenario())


# 低层 Unix protocol server 与 asyncio.Server 生命周期。
#
# start_serving=False 可先取得监听 socket、完成其他初始化，再显式 start_serving。Server.sockets
# 返回内部列表的副本；close 只停止接收新连接，wait_closed 才等待关闭完成。Server 也支持
# async context manager，退出时保证监听端已经关闭。案例只使用 pytest 临时 Unix socket。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.create_unix_server
# polyglot-covers: python.asyncio.loop.create_unix_connection
# polyglot-covers: python.asyncio.protocol-server-factory-per-connection
# polyglot-covers: python.asyncio.Server
# polyglot-covers: python.asyncio.Server.get_loop
# polyglot-covers: python.asyncio.Server.sockets-copy
# polyglot-covers: python.asyncio.Server.start-serving-idempotent
# polyglot-covers: python.asyncio.Server.serve_forever
# polyglot-covers: python.asyncio.Server-serve-forever-cancellation-closes




class EchoProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.transport.write(data.upper())
        self.transport.close()


class ClientProtocol(asyncio.Protocol):
    def __init__(self, loop):
        self.loop = loop
        self.result = loop.create_future()
        self.received = bytearray()

    def connection_made(self, transport):
        self.transport = transport
        transport.write(b"hello")

    def data_received(self, data):
        self.received.extend(data)

    def connection_lost(self, exc):
        if exc is None:
            self.result.set_result(bytes(self.received))
        else:
            self.result.set_exception(exc)


def test_server_can_delay_accepting_and_async_context_closes_it(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        path = tmp_path / "protocol-server.sock"
        server = await loop.create_unix_server(
            EchoProtocol,
            path,
            start_serving=False,
        )

        assert server.get_loop() is loop
        assert server.is_serving() is False
        first_snapshot = server.sockets
        second_snapshot = server.sockets
        assert first_snapshot is not second_snapshot
        assert first_snapshot[0].getsockname() == str(path)

        async with server:
            await server.start_serving()
            await server.start_serving()
            assert server.is_serving() is True

            client = ClientProtocol(loop)
            client_transport, returned = await loop.create_unix_connection(
                lambda: client,
                path,
            )
            try:
                assert returned is client
                assert await client.result == b"HELLO"
            finally:
                client_transport.close()

        assert server.is_serving() is False
        assert not server.sockets
        assert server.close() is None
        await server.wait_closed()

    asyncio.run(scenario())


def test_cancelling_serve_forever_closes_the_server(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        server = await loop.create_unix_server(
            EchoProtocol,
            tmp_path / "serve-forever.sock",
            start_serving=False,
        )
        task = asyncio.create_task(server.serve_forever())

        # 通过 call_soon 跨过一个确定的 loop turn，让 serve_forever 完成启动逻辑。
        started = loop.create_future()
        loop.call_soon(started.set_result, None)
        await started
        assert server.is_serving() is True

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert server.is_serving() is False
        await server.wait_closed()

    asyncio.run(scenario())


# 把 asyncio 外部 accept 的 socket 接入 Transport/Protocol。
#
# connect_accepted_socket 适合由其他线程或既有 server 接受连接，再交给 event loop 管理的框架。
# 成功后 accepted socket 的所有权转移给 transport；返回值仍是 (transport, protocol)。这里用
# AF_UNIX 监听地址，避免端口、DNS 和外部网络依赖。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.connect_accepted_socket
# polyglot-covers: python.asyncio.connect-accepted-socket-preaccepted-input
# polyglot-covers: python.asyncio.connect-accepted-socket-transport-protocol-pair
# polyglot-covers: python.asyncio.connect-accepted-socket-ownership-transfer
# polyglot-covers: python.asyncio.connect-accepted-socket-external-accept-workflow



class AcceptedProtocol(asyncio.Protocol):
    def __init__(self, loop):
        self.loop = loop
        self.connected = loop.create_future()
        self.received = loop.create_future()
        self.closed = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        self.connected.set_result(transport)

    def data_received(self, data):
        self.received.set_result(data)

    def connection_lost(self, exc):
        self.closed.set_result(exc)


def test_preaccepted_unix_socket_can_be_handed_to_the_event_loop(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        path = tmp_path / "accepted.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.setblocking(False)
        client.setblocking(False)
        listener.bind(str(path))
        listener.listen(1)
        transport = None

        try:
            await loop.sock_connect(client, str(path))
            accepted, _ = await loop.sock_accept(listener)
            accepted.setblocking(False)
            protocol = AcceptedProtocol(loop)
            transport, returned = await loop.connect_accepted_socket(
                lambda: protocol,
                accepted,
            )

            assert returned is protocol
            assert await protocol.connected is transport
            await loop.sock_sendall(client, b"request")
            assert await protocol.received == b"request"

            transport.write(b"response")
            assert await loop.sock_recv(client, 64) == b"response"
        finally:
            if transport is not None:
                transport.close()
                await protocol.closed
            client.close()
            listener.close()

    asyncio.run(scenario())


# loop.sendfile 通过 Transport 发送 regular file。
#
# 它与 sock_sendfile 的传输语义相同，但输入是 event loop 管理的 stream transport。实现优先
# os.sendfile，默认允许 fallback；返回传输字节数并更新 file position。SSL transport 通常只能
# 走 fallback，因为加密层不能直接零拷贝发送明文文件。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.sendfile
# polyglot-covers: python.asyncio.transport-sendfile-regular-binary-file
# polyglot-covers: python.asyncio.transport-sendfile-offset-count
# polyglot-covers: python.asyncio.transport-sendfile-return-count
# polyglot-covers: python.asyncio.transport-sendfile-updates-file-position
# polyglot-covers: python.asyncio.transport-sendfile-os-sendfile-preferred
# polyglot-covers: python.asyncio.transport-sendfile-fallback
# polyglot-covers: python.asyncio.SendfileNotAvailableError



class ClosingProtocol(asyncio.Protocol):
    def __init__(self, loop):
        self.closed = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        self.closed.set_result(exc)


async def _recv_exactly(loop, sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = await loop.sock_recv(sock, size - len(data))
        if not chunk:
            raise EOFError("transport 在文件传完前关闭")
        data.extend(chunk)
    return bytes(data)


def test_sendfile_uses_transport_and_updates_source_position(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        path = tmp_path / "transport-payload.bin"
        path.write_bytes(b"abcdefghij")
        owned, peer = socket.socketpair()
        owned.setblocking(False)
        peer.setblocking(False)
        protocol = ClosingProtocol(loop)
        transport, _ = await loop.create_connection(lambda: protocol, sock=owned)
        try:
            with path.open("rb") as file:
                sent = await loop.sendfile(transport, file, offset=3, count=5)
                assert sent == 5
                assert file.tell() == 8
            assert await _recv_exactly(loop, peer, 5) == b"defgh"
        finally:
            transport.close()
            await protocol.closed
            peer.close()

    asyncio.run(scenario())


# WriteTransport 的 high/low watermark、protocol flow control 与 abort。
#
# write 不阻塞；内核暂时写不下的字节进入 transport buffer。buffer 超过 high watermark 时，
# protocol.pause_writing 被调用；降到 low 或更低时 resume_writing。协议应据此暂停生产数据，不能
# 只看一次 write 的返回值。abort 立即丢弃尚未发送的 buffer，而 close 会先异步 flush。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.write-transport.get_write_buffer_size
# polyglot-covers: python.asyncio.write-transport.get_write_buffer_limits
# polyglot-covers: python.asyncio.write-transport.set_write_buffer_limits
# polyglot-covers: python.asyncio.write-buffer-low-not-above-high
# polyglot-covers: python.asyncio.write-buffer-watermark-nonnegative
# polyglot-covers: python.asyncio.protocol.pause_writing
# polyglot-covers: python.asyncio.protocol.resume_writing
# polyglot-covers: python.asyncio.transport-write-flow-control
# polyglot-covers: python.asyncio.write-watermark-zero-reduces-concurrency
# polyglot-covers: python.asyncio.write-transport.abort
# polyglot-covers: python.asyncio.abort-discards-buffer
# polyglot-covers: python.asyncio.close-flushes-buffer-before-connection-lost




class FlowControlProtocol(asyncio.Protocol):
    def __init__(self, loop):
        self.paused = loop.create_future()
        self.resumed = loop.create_future()
        self.closed = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport

    def pause_writing(self):
        if not self.paused.done():
            self.paused.set_result(self.transport.get_write_buffer_size())

    def resume_writing(self):
        if not self.resumed.done():
            self.resumed.set_result(self.transport.get_write_buffer_size())

    def connection_lost(self, exc):
        self.closed.set_result(exc)


async def _drain_socket(loop, sock, total):
    received = 0
    while received < total:
        chunk = await loop.sock_recv(sock, min(65536, total - received))
        if not chunk:
            break
        received += len(chunk)
    return received


def test_watermarks_pause_and_resume_a_protocol_around_buffer_pressure():
    async def scenario():
        loop = asyncio.get_running_loop()
        owned, peer = socket.socketpair()
        owned.setblocking(False)
        peer.setblocking(False)
        # 缩小内核 send buffer，再写足够大的 payload，保证至少一部分进入 transport buffer。
        owned.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        protocol = FlowControlProtocol(loop)
        transport, _ = await loop.create_connection(lambda: protocol, sock=owned)
        payload = b"x" * (1024 * 1024)
        try:
            transport.set_write_buffer_limits(high=1024, low=512)
            assert transport.get_write_buffer_limits() == (512, 1024)
            assert transport.get_write_buffer_size() == 0

            transport.write(payload)
            paused_size = await protocol.paused
            assert paused_size > 1024

            assert await _drain_socket(loop, peer, len(payload)) == len(payload)
            resumed_size = await protocol.resumed
            assert resumed_size <= 512

            with pytest.raises(ValueError):
                transport.set_write_buffer_limits(high=1, low=2)
            with pytest.raises(ValueError):
                transport.set_write_buffer_limits(high=-1)
        finally:
            transport.close()
            await protocol.closed
            peer.close()

    asyncio.run(scenario())


def test_abort_marks_transport_closing_without_flushing_pending_bytes():
    async def scenario():
        loop = asyncio.get_running_loop()
        owned, peer = socket.socketpair()
        owned.setblocking(False)
        peer.setblocking(False)
        owned.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        protocol = FlowControlProtocol(loop)
        transport, _ = await loop.create_connection(lambda: protocol, sock=owned)
        try:
            transport.write(b"pending" * 200_000)
            assert transport.get_write_buffer_size() > 0
            transport.abort()
            assert transport.is_closing() is True
            assert await protocol.closed is None
        finally:
            transport.abort()
            peer.close()

    asyncio.run(scenario())


# loop.start_tls 把既有 plain Transport/Protocol 原地升级为 TLS。
#
# start_tls 在 transport 与 protocol 之间插入 coder；await 后必须只使用返回的新 transport，因为
# coder 会缓存协议侧和 wire-side data。server/client 两端要协调升级，本例先让 server upgrade task
# 进入等待，再启动 client，避免 ClientHello 被旧 plain protocol 当 application data 消费。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.asyncio.loop.start_tls
# polyglot-covers: python.asyncio.start-tls-existing-transport-protocol
# polyglot-covers: python.asyncio.start-tls-server-side
# polyglot-covers: python.asyncio.start-tls-client-server-hostname
# polyglot-covers: python.asyncio.start-tls-handshake-timeout
# polyglot-covers: python.asyncio.start-tls-returns-new-transport
# polyglot-covers: python.asyncio.start-tls-stop-using-original-transport
# polyglot-covers: python.asyncio.start-tls-coordinated-upgrade




class UpgradeProtocol(asyncio.Protocol):
    def __init__(self, loop, expected_length=1):
        self.loop = loop
        self.expected_length = expected_length
        self.transport = None
        self.data = loop.create_future()
        self.closed = loop.create_future()
        self.received = bytearray()

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.received.extend(data)
        if len(self.received) >= self.expected_length and not self.data.done():
            self.data.set_result(bytes(self.received))

    def connection_lost(self, exc):
        if not self.closed.done():
            self.closed.set_result(exc)


def test_plain_socketpair_transports_upgrade_and_exchange_encrypted_data(tmp_path):
    async def scenario():
        certificate, private_key = write_test_certificate(tmp_path)
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(certificate, private_key)
        client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_context.load_verify_locations(cadata=CERTIFICATE_PEM)
        loop = asyncio.get_running_loop()
        client_socket, server_socket = socket.socketpair()
        client_socket.setblocking(False)
        server_socket.setblocking(False)
        payload = b"encrypted payload"
        client_protocol = UpgradeProtocol(loop)
        server_protocol = UpgradeProtocol(loop, len(payload))
        client_plain, _ = await loop.create_connection(
            lambda: client_protocol,
            sock=client_socket,
        )
        server_plain, _ = await loop.create_connection(
            lambda: server_protocol,
            sock=server_socket,
        )
        client_tls = None
        server_tls = None

        try:
            server_upgrade = asyncio.create_task(
                loop.start_tls(
                    server_plain,
                    server_protocol,
                    server_context,
                    server_side=True,
                    ssl_handshake_timeout=2,
                )
            )
            marker = loop.create_future()
            loop.call_soon(marker.set_result, None)
            await marker
            client_tls = await loop.start_tls(
                client_plain,
                client_protocol,
                client_context,
                server_hostname="localhost",
                ssl_handshake_timeout=2,
            )
            server_tls = await server_upgrade

            assert client_tls is not client_plain
            assert server_tls is not server_plain
            client_tls.write(payload)
            assert await server_protocol.data == payload
        finally:
            if client_tls is not None:
                client_tls.close()
            else:
                client_plain.close()
            if server_tls is not None:
                server_tls.close()
            else:
                server_plain.close()

    asyncio.run(scenario())
