"""302｜把现有 OS pipe 接入 event loop 的 ReadTransport/WriteTransport。

connect_read_pipe/connect_write_pipe 接收 file-like pipe，返回 (transport, protocol)。Unix 的
SelectorEventLoop 会把 pipe 设为 non-blocking。pause_reading 只暂停向 protocol 投递，不阻止
内核 pipe 接收；resume_reading 后继续。关闭 write end 后，reader 最终观察到 EOF。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.connect_read_pipe
# polyglot-covers: python.asyncio.loop.connect_write_pipe
# polyglot-covers: python.asyncio.pipe-transport-protocol-pair
# polyglot-covers: python.asyncio.selector-loop-pipe-nonblocking
# polyglot-covers: python.asyncio.ReadTransport
# polyglot-covers: python.asyncio.read-transport.pause_reading
# polyglot-covers: python.asyncio.read-transport.resume_reading
# polyglot-covers: python.asyncio.read-transport.is_reading
# polyglot-covers: python.asyncio.WriteTransport
# polyglot-covers: python.asyncio.pipe-write-close-delivers-eof

import asyncio
import os


async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_read_and_write_pipe_transports_support_pause_resume_and_eof():
    async def scenario():
        loop = asyncio.get_running_loop()
        read_fd, write_fd = os.pipe()
        read_pipe = os.fdopen(read_fd, "rb", buffering=0)
        write_pipe = os.fdopen(write_fd, "wb", buffering=0)
        reader = asyncio.StreamReader()
        read_protocol = asyncio.StreamReaderProtocol(reader)
        read_transport = None
        write_transport = None

        try:
            read_transport, returned_reader_protocol = await loop.connect_read_pipe(
                lambda: read_protocol,
                read_pipe,
            )
            write_transport, write_protocol = await loop.connect_write_pipe(
                asyncio.Protocol,
                write_pipe,
            )
            assert returned_reader_protocol is read_protocol
            assert isinstance(write_protocol, asyncio.Protocol)
            assert read_transport.is_reading() is True

            read_transport.pause_reading()
            assert read_transport.is_reading() is False
            pending = asyncio.create_task(reader.readexactly(4))
            write_transport.write(b"pipe")
            await _next_loop_turn()
            assert pending.done() is False

            read_transport.resume_reading()
            assert await pending == b"pipe"
            write_transport.close()
            assert await reader.read() == b""
        finally:
            if write_transport is not None:
                write_transport.close()
            else:
                write_pipe.close()
            if read_transport is not None:
                read_transport.close()
            else:
                read_pipe.close()

    asyncio.run(scenario())
