"""304｜低层 Unix protocol server 与 asyncio.Server 生命周期。

start_serving=False 可先取得监听 socket、完成其他初始化，再显式 start_serving。Server.sockets
返回内部列表的副本；close 只停止接收新连接，wait_closed 才等待关闭完成。Server 也支持
async context manager，退出时保证监听端已经关闭。案例只使用 pytest 临时 Unix socket。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.create_unix_server
# polyglot-covers: python.asyncio.loop.create_unix_connection
# polyglot-covers: python.asyncio.protocol-server-factory-per-connection
# polyglot-covers: python.asyncio.Server
# polyglot-covers: python.asyncio.Server.get_loop
# polyglot-covers: python.asyncio.Server.sockets-copy
# polyglot-covers: python.asyncio.Server.start-serving-idempotent
# polyglot-covers: python.asyncio.Server.serve_forever
# polyglot-covers: python.asyncio.Server-serve-forever-cancellation-closes

import asyncio

import pytest


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
