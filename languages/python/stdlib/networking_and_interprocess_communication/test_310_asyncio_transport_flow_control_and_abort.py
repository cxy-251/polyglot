"""310｜WriteTransport 的 high/low watermark、protocol flow control 与 abort。

write 不阻塞；内核暂时写不下的字节进入 transport buffer。buffer 超过 high watermark 时，
protocol.pause_writing 被调用；降到 low 或更低时 resume_writing。协议应据此暂停生产数据，不能
只看一次 write 的返回值。abort 立即丢弃尚未发送的 buffer，而 close 会先异步 flush。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import asyncio
import socket

import pytest


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
