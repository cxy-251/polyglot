"""339｜loop.start_tls 把既有 plain Transport/Protocol 原地升级为 TLS。

start_tls 在 transport 与 protocol 之间插入 coder；await 后必须只使用返回的新 transport，因为
coder 会缓存协议侧和 wire-side data。server/client 两端要协调升级，本例先让 server upgrade task
进入等待，再启动 client，避免 ClientHello 被旧 plain protocol 当 application data 消费。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.start_tls
# polyglot-covers: python.asyncio.start-tls-existing-transport-protocol
# polyglot-covers: python.asyncio.start-tls-server-side
# polyglot-covers: python.asyncio.start-tls-client-server-hostname
# polyglot-covers: python.asyncio.start-tls-handshake-timeout
# polyglot-covers: python.asyncio.start-tls-returns-new-transport
# polyglot-covers: python.asyncio.start-tls-stop-using-original-transport
# polyglot-covers: python.asyncio.start-tls-coordinated-upgrade

import asyncio
import socket
import ssl

from test_331_ssl_certificate_utilities_and_fixture import CERTIFICATE_PEM
from test_331_ssl_certificate_utilities_and_fixture import write_test_certificate


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
