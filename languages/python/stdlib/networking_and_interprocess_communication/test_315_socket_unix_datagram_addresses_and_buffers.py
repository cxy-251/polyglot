"""315｜AF_UNIX datagram 的 sendto/recvfrom、消息边界和 recvfrom_into。

未 connect 的 datagram socket 每次 sendto 指定目标，recvfrom 同时返回完整消息和发送方地址。
消息超过 bufsize 会被截断而非留给下一次读取。pathname 地址是 str；案例全部放在 pytest 临时
目录，不使用网络接口。recvfrom_into 可直接写 caller buffer，并同样返回来源地址。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.socket.socket.bind
# polyglot-covers: python.socket.AF_UNIX-pathname-address-str
# polyglot-covers: python.socket.socket.sendto
# polyglot-covers: python.socket.sendto-unconnected-destination
# polyglot-covers: python.socket.socket.recvfrom
# polyglot-covers: python.socket.recvfrom-data-address-pair
# polyglot-covers: python.socket.datagram-preserves-message-boundaries
# polyglot-covers: python.socket.datagram-truncation-discards-remainder
# polyglot-covers: python.socket.socket.recvfrom_into
# polyglot-covers: python.socket.recvfrom-into-count-and-address

import socket


def test_sendto_and_recvfrom_preserve_separate_datagrams_and_source_address(tmp_path):
    sender_path = tmp_path / "sender.sock"
    receiver_path = tmp_path / "receiver.sock"
    sender = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sender.bind(str(sender_path))
        receiver.bind(str(receiver_path))
        assert sender.sendto(b"first", str(receiver_path)) == 5
        assert sender.sendto(b"second", str(receiver_path)) == 6

        first, first_address = receiver.recvfrom(64)
        second, second_address = receiver.recvfrom(64)
        assert (first, second) == (b"first", b"second")
        assert first_address == second_address == str(sender_path)
    finally:
        sender.close()
        receiver.close()


def test_small_datagram_buffer_discards_remainder_and_into_returns_address(tmp_path):
    sender_path = tmp_path / "sender-into.sock"
    receiver_path = tmp_path / "receiver-into.sock"
    sender = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    buffer = bytearray(b"........")
    try:
        sender.bind(str(sender_path))
        receiver.bind(str(receiver_path))
        sender.sendto(b"too-long", str(receiver_path))
        assert receiver.recvfrom(3)[0] == b"too"

        sender.sendto(b"next", str(receiver_path))
        count, address = receiver.recvfrom_into(memoryview(buffer)[2:6])
        assert count == 4
        assert address == str(sender_path)
        assert buffer == bytearray(b"..next..")
    finally:
        sender.close()
        receiver.close()
