"""280｜``open_connection(sock=...)``、StreamWriter flow control 与 half-close。

传入 sock 会把 ownership 转交给 StreamWriter；caller 只能关闭 writer，不能再独立管理该
socket。write/writelines 只写入 transport buffer，drain 才实施 high/low watermark backpressure。
close 后应 await wait_closed。案例只使用 socketpair，不访问网络或固定机器端口。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import asyncio
import socket


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
