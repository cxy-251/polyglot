"""296｜event loop 直接操作非阻塞 stream socket。

sock_recv/sock_recv_into/sock_sendall 是 socket 阻塞 API 的 coroutine 版本；传入的 socket
必须先设为 non-blocking。sendall 成功只返回 None，失败时也无法得知对端实际处理了多少字节。
直接 socket API 较直观，但大量连接通常由 Transport/Protocol 或 Streams 更高效地管理。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.sock_recv
# polyglot-covers: python.asyncio.sock-recv-up-to-nbytes
# polyglot-covers: python.asyncio.loop.sock_recv_into
# polyglot-covers: python.asyncio.sock-recv-into-buffer-count
# polyglot-covers: python.asyncio.loop.sock_sendall
# polyglot-covers: python.asyncio.sock-sendall-none-on-success
# polyglot-covers: python.asyncio.direct-socket-must-be-nonblocking
# polyglot-covers: python.asyncio.direct-socketpair-local-workflow

import asyncio
import socket


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
