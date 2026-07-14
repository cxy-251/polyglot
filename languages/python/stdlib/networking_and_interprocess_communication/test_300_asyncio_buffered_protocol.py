"""300｜BufferedProtocol 让协议直接提供接收缓冲区。

普通 Protocol 的 data_received 会收到新 bytes；BufferedProtocol 改为 get_buffer 提供可写
buffer，event loop 填充后用 buffer_updated(nbytes) 告知有效长度，从而减少大数据接收时的复制。
sizehint 只是建议，返回零长度 buffer 才是错误；只应读取本次 nbytes 覆盖的前缀。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.BufferedProtocol
# polyglot-covers: python.asyncio.buffered-protocol.get_buffer
# polyglot-covers: python.asyncio.buffered-protocol-sizehint-advisory
# polyglot-covers: python.asyncio.buffered-protocol-nonzero-writable-buffer
# polyglot-covers: python.asyncio.buffered-protocol.buffer_updated
# polyglot-covers: python.asyncio.buffered-protocol-nbytes-valid-prefix
# polyglot-covers: python.asyncio.buffered-protocol-reduces-receive-copying
# polyglot-covers: python.asyncio.buffered-protocol-lifecycle

import asyncio
import socket


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
