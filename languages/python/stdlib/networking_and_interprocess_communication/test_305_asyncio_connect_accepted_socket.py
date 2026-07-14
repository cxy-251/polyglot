"""305｜把 asyncio 外部 accept 的 socket 接入 Transport/Protocol。

connect_accepted_socket 适合由其他线程或既有 server 接受连接，再交给 event loop 管理的框架。
成功后 accepted socket 的所有权转移给 transport；返回值仍是 (transport, protocol)。这里用
AF_UNIX 监听地址，避免端口、DNS 和外部网络依赖。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.connect_accepted_socket
# polyglot-covers: python.asyncio.connect-accepted-socket-preaccepted-input
# polyglot-covers: python.asyncio.connect-accepted-socket-transport-protocol-pair
# polyglot-covers: python.asyncio.connect-accepted-socket-ownership-transfer
# polyglot-covers: python.asyncio.connect-accepted-socket-external-accept-workflow

import asyncio
import socket


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
