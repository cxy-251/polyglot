"""281｜临时 Unix socket 的 ``start_unix_server/open_unix_connection`` workflow。

stream server 为每个连接把 client callback 调度为 Task，并交付 reader/writer。start_serving
可把 bind/listen 与开始 accept 分开；Server async context 退出时 close 并 wait_closed。
Unix socket path 使用 pytest 临时目录，无公网、固定端口或持久机器状态。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import asyncio
import os
import socket

import pytest


pytestmark = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="案例使用临时 Unix-domain stream socket",
)


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
