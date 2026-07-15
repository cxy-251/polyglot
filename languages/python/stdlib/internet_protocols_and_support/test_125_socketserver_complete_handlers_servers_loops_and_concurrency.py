"""125｜学习 socketserver 的 handler、server、事件循环、线程与进程并发。

构造处理器就会立即完成一次请求，不应把 __init__ 当作普通数据对象初始化。handle 抛出时
finish 仍执行；setup 尚未成功时则不会调用 finish，因为可清理资源还没有建立。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

from io import BytesIO
import selectors
import socket
import socketserver
from socketserver import BaseRequestHandler
from socketserver import BaseServer
from socketserver import DatagramRequestHandler
from socketserver import StreamRequestHandler
from socketserver import TCPServer
from socketserver import ThreadingMixIn
from socketserver import UDPServer

import pytest


# polyglot-covers: python.socketserver.BaseRequestHandler
# polyglot-covers: python.socketserver.BaseRequestHandler-per-request-instance
# polyglot-covers: python.socketserver.BaseRequestHandler.request
# polyglot-covers: python.socketserver.BaseRequestHandler.client_address
# polyglot-covers: python.socketserver.BaseRequestHandler.server
# polyglot-covers: python.socketserver.BaseRequestHandler.setup
# polyglot-covers: python.socketserver.BaseRequestHandler.handle
# polyglot-covers: python.socketserver.BaseRequestHandler.finish
# polyglot-covers: python.socketserver.handler-lifecycle-order
# polyglot-covers: python.socketserver.handler-finish-after-handle-error
# polyglot-covers: python.socketserver.handler-no-finish-after-setup-error




class RecordingHandler(BaseRequestHandler):
    events = []

    def setup(self):
        self.events.append(("setup", self.request))

    def handle(self):
        self.events.append(
            ("handle", self.client_address, self.server),
        )

    def finish(self):
        self.events.append(("finish", self.request))


class FailingHandleHandler(RecordingHandler):
    events = []

    def handle(self):
        self.events.append(("handle", self.request))
        raise RuntimeError("handler failed")


class FailingSetupHandler(RecordingHandler):
    events = []

    def setup(self):
        self.events.append(("setup", self.request))
        raise RuntimeError("setup failed")


def test_construction_assigns_context_and_runs_the_full_lifecycle():
    RecordingHandler.events.clear()
    request = object()
    server = object()

    handler = RecordingHandler(request, ("client.test", 9000), server)

    assert handler.request is request
    assert handler.client_address == ("client.test", 9000)
    assert handler.server is server
    assert [event[0] for event in handler.events] == [
        "setup",
        "handle",
        "finish",
    ]


def test_finish_runs_when_handle_raises_and_original_error_propagates():
    FailingHandleHandler.events.clear()

    with pytest.raises(RuntimeError, match="handler failed"):
        FailingHandleHandler("request", ("client.test", 1), object())

    assert [event[0] for event in FailingHandleHandler.events] == [
        "setup",
        "handle",
        "finish",
    ]


def test_finish_is_not_called_when_setup_itself_never_completes():
    FailingSetupHandler.events.clear()

    with pytest.raises(RuntimeError, match="setup failed"):
        FailingSetupHandler("request", ("client.test", 1), object())

    assert FailingSetupHandler.events == [("setup", "request")]

# StreamRequestHandler 的 rfile/wfile、无缓冲 SocketWriter、超时与 Nagle 配置。
#
# 默认 rfile 是缓冲二进制流，wfile 则用 sendall 实现 BufferedIOBase 写接口；write 返回完整
# 字节数而不是底层 send 的部分结果。启用缓冲输出时 finish 会 flush 并关闭两端文件对象。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.StreamRequestHandler
# polyglot-covers: python.socketserver.StreamRequestHandler.connection
# polyglot-covers: python.socketserver.StreamRequestHandler.rfile
# polyglot-covers: python.socketserver.StreamRequestHandler.wfile-bufferedio-3.6
# polyglot-covers: python.socketserver.StreamRequestHandler.rbufsize
# polyglot-covers: python.socketserver.StreamRequestHandler.wbufsize
# polyglot-covers: python.socketserver.StreamRequestHandler.timeout
# polyglot-covers: python.socketserver.StreamRequestHandler.disable_nagle_algorithm
# polyglot-covers: python.socketserver.socket-writer-sendall
# polyglot-covers: python.socketserver.socket-writer-write-byte-count
# polyglot-covers: python.socketserver.stream-handler-finish-flush-close



class RecordingBuffer(BytesIO):
    def __init__(self, initial=b""):
        super().__init__(initial)
        self.snapshot = None

    def close(self):
        if not self.closed:
            self.snapshot = self.getvalue()
        super().close()


class MemoryStreamSocket:
    def __init__(self, incoming=b"line\n"):
        self.reader = RecordingBuffer(incoming)
        self.writer = RecordingBuffer()
        self.sent = []
        self.makefile_calls = []
        self.timeout_values = []
        self.socket_options = []

    def makefile(self, mode, buffering):
        self.makefile_calls.append((mode, buffering))
        if mode == "rb":
            return self.reader
        if mode == "wb":
            return self.writer
        raise AssertionError(mode)

    def sendall(self, data):
        self.sent.append(bytes(data))

    def fileno(self):
        return 77

    def settimeout(self, value):
        self.timeout_values.append(value)

    def setsockopt(self, level, option, value):
        self.socket_options.append((level, option, value))


class UpperStreamHandler(StreamRequestHandler):
    def handle(self):
        data = self.rfile.readline()
        self.write_result = self.wfile.write(data.upper())


class BufferedConfiguredHandler(UpperStreamHandler):
    timeout = 2.5
    disable_nagle_algorithm = True
    wbufsize = 16


def test_default_writer_calls_sendall_and_reports_the_full_byte_count():
    request = MemoryStreamSocket(b"hello\n")

    handler = UpperStreamHandler(request, ("client.test", 1), object())

    assert handler.connection is request
    assert handler.write_result == len(b"HELLO\n")
    assert request.sent == [b"HELLO\n"]
    assert request.makefile_calls == [("rb", -1)]
    assert request.reader.closed


def test_configured_stream_applies_socket_options_and_flushes_buffered_output():
    request = MemoryStreamSocket(b"buffered\n")

    BufferedConfiguredHandler(request, ("client.test", 1), object())

    assert request.timeout_values == [2.5]
    assert request.socket_options == [
        (socket.IPPROTO_TCP, socket.TCP_NODELAY, True),
    ]
    assert request.makefile_calls == [("rb", -1), ("wb", 16)]
    assert request.reader.closed
    assert request.writer.closed
    assert request.writer.snapshot == b"BUFFERED\n"

# DatagramRequestHandler 的 (packet, socket) 请求形态与单报文回复。
#
# UDP 没有连接流：setup 把输入数据复制进 BytesIO rfile，另建 wfile；finish 把完整输出作为
# 一个数据报 sendto 到 client_address。它和 StreamRequestHandler 的 request 类型不同。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.DatagramRequestHandler
# polyglot-covers: python.socketserver.datagram-request-packet-socket-pair
# polyglot-covers: python.socketserver.DatagramRequestHandler.packet
# polyglot-covers: python.socketserver.DatagramRequestHandler.socket
# polyglot-covers: python.socketserver.datagram-handler-rfile-bytesio
# polyglot-covers: python.socketserver.datagram-handler-wfile-bytesio
# polyglot-covers: python.socketserver.datagram-handler-finish-sendto
# polyglot-covers: python.socketserver.datagram-reply-client-address



class HandlerDatagramSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, data, address):
        self.sent.append((bytes(data), address))


class UpperDatagramHandler(DatagramRequestHandler):
    def handle(self):
        assert isinstance(self.rfile, BytesIO)
        assert isinstance(self.wfile, BytesIO)
        self.wfile.write(self.rfile.read().upper())


def test_datagram_handler_buffers_one_packet_and_sends_one_addressed_reply():
    transport = HandlerDatagramSocket()
    request = (b"hello datagram", transport)
    client = ("192.0.2.110", 9000)

    handler = UpperDatagramHandler(request, client, object())

    assert handler.request == request
    assert handler.packet == b"hello datagram"
    assert handler.socket is transport
    assert transport.sent == [(b"HELLO DATAGRAM", client)]

# BaseServer 的地址/处理器配置、同步 process_request、finish_request 与上下文管理。
#
# 默认 process_request 同步实例化处理器，然后 shutdown_request；finish_request 的“调用
# 构造器”会连带执行完整 handler 生命周期。with 退出只调用 server_close，不会自行 shutdown。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.BaseServer
# polyglot-covers: python.socketserver.BaseServer.server_address
# polyglot-covers: python.socketserver.BaseServer.RequestHandlerClass
# polyglot-covers: python.socketserver.BaseServer.process_request
# polyglot-covers: python.socketserver.BaseServer.finish_request
# polyglot-covers: python.socketserver.BaseServer.shutdown_request
# polyglot-covers: python.socketserver.BaseServer.close_request
# polyglot-covers: python.socketserver.BaseServer.verify_request-default-true
# polyglot-covers: python.socketserver.BaseServer-context-manager-3.6
# polyglot-covers: python.socketserver.BaseServer.__enter__
# polyglot-covers: python.socketserver.BaseServer.__exit__-server-close



class RecordingRequestHandler(BaseRequestHandler):
    calls = []

    def handle(self):
        self.calls.append((self.request, self.client_address, self.server))


class RecordingServer(BaseServer):
    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.events = []

    def close_request(self, request):
        self.events.append(("close_request", request))

    def server_close(self):
        self.events.append(("server_close",))


def test_process_request_constructs_handler_then_closes_request_synchronously():
    RecordingRequestHandler.calls.clear()
    server = RecordingServer(("memory.test", 8000), RecordingRequestHandler)
    request = object()
    client = ("client.test", 9000)

    server.process_request(request, client)

    assert server.server_address == ("memory.test", 8000)
    assert server.RequestHandlerClass is RecordingRequestHandler
    assert RecordingRequestHandler.calls == [(request, client, server)]
    assert server.events == [("close_request", request)]
    assert server.verify_request(request, client) is True


def test_context_manager_returns_server_and_closes_it_on_exit():
    server = RecordingServer(("memory.test", 8000), RecordingRequestHandler)

    with server as entered:
        assert entered is server
        assert server.events == []

    assert server.events == [("server_close",)]

# BaseServer 的非阻塞单请求管线、verify_request 拒绝与异常清理。
#
# 选择器确认可读后，内部管线按 get→verify→process 运行。拒绝请求会直接 shutdown；
# process 的 Exception 交给 handle_error 后清理，BaseException 则只清理并继续向外传播。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.BaseServer._handle_request_noblock
# polyglot-covers: python.socketserver.BaseServer.get_request
# polyglot-covers: python.socketserver.BaseServer.verify_request
# polyglot-covers: python.socketserver.BaseServer.handle_error
# polyglot-covers: python.socketserver.nonblocking-request-pipeline-order
# polyglot-covers: python.socketserver.verify-false-shutdowns-request
# polyglot-covers: python.socketserver.get-request-oserror-is-ignored
# polyglot-covers: python.socketserver.process-exception-handle-error-then-shutdown
# polyglot-covers: python.socketserver.process-baseexception-shutdown-reraise




class PipelineServer(BaseServer):
    def __init__(self, *, verified=True, failure=None):
        super().__init__(("memory.test", 0), object)
        self.verified = verified
        self.failure = failure
        self.events = []
        self.request = object()
        self.client = ("client.test", 9000)

    def get_request(self):
        self.events.append("get")
        if self.failure == "get":
            raise OSError("unavailable")
        return self.request, self.client

    def verify_request(self, request, client_address):
        self.events.append("verify")
        return self.verified

    def process_request(self, request, client_address):
        self.events.append("process")
        if self.failure == "exception":
            raise RuntimeError("failed")
        if self.failure == "baseexception":
            raise KeyboardInterrupt()

    def handle_error(self, request, client_address):
        self.events.append("error")

    def shutdown_request(self, request):
        self.events.append("shutdown")


def test_verified_request_reaches_process_without_extra_framework_cleanup():
    server = PipelineServer()

    server._handle_request_noblock()

    # 成功路径是否清理由 process_request 的具体实现负责；BaseServer 默认实现会处理。
    assert server.events == ["get", "verify", "process"]


def test_rejected_and_unavailable_requests_stop_at_their_respective_boundaries():
    rejected = PipelineServer(verified=False)
    unavailable = PipelineServer(failure="get")

    rejected._handle_request_noblock()
    unavailable._handle_request_noblock()

    assert rejected.events == ["get", "verify", "shutdown"]
    assert unavailable.events == ["get"]


def test_exception_is_reported_then_shutdown_but_baseexception_is_reraised():
    failed = PipelineServer(failure="exception")
    interrupted = PipelineServer(failure="baseexception")

    failed._handle_request_noblock()
    with pytest.raises(KeyboardInterrupt):
        interrupted._handle_request_noblock()

    assert failed.events == ["get", "verify", "process", "error", "shutdown"]
    assert interrupted.events == ["get", "verify", "process", "shutdown"]

# TCPServer 的绑定/监听/接受委派、选择器接口与半关闭清理。
#
# TCPServer 把 socket 生命周期拆成可覆盖钩子。allow_reuse_address 只影响 bind 前的选项；
# shutdown_request 即使 SHUT_WR 失败仍会 close，避免把“未连接”异常变成资源泄漏。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.TCPServer
# polyglot-covers: python.socketserver.TCPServer.address_family
# polyglot-covers: python.socketserver.TCPServer.socket_type
# polyglot-covers: python.socketserver.TCPServer.allow_reuse_address
# polyglot-covers: python.socketserver.TCPServer.server_bind
# polyglot-covers: python.socketserver.TCPServer.server_activate
# polyglot-covers: python.socketserver.TCPServer.get_request
# polyglot-covers: python.socketserver.TCPServer.fileno
# polyglot-covers: python.socketserver.TCPServer.server_close
# polyglot-covers: python.socketserver.TCPServer.shutdown_request
# polyglot-covers: python.socketserver.tcp-shutdown-error-still-closes



class MemoryListeningSocket:
    def __init__(self):
        self.events = []
        self.accepted = (object(), ("client.test", 9000))

    def setsockopt(self, level, option, value):
        self.events.append(("setsockopt", level, option, value))

    def bind(self, address):
        self.events.append(("bind", address))

    def getsockname(self):
        return ("127.0.0.1", 8123)

    def listen(self, backlog):
        self.events.append(("listen", backlog))

    def accept(self):
        self.events.append(("accept",))
        return self.accepted

    def fileno(self):
        return 88

    def close(self):
        self.events.append(("close",))


class MemoryClientSocket:
    def __init__(self):
        self.events = []

    def shutdown(self, how):
        self.events.append(("shutdown", how))
        raise OSError("not connected")

    def close(self):
        self.events.append(("close",))


def make_server():
    server = object.__new__(TCPServer)
    server.socket = MemoryListeningSocket()
    server.server_address = ("127.0.0.1", 0)
    server.allow_reuse_address = True
    server.request_queue_size = 7
    return server


def test_tcp_bind_activate_accept_fileno_and_close_delegate_to_socket():
    server = make_server()

    server.server_bind()
    server.server_activate()
    accepted = server.get_request()
    descriptor = server.fileno()
    server.server_close()

    assert TCPServer.address_family == socket.AF_INET
    assert TCPServer.socket_type == socket.SOCK_STREAM
    assert TCPServer.allow_reuse_address is False
    assert server.server_address == ("127.0.0.1", 8123)
    assert accepted == server.socket.accepted
    assert descriptor == 88
    assert server.socket.events == [
        ("setsockopt", socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
        ("bind", ("127.0.0.1", 0)),
        ("listen", 7),
        ("accept",),
        ("close",),
    ]


def test_shutdown_request_closes_even_when_half_close_reports_oserror():
    server = make_server()
    request = MemoryClientSocket()

    server.shutdown_request(request)

    assert request.events == [
        ("shutdown", socket.SHUT_WR),
        ("close",),
    ]

# UDPServer 的报文接收形态、无监听激活与无连接清理。
#
# UDPServer 复用 TCPServer 的大部分框架，却把 socket_type 改为 SOCK_DGRAM。get_request
# 返回 ((data, server_socket), client_address)；没有 listen、半关闭或逐请求 socket 可清理。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.UDPServer
# polyglot-covers: python.socketserver.UDPServer-inherits-TCPServer
# polyglot-covers: python.socketserver.UDPServer.socket_type
# polyglot-covers: python.socketserver.UDPServer.max_packet_size
# polyglot-covers: python.socketserver.UDPServer.get_request
# polyglot-covers: python.socketserver.udp-get-request-packet-socket-pair
# polyglot-covers: python.socketserver.UDPServer.server_activate-no-listen
# polyglot-covers: python.socketserver.UDPServer.shutdown_request-noop-close
# polyglot-covers: python.socketserver.UDPServer.close_request-noop



class ServerDatagramSocket:
    def __init__(self):
        self.events = []

    def recvfrom(self, size):
        self.events.append(("recvfrom", size))
        return b"packet", ("client.test", 9000)

    def listen(self, backlog):
        self.events.append(("listen", backlog))

    def close(self):
        self.events.append(("close",))


def test_udp_get_request_preserves_server_socket_for_handler_reply():
    server = object.__new__(UDPServer)
    server.socket = ServerDatagramSocket()
    server.max_packet_size = 4096

    request, client = server.get_request()

    assert issubclass(UDPServer, TCPServer)
    assert UDPServer.socket_type == socket.SOCK_DGRAM
    assert UDPServer.max_packet_size == 8192
    assert request == (b"packet", server.socket)
    assert client == ("client.test", 9000)
    assert server.socket.events == [("recvfrom", 4096)]


def test_udp_activation_and_per_request_cleanup_do_not_touch_socket():
    server = object.__new__(UDPServer)
    server.socket = ServerDatagramSocket()
    request = (b"packet", server.socket)

    server.server_activate()
    server.shutdown_request(request)
    server.close_request(request)

    assert server.socket.events == []

# ThreadingMixIn 的线程分派、守护标志、错误清理与 server_close 等待。
#
# ThreadingMixIn 必须放在同步服务器类之前才能覆盖 process_request。非守护线程默认会被
# 跟踪，并在 server_close 时 join；无论 handler 成败，线程入口最终都 shutdown_request。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.ThreadingMixIn
# polyglot-covers: python.socketserver.ThreadingMixIn-first-in-mro
# polyglot-covers: python.socketserver.ThreadingMixIn.process_request
# polyglot-covers: python.socketserver.ThreadingMixIn.process_request_thread
# polyglot-covers: python.socketserver.ThreadingMixIn.daemon_threads
# polyglot-covers: python.socketserver.ThreadingMixIn.block_on_close-3.7
# polyglot-covers: python.socketserver.threading-mixin-finish-then-shutdown
# polyglot-covers: python.socketserver.threading-mixin-error-then-shutdown
# polyglot-covers: python.socketserver.threading-mixin-server-close-joins
# polyglot-covers: python.socketserver.threading-mixin-daemon-not-tracked



class FakeThread:
    instances = []

    def __init__(self, target, args):
        self.target = target
        self.args = args
        self.daemon = False
        self.started = False
        self.alive = False
        self.joined = False
        self.instances.append(self)

    def start(self):
        self.started = True
        self.alive = True
        try:
            self.target(*self.args)
        finally:
            self.alive = False

    def is_alive(self):
        return self.alive

    def join(self):
        self.joined = True


class MemoryThreadedServer(ThreadingMixIn, BaseServer):
    def __init__(self, *, fail=False):
        BaseServer.__init__(self, ("memory.test", 0), object)
        self.fail = fail
        self.events = []

    def finish_request(self, request, client_address):
        self.events.append("finish")
        if self.fail:
            raise RuntimeError("handler failed")

    def handle_error(self, request, client_address):
        self.events.append("error")

    def shutdown_request(self, request):
        self.events.append("shutdown")


def test_thread_dispatch_runs_handler_then_cleanup_and_close_joins(monkeypatch):
    FakeThread.instances.clear()
    monkeypatch.setattr(socketserver.threading, "Thread", FakeThread)
    server = MemoryThreadedServer()

    server.process_request("request", ("client.test", 1))

    [thread] = FakeThread.instances
    assert thread.started
    assert thread.daemon is False
    assert server.events == ["finish", "shutdown"]

    server.server_close()

    assert thread.joined


def test_thread_entry_reports_exception_and_still_shutdowns(monkeypatch):
    FakeThread.instances.clear()
    monkeypatch.setattr(socketserver.threading, "Thread", FakeThread)
    server = MemoryThreadedServer(fail=True)

    server.process_request("request", ("client.test", 1))

    assert server.events == ["finish", "error", "shutdown"]


def test_daemon_thread_is_not_retained_for_server_close_join(monkeypatch):
    FakeThread.instances.clear()
    monkeypatch.setattr(socketserver.threading, "Thread", FakeThread)
    server = MemoryThreadedServer()
    server.daemon_threads = True

    server.process_request("request", ("client.test", 1))
    server.server_close()

    [thread] = FakeThread.instances
    assert thread.daemon is True
    assert not thread.joined

# BaseServer.serve_forever 的选择器轮询、service_actions 与退出状态复位。
#
# serve_forever 使用 poll_interval 而忽略 server.timeout，每轮即使没有请求也调用
# service_actions。退出时会复位 shutdown 标志并通知等待者；shutdown 必须由另一线程调用。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.BaseServer.serve_forever
# polyglot-covers: python.socketserver.serve-forever-selector
# polyglot-covers: python.socketserver.serve-forever-poll-interval
# polyglot-covers: python.socketserver.serve-forever-ignores-timeout
# polyglot-covers: python.socketserver.BaseServer.service_actions-3.3
# polyglot-covers: python.socketserver.service-actions-without-ready-request
# polyglot-covers: python.socketserver.serve-forever-shutdown-flag-reset
# polyglot-covers: python.socketserver.BaseServer.shutdown-other-thread-required



class FakeSelector:
    next_ready = []
    instances = []

    def __init__(self):
        self.registered = []
        self.timeouts = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def register(self, fileobj, events):
        self.registered.append((fileobj, events))

    def select(self, timeout):
        self.timeouts.append(timeout)
        return list(self.next_ready)


class LoopServer(BaseServer):
    def __init__(self):
        super().__init__(("memory.test", 0), object)
        self.timeout = 999
        self.events = []

    def _handle_request_noblock(self):
        self.events.append("request")

    def service_actions(self):
        self.events.append("service")
        self._BaseServer__shutdown_request = True


def run_one_iteration(monkeypatch, ready):
    FakeSelector.instances.clear()
    FakeSelector.next_ready = ready
    monkeypatch.setattr(socketserver, "_ServerSelector", FakeSelector)
    server = LoopServer()

    server.serve_forever(poll_interval=0.125)

    return server, FakeSelector.instances[0]


def test_ready_iteration_handles_request_then_runs_service_actions(monkeypatch):
    server, selector = run_one_iteration(monkeypatch, [object()])

    assert server.events == ["request", "service"]
    assert selector.registered == [(server, selectors.EVENT_READ)]
    assert selector.timeouts == [0.125]
    assert server._BaseServer__shutdown_request is False
    assert server._BaseServer__is_shut_down.is_set()


def test_service_actions_runs_even_when_no_descriptor_is_ready(monkeypatch):
    server, selector = run_one_iteration(monkeypatch, [])

    assert server.events == ["service"]
    assert selector.timeouts == [0.125]

# BaseServer.handle_request 的一次性选择、socket/server 超时合并与提前唤醒。
#
# handle_request 取 socket 超时与 server.timeout 的较小值。选择器无事件却提前返回时会按
# 截止时间重算剩余时间，而不是立即调用 handle_timeout；真正到期才执行超时钩子。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.BaseServer.handle_request
# polyglot-covers: python.socketserver.BaseServer.timeout
# polyglot-covers: python.socketserver.handle-request-socket-timeout-minimum
# polyglot-covers: python.socketserver.handle-request-selector
# polyglot-covers: python.socketserver.handle-request-early-wakeup-retry
# polyglot-covers: python.socketserver.BaseServer.handle_timeout
# polyglot-covers: python.socketserver.handle-request-ready-dispatch



class TimeoutSocket:
    def __init__(self, timeout):
        self.timeout = timeout

    def gettimeout(self):
        return self.timeout


class SequenceSelector:
    results = []
    instances = []

    def __init__(self):
        self.timeouts = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def register(self, fileobj, events):
        pass

    def select(self, timeout):
        self.timeouts.append(timeout)
        return self.results.pop(0)


class OneRequestServer(BaseServer):
    def __init__(self, socket_timeout, server_timeout):
        super().__init__(("memory.test", 0), object)
        self.socket = TimeoutSocket(socket_timeout)
        self.timeout = server_timeout
        self.events = []

    def _handle_request_noblock(self):
        self.events.append("request")

    def handle_timeout(self):
        self.events.append("timeout")


def install_selector(monkeypatch, results):
    SequenceSelector.instances.clear()
    SequenceSelector.results = list(results)
    monkeypatch.setattr(socketserver, "_ServerSelector", SequenceSelector)


def test_ready_descriptor_dispatches_one_request_without_timeout(monkeypatch):
    install_selector(monkeypatch, [[object()]])
    server = OneRequestServer(None, None)

    server.handle_request()

    assert server.events == ["request"]
    assert SequenceSelector.instances[0].timeouts == [None]


def test_early_empty_wakeup_recomputes_deadline_then_calls_timeout(
    monkeypatch,
):
    install_selector(monkeypatch, [[], []])
    times = iter((10.0, 11.0, 13.0))
    monkeypatch.setattr(socketserver, "time", lambda: next(times))
    server = OneRequestServer(socket_timeout=5.0, server_timeout=2.0)

    server.handle_request()

    assert server.events == ["timeout"]
    assert SequenceSelector.instances[0].timeouts == [2.0, 1.0]

# ForkingMixIn 父进程路径、子进程收集钩子与预组合服务器类。
#
# POSIX 上 fork 父进程只记录子 PID 并关闭自己的请求副本，实际处理发生在子进程；
# service_actions/超时负责回收。mixin 必须位于 TCPServer/UDPServer 前才能覆盖同步方法。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.socketserver.ForkingMixIn
# polyglot-covers: python.socketserver.ForkingMixIn.max_children
# polyglot-covers: python.socketserver.ForkingMixIn.block_on_close-3.7
# polyglot-covers: python.socketserver.forking-parent-records-child
# polyglot-covers: python.socketserver.forking-parent-closes-request-copy
# polyglot-covers: python.socketserver.forking-service-actions-collect-children
# polyglot-covers: python.socketserver.forking-server-close-blocking-policy
# polyglot-covers: python.socketserver.ThreadingTCPServer
# polyglot-covers: python.socketserver.ThreadingUDPServer
# polyglot-covers: python.socketserver.ForkingTCPServer
# polyglot-covers: python.socketserver.ForkingUDPServer
# polyglot-covers: python.socketserver.UnixStreamServer
# polyglot-covers: python.socketserver.UnixDatagramServer




def test_prebuilt_threading_and_platform_server_classes_have_mixin_first():
    assert socketserver.ThreadingTCPServer.__mro__[:3] == (
        socketserver.ThreadingTCPServer,
        ThreadingMixIn,
        TCPServer,
    )
    assert socketserver.ThreadingUDPServer.__mro__[:3] == (
        socketserver.ThreadingUDPServer,
        ThreadingMixIn,
        UDPServer,
    )

    if hasattr(socketserver, "UnixStreamServer"):
        assert socketserver.UnixStreamServer.address_family == socket.AF_UNIX
        assert issubclass(socketserver.UnixStreamServer, TCPServer)
        assert issubclass(socketserver.UnixDatagramServer, UDPServer)


@pytest.mark.skipif(
    not hasattr(socketserver, "ForkingMixIn"),
    reason="forking servers require POSIX os.fork",
)
def test_forking_parent_records_pid_closes_copy_and_collects_on_close(monkeypatch):
    ForkingMixIn = socketserver.ForkingMixIn

    class MemoryForkingServer(ForkingMixIn, BaseServer):
        def __init__(self):
            BaseServer.__init__(self, ("memory.test", 0), object)
            self.events = []

        def close_request(self, request):
            self.events.append(("close", request))

        def collect_children(self, *, blocking=False):
            self.events.append(("collect", blocking))

    server = MemoryForkingServer()
    monkeypatch.setattr(socketserver.os, "fork", lambda: 4321)

    server.process_request("request", ("client.test", 1))

    assert server.active_children == {4321}
    assert server.events == [("close", "request")]

    server.service_actions()
    server.server_close()

    assert server.events[-2:] == [
        ("collect", False),
        ("collect", True),
    ]
    assert ForkingMixIn.max_children == 40
    assert ForkingMixIn.block_on_close is True

    assert socketserver.ForkingTCPServer.__mro__[1] is ForkingMixIn
    assert socketserver.ForkingUDPServer.__mro__[1] is ForkingMixIn
