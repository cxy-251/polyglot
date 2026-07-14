"""301｜DatagramTransport/DatagramProtocol 保留消息边界的无连接 I/O。

datagram_received 每次给出一个完整 datagram 和平台形式的 peer address；它不同于 stream，
不需要自己重组字节流。error_received 只在底层能观察到 OSError 时触发，无法投递的数据也可能
被静默丢弃，因此它不是可靠送达确认。传入 sock 后，关闭责任转移给 transport。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.create_datagram_endpoint
# polyglot-covers: python.asyncio.create-datagram-endpoint-existing-sock
# polyglot-covers: python.asyncio.DatagramTransport
# polyglot-covers: python.asyncio.DatagramProtocol
# polyglot-covers: python.asyncio.datagram-protocol.datagram_received
# polyglot-covers: python.asyncio.datagram-protocol.error_received
# polyglot-covers: python.asyncio.datagram-message-boundary
# polyglot-covers: python.asyncio.datagram-undeliverable-may-be-silent
# polyglot-covers: python.asyncio.datagram-transport.sendto
# polyglot-covers: python.asyncio.datagram-transport.close
# polyglot-covers: python.asyncio.datagram-socket-ownership-transfer

import asyncio
import socket


class RecordingDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.datagrams = loop.create_future()
        self.errors = []
        self.closed = loop.create_future()
        self.received = []

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.received.append((data, addr))
        if len(self.received) == 2:
            self.datagrams.set_result(list(self.received))

    def error_received(self, exc):
        # 某些平台永远不会为无法投递的数据调用这里，因此这里只记录协议契约。
        self.errors.append(exc)

    def connection_lost(self, exc):
        self.closed.set_result(exc)


async def _recv_datagram(loop, sock):
    ready = loop.create_future()

    def receive_once():
        try:
            ready.set_result(sock.recv(64))
        except BaseException as error:
            ready.set_exception(error)
        finally:
            loop.remove_reader(sock.fileno())

    loop.add_reader(sock.fileno(), receive_once)
    return await ready


def test_connected_datagram_transport_preserves_each_message_boundary():
    async def scenario():
        loop = asyncio.get_running_loop()
        owned, peer = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        owned.setblocking(False)
        peer.setblocking(False)
        protocol = RecordingDatagramProtocol(loop)
        transport, returned = await loop.create_datagram_endpoint(
            lambda: protocol,
            sock=owned,
        )
        try:
            peer.send(b"one")
            peer.send(b"two")
            received = await protocol.datagrams

            assert returned is protocol
            assert [data for data, _ in received] == [b"one", b"two"]
            assert protocol.errors == []

            transport.sendto(b"reply")
            assert await _recv_datagram(loop, peer) == b"reply"
        finally:
            transport.close()
            assert await protocol.closed is None
            peer.close()

    asyncio.run(scenario())
