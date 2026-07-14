"""299｜stream Transport 与 Protocol 的连接状态机和双向 I/O。

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
