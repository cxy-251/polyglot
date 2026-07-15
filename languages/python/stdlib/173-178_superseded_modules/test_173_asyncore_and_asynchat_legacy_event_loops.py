"""173｜asyncore 与 asynchat：旧式 select channel 和终止符协议。

asyncore 用 channel map 驱动非阻塞 socket，asynchat 在其上增加 terminator 与
producer 队列。两者在 3.10 只为兼容旧程序保留，新代码应使用 asyncio；
这些案例用于读懂遗留框架的回调、缓冲和关闭语义，
不是推荐新项目采用它。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.asyncore python.asyncore.loop
# polyglot-covers: python.asyncore.channel-map python.asyncore.dispatcher
# polyglot-covers: python.asyncore.readable-writable python.asyncore.event-callbacks
# polyglot-covers: python.asyncore.handle-read-close python.asyncore.handle-error
# polyglot-covers: python.asyncore.dispatcher-with-send python.asyncore.buffered-send
# polyglot-covers: python.asyncore.file-wrapper python.asyncore.close-removes-map
# polyglot-covers: python.stdlib.asynchat python.asynchat.async-chat
# polyglot-covers: python.asynchat.byte-terminator python.asynchat.integer-terminator
# polyglot-covers: python.asynchat.none-terminator python.asynchat.split-terminator
# polyglot-covers: python.asynchat.collect-incoming-data
# polyglot-covers: python.asynchat.found-terminator python.asynchat.trailing-data
# polyglot-covers: python.asynchat.push python.asynchat.producer-more
# polyglot-covers: python.asynchat.close-when-done python.asynchat.discard-buffers

import os
import socket

import asynchat
import asyncore
import pytest


class RecordingDispatcher(asyncore.dispatcher):
    def __init__(self, sock, channel_map):
        super().__init__(sock=sock, map=channel_map)
        self.received = []
        self.closed = False

    def handle_read(self):
        data = self.recv(8192)
        if data:
            self.received.append(data)
        else:
            self.handle_close()

    def handle_close(self):
        self.closed = True
        self.close()

    def writable(self):
        return False


class MessageChat(asynchat.async_chat):
    def __init__(self, sock, channel_map, terminator):
        super().__init__(sock=sock, map=channel_map)
        self.fragments = []
        self.messages = []
        self.set_terminator(terminator)

    def collect_incoming_data(self, data):
        self.fragments.append(data)

    def found_terminator(self):
        self.messages.append(b"".join(self.fragments))
        self.fragments.clear()

    def writable(self):
        return bool(self.producer_fifo)


class ChunkProducer:
    def __init__(self, *chunks):
        self.chunks = list(chunks)
        self.calls = 0

    def more(self):
        self.calls += 1
        if self.chunks:
            return self.chunks.pop(0)
        return b""


def socket_pair():
    return socket.socketpair()


def test_dispatcher_joins_a_custom_map_and_close_removes_it():
    channel_map = {}
    left, right = socket_pair()
    channel = asyncore.dispatcher(left, map=channel_map)
    try:
        assert channel.fileno() in channel_map
        assert channel_map[channel.fileno()] is channel
        assert channel.readable() is True
        assert channel.writable() is True
        assert channel.connected is True
    finally:
        channel.close()
        right.close()

    assert channel_map == {}
    # 不传 map 会落入模块全局 socket_map，测试和可复用组件都更难隔离。


def test_loop_dispatches_ready_reads_and_stops_after_count_passes():
    channel_map = {}
    left, right = socket_pair()
    channel = RecordingDispatcher(left, channel_map)
    try:
        right.sendall(b"event-data")
        asyncore.loop(
            timeout=0,
            map=channel_map,
            count=1,
        )
        assert channel.received == [b"event-data"]
        assert channel.closed is False
    finally:
        channel.close()
        right.close()


def test_peer_eof_becomes_handle_close_and_removes_the_channel():
    channel_map = {}
    left, right = socket_pair()
    channel = RecordingDispatcher(left, channel_map)
    right.close()

    asyncore.loop(timeout=0, map=channel_map, count=2)

    assert channel.closed is True
    assert channel_map == {}


def test_dispatcher_handle_error_is_the_callback_exception_boundary():
    events = []

    class FailingDispatcher(asyncore.dispatcher):
        def handle_read(self):
            raise RuntimeError("callback failed")

        def handle_error(self):
            events.append("handled")
            self.close()

        def writable(self):
            return False

    channel_map = {}
    left, right = socket_pair()
    channel = FailingDispatcher(left, map=channel_map)
    try:
        right.sendall(b"trigger")
        asyncore.loop(timeout=0, map=channel_map, count=1)
    finally:
        channel.close()
        right.close()

    assert events == ["handled"]
    # 默认 handle_error 打印压缩 traceback；服务端通常应覆盖它，
    # 记录上下文后关闭 channel。


def test_dispatcher_with_send_buffers_unsent_suffixes():
    channel_map = {}
    left, right = socket_pair()
    right.settimeout(1)
    channel = asyncore.dispatcher_with_send(left, map=channel_map)
    try:
        sent_or_buffered = channel.send(b"hello")
        assert 0 <= sent_or_buffered <= 5
        while channel.out_buffer:
            asyncore.loop(timeout=0, map=channel_map, count=1)
        assert right.recv(5) == b"hello"
    finally:
        channel.close()
        right.close()
    # send 的返回值可能小于输入长度；dispatcher_with_send 保存剩余部分。


def test_file_wrapper_duplicates_the_original_descriptor_on_unix():
    if os.name != "posix":
        pytest.skip("file_wrapper 仅在 Unix 提供")

    read_fd, write_fd = os.pipe()
    wrapper = asyncore.file_wrapper(read_fd)
    os.close(read_fd)
    try:
        os.write(write_fd, b"wrapped")
        assert wrapper.recv(7) == b"wrapped"
    finally:
        wrapper.close()
        os.close(write_fd)
    # wrapper 使用 dup，所以关闭原 fd 不会使包装后的 channel 失效。


def test_asynchat_byte_terminator_can_span_multiple_socket_reads():
    channel_map = {}
    left, right = socket_pair()
    chat = MessageChat(left, channel_map, b"\r\n\r\n")
    try:
        right.sendall(b"Header: value\r\n")
        asyncore.loop(timeout=0, map=channel_map, count=1)
        assert chat.messages == []

        right.sendall(b"\r\ntrailing")
        asyncore.loop(timeout=0, map=channel_map, count=1)
        assert chat.messages == [b"Header: value"]
        assert b"".join(chat.fragments) == b"trailing"
    finally:
        chat.close()
        right.close()
    # terminator 后的字节不会丢失，而是继续按当前或新 terminator 处理。


def test_asynchat_integer_terminator_collects_an_exact_byte_count():
    channel_map = {}
    left, right = socket_pair()
    chat = MessageChat(left, channel_map, 5)
    try:
        right.sendall(b"helloextra")
        asyncore.loop(timeout=0, map=channel_map, count=1)
        assert chat.messages == [b"hello"]
        assert b"".join(chat.fragments) == b"extra"
        assert chat.get_terminator() == 0
    finally:
        chat.close()
        right.close()
    # 数值 terminator 会递减到 0；found_terminator 通常应设置下一阶段条件。


def test_asynchat_none_terminator_collects_without_firing_callback():
    channel_map = {}
    left, right = socket_pair()
    chat = MessageChat(left, channel_map, None)
    try:
        right.sendall(b"unbounded")
        asyncore.loop(timeout=0, map=channel_map, count=1)
        assert chat.messages == []
        assert chat.fragments == [b"unbounded"]
    finally:
        chat.close()
        right.close()


def test_asynchat_push_producer_and_close_when_done_preserve_fifo_order():
    channel_map = {}
    left, right = socket_pair()
    right.settimeout(1)
    chat = MessageChat(left, channel_map, None)
    producer = ChunkProducer(b"second-", b"third")
    try:
        chat.push(b"first-")
        chat.push_with_producer(producer)
        chat.close_when_done()

        for _ in range(10):
            if not channel_map:
                break
            asyncore.loop(timeout=0, map=channel_map, count=1)

        received = b""
        while True:
            chunk = right.recv(8192)
            if not chunk:
                break
            received += chunk
    finally:
        chat.close()
        right.close()

    assert received == b"first-second-third"
    assert producer.calls == 3
    assert channel_map == {}
    # producer.more() 用 b"" 表示耗尽；队列里的 None 才表示发送完后
    # 关闭 channel。


def test_discard_buffers_clears_input_output_and_producer_state():
    chat = MessageChat(None, {}, b"\n")
    chat.ac_in_buffer = b"incoming"
    chat.incoming = [b"application fragment"]
    chat.push(b"outgoing")
    assert chat.producer_fifo

    assert chat.discard_buffers() is None

    assert chat.ac_in_buffer == b""
    assert list(chat.producer_fifo) == []
    # discard_buffers 不知道子类自建的 incoming 属性；
    # 业务缓冲仍需子类自行清理。
    assert chat.incoming == [b"application fragment"]


def test_abstract_async_chat_callbacks_must_be_overridden():
    chat = asynchat.async_chat(map={})
    with pytest.raises(NotImplementedError):
        chat.collect_incoming_data(b"data")
    with pytest.raises(NotImplementedError):
        chat.found_terminator()
