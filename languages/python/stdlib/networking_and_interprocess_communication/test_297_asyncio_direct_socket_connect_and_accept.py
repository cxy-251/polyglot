"""297｜用 event loop 在 Unix socket 上直接 connect 与 accept。

sock_connect/sock_accept 要求 non-blocking socket。accept 返回全新的连接 socket，监听 socket
仍归调用者。这里使用 pytest 临时目录中的 AF_UNIX 地址，不占用端口，也不依赖 DNS 或外部网络。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.sock_connect
# polyglot-covers: python.asyncio.sock-connect-nonblocking
# polyglot-covers: python.asyncio.loop.sock_accept
# polyglot-covers: python.asyncio.sock-accept-connection-address-pair
# polyglot-covers: python.asyncio.sock-accept-new-socket-ownership
# polyglot-covers: python.asyncio.direct-unix-socket-no-external-network

import asyncio
import socket


def test_sock_connect_and_accept_create_two_independently_owned_endpoints(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        path = tmp_path / "direct.sock"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.setblocking(False)
        client.setblocking(False)
        listener.bind(str(path))
        listener.listen(1)
        accepted = None

        try:
            accept_task = asyncio.create_task(loop.sock_accept(listener))
            assert await loop.sock_connect(client, str(path)) is None
            accepted, peer_address = await accept_task
            accepted.setblocking(False)

            # 未命名的 AF_UNIX client 通常给出空 peer address；其类型由平台表示决定，
            # 教学重点是返回二元组和新的 socket，而不是把该表示写死。
            assert isinstance(accepted, socket.socket)
            assert peer_address in ("", None)
            assert accepted.fileno() != listener.fileno()

            await loop.sock_sendall(client, b"hello")
            assert await loop.sock_recv(accepted, 16) == b"hello"
        finally:
            if accepted is not None:
                accepted.close()
            client.close()
            listener.close()

    asyncio.run(scenario())
