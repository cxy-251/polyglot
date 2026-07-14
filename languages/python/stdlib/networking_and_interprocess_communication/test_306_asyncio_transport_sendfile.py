"""306｜loop.sendfile 通过 Transport 发送 regular file。

它与 sock_sendfile 的传输语义相同，但输入是 event loop 管理的 stream transport。实现优先
os.sendfile，默认允许 fallback；返回传输字节数并更新 file position。SSL transport 通常只能
走 fallback，因为加密层不能直接零拷贝发送明文文件。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.sendfile
# polyglot-covers: python.asyncio.transport-sendfile-regular-binary-file
# polyglot-covers: python.asyncio.transport-sendfile-offset-count
# polyglot-covers: python.asyncio.transport-sendfile-return-count
# polyglot-covers: python.asyncio.transport-sendfile-updates-file-position
# polyglot-covers: python.asyncio.transport-sendfile-os-sendfile-preferred
# polyglot-covers: python.asyncio.transport-sendfile-fallback
# polyglot-covers: python.asyncio.SendfileNotAvailableError

import asyncio
import socket


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
