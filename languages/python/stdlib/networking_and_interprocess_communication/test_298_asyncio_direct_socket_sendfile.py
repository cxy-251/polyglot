"""298｜loop.sock_sendfile 的零拷贝优先文件传输。

sock_sendfile 尝试 os.sendfile，平台不支持时默认退回普通读取发送；file 必须是二进制模式的
regular file，socket 必须是 non-blocking SOCK_STREAM。返回实际发送字节数，并更新文件位置。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.sock_sendfile
# polyglot-covers: python.asyncio.sock-sendfile-stream-socket
# polyglot-covers: python.asyncio.sock-sendfile-binary-regular-file
# polyglot-covers: python.asyncio.sock-sendfile-offset-count
# polyglot-covers: python.asyncio.sock-sendfile-return-count
# polyglot-covers: python.asyncio.sock-sendfile-updates-file-position
# polyglot-covers: python.asyncio.sock-sendfile-fallback-default

import asyncio
import socket


def test_sock_sendfile_honors_offset_and_count_and_advances_the_file(tmp_path):
    async def scenario():
        loop = asyncio.get_running_loop()
        source = tmp_path / "payload.bin"
        source.write_bytes(b"0123456789")
        left, right = socket.socketpair()
        left.setblocking(False)
        right.setblocking(False)
        try:
            with source.open("rb") as file:
                sent = await loop.sock_sendfile(left, file, offset=2, count=4)
                received = await loop.sock_recv(right, 16)

                assert sent == 4
                assert received == b"2345"
                assert file.tell() == 6
        finally:
            left.close()
            right.close()

    asyncio.run(scenario())
