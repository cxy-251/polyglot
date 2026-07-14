"""295｜event loop 直接监听文件描述符的可读、可写事件。

add_reader/add_writer 属于 SelectorEventLoop 的低层能力，适合整合已有 fd；普通应用优先
Streams。注册同一 fd 会替换旧 callback，remove_* 的 bool 能区分“确实移除”和“本来没有”。
callback 必须主动读取或移除监听，否则 level-triggered fd 会持续就绪并反复触发。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.add_reader
# polyglot-covers: python.asyncio.loop.remove_reader
# polyglot-covers: python.asyncio.add-reader-callback-args
# polyglot-covers: python.asyncio.add-reader-replaces-existing-callback
# polyglot-covers: python.asyncio.reader-callback-must-consume-or-remove
# polyglot-covers: python.asyncio.loop.add_writer
# polyglot-covers: python.asyncio.loop.remove_writer
# polyglot-covers: python.asyncio.remove-fd-watcher-return-value
# polyglot-covers: python.asyncio.fd-watchers-selector-loop

import asyncio
import os
import socket


def test_reader_callback_consumes_the_fd_and_replacement_is_observable():
    async def scenario():
        loop = asyncio.get_running_loop()
        read_fd, write_fd = os.pipe()
        received = loop.create_future()
        stale_calls = []

        def stale_callback():
            stale_calls.append("不应执行")

        def consume(prefix):
            # fd 的“可读”只是 readiness 通知；数据仍需调用者自己读取。
            payload = os.read(read_fd, 64)
            assert loop.remove_reader(read_fd) is True
            received.set_result(prefix + payload)

        try:
            loop.add_reader(read_fd, stale_callback)
            loop.add_reader(read_fd, consume, b"prefix:")
            os.write(write_fd, b"ready")

            assert await received == b"prefix:ready"
            assert stale_calls == []
            assert loop.remove_reader(read_fd) is False
        finally:
            loop.remove_reader(read_fd)
            os.close(read_fd)
            os.close(write_fd)

    asyncio.run(scenario())


def test_writer_callback_fires_for_a_writable_socket_and_can_remove_itself():
    async def scenario():
        loop = asyncio.get_running_loop()
        left, right = socket.socketpair()
        writable = loop.create_future()

        def on_writable(label):
            assert loop.remove_writer(left.fileno()) is True
            writable.set_result(label)

        try:
            loop.add_writer(left.fileno(), on_writable, "socket is writable")
            assert await writable == "socket is writable"
            assert loop.remove_writer(left.fileno()) is False
        finally:
            loop.remove_writer(left.fileno())
            left.close()
            right.close()

    asyncio.run(scenario())
