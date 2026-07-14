"""307｜event loop 的异步 getaddrinfo/getnameinfo 桥接。

这两个 coroutine 对应 socket 模块的同步名称解析函数，event loop 通常把可能阻塞的解析工作
放入 executor。案例强制 numeric host/service，只验证地址结构转换，不查询 DNS，也不访问网络。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.getaddrinfo
# polyglot-covers: python.asyncio.getaddrinfo-coroutine
# polyglot-covers: python.asyncio.getaddrinfo-family-type-proto-address-tuples
# polyglot-covers: python.asyncio.getaddrinfo-numeric-no-dns
# polyglot-covers: python.asyncio.loop.getnameinfo
# polyglot-covers: python.asyncio.getnameinfo-coroutine
# polyglot-covers: python.asyncio.getnameinfo-numeric-no-dns

import asyncio
import socket


def test_numeric_address_and_name_resolution_are_async_and_network_free():
    async def scenario():
        loop = asyncio.get_running_loop()
        addresses = await loop.getaddrinfo(
            "127.0.0.1",
            "80",
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            flags=socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
        )

        assert addresses
        for family, sock_type, protocol, canonical_name, address in addresses:
            assert family == socket.AF_INET
            assert sock_type == socket.SOCK_STREAM
            assert isinstance(protocol, int)
            assert canonical_name == ""
            assert address == ("127.0.0.1", 80)

        host, service = await loop.getnameinfo(
            ("127.0.0.1", 80),
            socket.NI_NUMERICHOST | socket.NI_NUMERICSERV,
        )
        assert (host, service) == ("127.0.0.1", "80")

    asyncio.run(scenario())
