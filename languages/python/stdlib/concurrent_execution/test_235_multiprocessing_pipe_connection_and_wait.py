"""235｜``multiprocessing.Pipe`` message protocol、bytes buffers 与 multi-wait。

Connection 是 message-oriented channel：``send`` pickle object，``send_bytes`` 保留一个
bytes message boundary。duplex=False 返回 receive-only/send-only 两端。不要让多个 writer
并发使用同一 pipe end；frame 可能交错损坏。``connection.wait`` 可统一等待多个 endpoint。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.multiprocessing.Pipe python.multiprocessing.Pipe-duplex
# polyglot-covers: python.multiprocessing.Pipe-simplex-end-order
# polyglot-covers: python.multiprocessing.connection.Connection
# polyglot-covers: python.multiprocessing.Connection.send
# polyglot-covers: python.multiprocessing.Connection.recv
# polyglot-covers: python.multiprocessing.Connection-pickle-copy
# polyglot-covers: python.multiprocessing.Connection.poll
# polyglot-covers: python.multiprocessing.Connection.send_bytes
# polyglot-covers: python.multiprocessing.Connection.recv_bytes
# polyglot-covers: python.multiprocessing.Connection.recv_bytes_into
# polyglot-covers: python.multiprocessing.BufferTooShort
# polyglot-covers: python.multiprocessing.Connection.fileno
# polyglot-covers: python.multiprocessing.Connection.close
# polyglot-covers: python.multiprocessing.Connection-context-manager
# polyglot-covers: python.multiprocessing.connection.wait
# polyglot-covers: python.multiprocessing.pipe-shared-end-corruption-trap

import multiprocessing
import multiprocessing.connection

import pytest


def test_duplex_pipe_pickles_objects_and_preserves_message_boundaries():
    """recv 得到相等但独立 object graph；两个 duplex endpoints 都能 send/recv。"""

    left, right = multiprocessing.Pipe(duplex=True)
    payload = {"items": [1, 2]}

    try:
        left.send(payload)
        received = right.recv()
        assert received == payload
        assert received is not payload
        assert received["items"] is not payload["items"]

        right.send("reply")
        assert left.poll(timeout=0) is True
        assert left.recv() == "reply"
        assert isinstance(left.fileno(), int)
    finally:
        left.close()
        right.close()


def test_simplex_pipe_returns_receive_end_then_send_end():
    """duplex=False 的 tuple 顺序很容易写反；错误方向调用以 OSError 明确失败。"""

    receive_end, send_end = multiprocessing.Pipe(duplex=False)

    try:
        send_end.send({"answer": 42})
        assert receive_end.recv() == {"answer": 42}
        with pytest.raises(OSError, match="write-only"):
            send_end.recv()
        with pytest.raises(OSError, match="read-only"):
            receive_end.send("invalid")
    finally:
        receive_end.close()
        send_end.close()


def test_send_bytes_offset_and_recv_bytes_into_small_buffer_error():
    """BufferTooShort.args[0] 保留完整 message，调用方可据此扩容而不丢数据。"""

    receive_end, send_end = multiprocessing.Pipe(duplex=False)

    try:
        send_end.send_bytes(b"abcdef", offset=1, size=3)
        assert receive_end.recv_bytes() == b"bcd"

        send_end.send_bytes(b"hello")
        small = bytearray(2)
        with pytest.raises(multiprocessing.BufferTooShort) as raised:
            receive_end.recv_bytes_into(small)
        assert raised.value.args == (b"hello",)
    finally:
        receive_end.close()
        send_end.close()


def test_recv_raises_eof_after_peer_closes_and_messages_are_drained():
    """close 不生成普通 sentinel object；读取完 frame 后下一次 recv 抛 EOFError。"""

    receive_end, send_end = multiprocessing.Pipe(duplex=False)
    send_end.send("last")
    send_end.close()

    try:
        assert receive_end.recv() == "last"
        with pytest.raises(EOFError):
            receive_end.recv()
    finally:
        receive_end.close()


def test_connection_context_manager_closes_endpoint():
    """__enter__ 返回自身，__exit__ 无论异常与否调用 close。"""

    left, right = multiprocessing.Pipe()

    with left as entered:
        assert entered is left
        left.send("value")

    assert left.closed is True
    assert right.recv() == "value"
    right.close()


def test_connection_wait_returns_only_ready_endpoints():
    """数据已 send 后用 timeout=0 检查，不依赖调度或 wall-clock delay。"""

    first_receive, first_send = multiprocessing.Pipe(duplex=False)
    second_receive, second_send = multiprocessing.Pipe(duplex=False)

    try:
        second_send.send("second")
        ready = multiprocessing.connection.wait(
            [first_receive, second_receive],
            timeout=0,
        )

        assert ready == [second_receive]
        assert second_receive.recv() == "second"
    finally:
        first_receive.close()
        first_send.close()
        second_receive.close()
        second_send.close()
