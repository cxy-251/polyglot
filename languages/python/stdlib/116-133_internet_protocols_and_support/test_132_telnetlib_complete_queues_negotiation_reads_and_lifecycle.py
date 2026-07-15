"""132｜telnetlib 的 IAC 转义、协商、队列、读取策略与连接生命周期。

Telnet 是字节协议，不负责终端文本编码。案例直接向协议队列喂入字节，
并用内存 socket 展示读取方法背后的状态机；不连接外部服务或进入 stdin。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过
pytest 统一验证。
"""

# polyglot-covers: python.stdlib.telnetlib python.telnetlib.Telnet-default-state
# polyglot-covers: python.telnetlib.write-iac-doubling python.telnetlib.bytes-only
# polyglot-covers: python.telnetlib.process_rawq python.telnetlib.iac-iac-literal
# polyglot-covers: python.telnetlib.option-negotiation-default-rejection
# polyglot-covers: python.telnetlib.set_option_negotiation_callback
# polyglot-covers: python.telnetlib.subnegotiation-data python.telnetlib.read_sb_data
# polyglot-covers: python.telnetlib.read_until-buffer-boundary
# polyglot-covers: python.telnetlib.expect-regex-order-and-match
# polyglot-covers: python.telnetlib.read_very_lazy-eof python.telnetlib.read_lazy
# polyglot-covers: python.telnetlib.read_some python.telnetlib.read_all
# polyglot-covers: python.telnetlib.fill_rawq-eof python.telnetlib.get_socket
# polyglot-covers: python.telnetlib.open-timeout-zero python.telnetlib.context-manager

import re

import telnetlib
import pytest


class MemoryTelnetSocket:
    def __init__(self, chunks=()):
        self.chunks = iter(chunks)
        self.sent = []
        self.closed = False

    def recv(self, size):
        try:
            return next(self.chunks)
        except StopIteration:
            return b""

    def sendall(self, data):
        self.sent.append(data)

    def close(self):
        self.closed = True


def test_telnet_default_state_is_disconnected_and_uses_separate_protocol_queues():
    client = telnetlib.Telnet()

    assert client.sock is None
    assert client.rawq == b""
    assert client.cookedq == b""
    assert client.sbdataq == b""
    assert client.eof == 0
    assert client.get_socket() is None


def test_telnet_write_requires_bytes_and_doubles_iac_octets():
    client = telnetlib.Telnet()
    client.sock = MemoryTelnetSocket()

    client.write(b"alpha" + telnetlib.IAC + b"omega")

    assert client.sock.sent == [b"alpha" + telnetlib.IAC * 2 + b"omega"]
    with pytest.raises(TypeError):
        client.write("text is not implicitly encoded")


def test_telnet_process_rawq_turns_doubled_iac_into_literal_data():
    client = telnetlib.Telnet()
    client.rawq = b"left" + telnetlib.IAC * 2 + b"right"

    client.process_rawq()

    assert client.cookedq == b"left" + telnetlib.IAC + b"right"
    assert client.rawq == b""


def test_telnet_default_negotiation_rejects_remote_will_and_do_requests():
    client = telnetlib.Telnet()
    client.sock = MemoryTelnetSocket()
    client.rawq = (
        telnetlib.IAC
        + telnetlib.WILL
        + telnetlib.ECHO
        + telnetlib.IAC
        + telnetlib.DO
        + telnetlib.SGA
    )

    client.process_rawq()

    assert client.sock.sent == [
        telnetlib.IAC + telnetlib.DONT + telnetlib.ECHO,
        telnetlib.IAC + telnetlib.WONT + telnetlib.SGA,
    ]
    assert client.cookedq == b""


def test_telnet_negotiation_callback_observes_commands_and_takes_over_reply_policy():
    client = telnetlib.Telnet()
    client.sock = MemoryTelnetSocket()
    events = []
    client.set_option_negotiation_callback(
        lambda sock, command, option: events.append((sock, command, option))
    )
    client.rawq = telnetlib.IAC + telnetlib.WILL + telnetlib.ECHO

    client.process_rawq()

    assert events == [(client.sock, telnetlib.WILL, telnetlib.ECHO)]
    # 一旦提供 callback，库不会再自动发送 DONT/WONT；协商责任属于回调。
    assert client.sock.sent == []


def test_telnet_subnegotiation_bytes_are_separated_from_normal_cooked_data():
    client = telnetlib.Telnet()
    client.sock = MemoryTelnetSocket()
    client.rawq = (
        b"before"
        + telnetlib.IAC
        + telnetlib.SB
        + b"\x18terminal-type"
        + telnetlib.IAC
        + telnetlib.SE
        + b"after"
    )

    client.process_rawq()

    assert client.cookedq == b"beforeafter"
    assert client.read_sb_data() == b"\x18terminal-type"
    assert client.read_sb_data() == b""


def test_telnet_read_until_returns_through_match_and_keeps_trailing_bytes():
    client = telnetlib.Telnet()
    client.cookedq = b"banner\r\nlogin: trailing"

    result = client.read_until(b"login:", timeout=0)

    assert result == b"banner\r\nlogin:"
    assert client.cookedq == b" trailing"


def test_telnet_expect_uses_first_matching_pattern_and_returns_match_object():
    client = telnetlib.Telnet()
    client.cookedq = b"status=READY code=200 tail"

    index, match, data = client.expect(
        [re.compile(br"status=(\w+)"), re.compile(br"code=(\d+)")],
        timeout=0,
    )

    assert index == 0
    assert match.group(1) == b"READY"
    assert data == b"status=READY"
    assert client.cookedq == b" code=200 tail"


def test_telnet_read_lazy_processes_available_raw_bytes_without_socket_read():
    client = telnetlib.Telnet()
    client.rawq = b"alpha" + telnetlib.IAC * 2 + b"beta"

    assert client.read_lazy() == b"alpha" + telnetlib.IAC + b"beta"
    assert client.rawq == b""
    assert client.cookedq == b""


def test_telnet_read_very_lazy_returns_buffer_then_raises_only_on_empty_eof():
    client = telnetlib.Telnet()
    client.cookedq = b"last bytes"
    client.eof = 1

    assert client.read_very_lazy() == b"last bytes"
    with pytest.raises(EOFError, match="telnet connection closed"):
        client.read_very_lazy()


def test_telnet_fill_rawq_reads_one_chunk_and_marks_empty_recv_as_eof():
    client = telnetlib.Telnet()
    client.sock = MemoryTelnetSocket([b"first", b""])

    client.fill_rawq()
    assert client.rawq == b"first"
    assert client.eof == 0

    client.fill_rawq()
    assert client.eof == 1


def test_telnet_read_some_returns_cooked_data_or_empty_bytes_at_eof():
    client = telnetlib.Telnet()
    client.sock = MemoryTelnetSocket([b"hello", b""])

    assert client.read_some() == b"hello"
    assert client.read_some() == b""


def test_telnet_read_all_drains_until_orderly_eof_and_processes_iac():
    client = telnetlib.Telnet()
    client.sock = MemoryTelnetSocket(
        [b"alpha", telnetlib.IAC * 2 + b"beta", b""]
    )

    assert client.read_all() == b"alpha" + telnetlib.IAC + b"beta"
    assert client.eof == 1


def test_telnet_open_passes_connection_parameters_and_rejects_zero_timeout(monkeypatch):
    calls = []

    def reject_connection(address, timeout):
        calls.append((address, timeout))
        raise ValueError("Non-blocking socket (timeout=0) is not supported")

    monkeypatch.setattr(telnetlib.socket, "create_connection", reject_connection)
    client = telnetlib.Telnet()

    with pytest.raises(ValueError, match="Non-blocking"):
        client.open("terminal.example.test", port=2323, timeout=0)

    assert calls == [(('terminal.example.test', 2323), 0)]


def test_telnet_context_manager_closes_socket_but_does_not_consume_buffered_bytes():
    socket = MemoryTelnetSocket()
    client = telnetlib.Telnet()
    client.sock = socket
    client.rawq = b"pending"
    client.cookedq = b"ready"

    with client as entered:
        assert entered is client
        assert entered.get_socket() is socket

    assert socket.closed is True
    # 3.10 的 close 用假值 0 标记已经断开的 socket；
    # 因此调用方应通过真假值或 get_socket 判断连接状态，而不是依赖 None。
    assert client.sock == 0
    assert client.get_socket() == 0
    # close 只终止传输并复位 IAC 子状态；
    # 尚未读取的应用数据仍可用于故障诊断。
    assert client.rawq == b"pending"
    assert client.cookedq == b"ready"
