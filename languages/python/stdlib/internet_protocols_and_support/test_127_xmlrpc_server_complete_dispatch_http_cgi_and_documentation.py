"""127｜SimpleXMLRPCDispatcher 的函数注册、线路分派、覆盖回调与 Fault 转换。

register_function 支持直接调用和装饰器命名；_marshaled_dispatch 完成 loads→调用→dumps。
未知方法、普通异常和显式 Fault 都返回 XML-RPC fault 包，而不是让 Python 异常逃到 HTTP 层。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCDispatcher
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCDispatcher.register_function
# polyglot-covers: python.xmlrpc.server.register-function-default-name
# polyglot-covers: python.xmlrpc.server.register-function-explicit-name
# polyglot-covers: python.xmlrpc.server.register-function-decorator
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCDispatcher._marshaled_dispatch
# polyglot-covers: python.xmlrpc.server.marshaled-dispatch-custom-callback
# polyglot-covers: python.xmlrpc.server.unknown-method-fault
# polyglot-covers: python.xmlrpc.server.function-exception-fault
# polyglot-covers: python.xmlrpc.server.explicit-fault-preserved

import socketserver
import sys
from email.message import Message
from io import BytesIO, StringIO
from xmlrpc.client import Fault, dumps, gzip_decode, gzip_encode, loads
from xmlrpc.server import (
    CGIXMLRPCRequestHandler,
    DocCGIXMLRPCRequestHandler,
    DocXMLRPCRequestHandler,
    DocXMLRPCServer,
    MultiPathXMLRPCServer,
    SimpleXMLRPCDispatcher,
    SimpleXMLRPCRequestHandler,
    SimpleXMLRPCServer,
    XMLRPCDocGenerator,
)

import pytest


def wire_call(dispatcher, method, *params, dispatch_method=None):
    request = dumps(params, methodname=method).encode("utf-8")
    response = dispatcher._marshaled_dispatch(
        request,
        dispatch_method=dispatch_method,
    )
    values, response_method = loads(response)
    assert response_method is None
    return values[0]


def test_functions_can_use_python_name_explicit_name_and_decorator_form():
    dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None)

    def add(left, right):
        return left + right

    registered = dispatcher.register_function(add)

    @dispatcher.register_function(name="math.subtract")
    def subtract(left, right):
        return left - right

    assert registered is add
    assert wire_call(dispatcher, "add", 2, 3) == 5
    assert wire_call(dispatcher, "math.subtract", 7, 4) == 3
    assert subtract(7, 4) == 3


def test_per_request_dispatch_callback_can_override_registered_lookup():
    dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None)

    def route(method, params):
        return {"method": method, "params": list(params)}

    result = wire_call(
        dispatcher,
        "virtual.echo",
        "value",
        dispatch_method=route,
    )

    assert result == {"method": "virtual.echo", "params": ["value"]}


def test_unknown_method_and_python_exception_become_fault_responses():
    dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None)

    def fail():
        raise ValueError("bad lesson")

    dispatcher.register_function(fail)

    with pytest.raises(Fault) as missing:
        wire_call(dispatcher, "missing")
    assert missing.value.faultCode == 1
    assert "method \"missing\" is not supported" in missing.value.faultString

    with pytest.raises(Fault) as failed:
        wire_call(dispatcher, "fail")
    assert failed.value.faultCode == 1
    assert "ValueError:bad lesson" in failed.value.faultString


def test_explicit_fault_keeps_application_code_and_message():
    dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None)

    def reject():
        raise Fault(403, "not allowed")

    dispatcher.register_function(reject)

    with pytest.raises(Fault) as raised:
        wire_call(dispatcher, "reject")

    assert raised.value.faultCode == 403
    assert raised.value.faultString == "not allowed"


# register_instance 的直接/自定义分派、点分名称开关、优先级与私有属性保护。
#
# 注册函数优先于实例同名方法。默认只暴露实例的顶层公开方法；allow_dotted_names=True 才
# 沿属性链解析，但任何以下划线开头的段仍拒绝。点分开放给不可信实例可能暴露全局对象。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCDispatcher.register_instance
# polyglot-covers: python.xmlrpc.server.register-instance-public-method
# polyglot-covers: python.xmlrpc.server.register-instance-allow_dotted_names
# polyglot-covers: python.xmlrpc.server.dotted-names-disabled-default
# polyglot-covers: python.xmlrpc.server.dotted-name-resolution
# polyglot-covers: python.xmlrpc.server.dotted-private-segment-rejected
# polyglot-covers: python.xmlrpc.server.registered-function-precedes-instance
# polyglot-covers: python.xmlrpc.server.instance-custom-_dispatch
# polyglot-covers: python.xmlrpc.server.allow-dotted-names-security-risk


class AdminAPI:
    def echo(self, value):
        return f"admin:{value}"

    def _secret(self):
        return "must not be exposed"


class LessonAPI:
    def __init__(self):
        self.admin = AdminAPI()

    def ping(self):
        return "instance pong"


class CustomDispatchAPI:
    def __init__(self):
        self.calls = []

    def _dispatch(self, method, params):
        self.calls.append((method, params))
        return f"custom:{method}:{len(params)}"


def call_instance_dispatcher(dispatcher, method, *params):
    request = dumps(params, methodname=method)
    response = dispatcher._marshaled_dispatch(request)
    values, _ = loads(response)
    return values[0]


def test_default_instance_exposes_top_level_method_but_not_dotted_path():
    dispatcher = SimpleXMLRPCDispatcher(False, None)
    dispatcher.register_instance(LessonAPI())

    assert call_instance_dispatcher(dispatcher, "ping") == "instance pong"
    with pytest.raises(Fault):
        call_instance_dispatcher(dispatcher, "admin.echo", "hello")


def test_opted_in_dotted_resolution_still_rejects_private_segments():
    dispatcher = SimpleXMLRPCDispatcher(False, None)
    dispatcher.register_instance(LessonAPI(), allow_dotted_names=True)

    assert call_instance_dispatcher(dispatcher, "admin.echo", "hello") == "admin:hello"
    with pytest.raises(Fault):
        call_instance_dispatcher(dispatcher, "admin._secret")


def test_registered_function_takes_precedence_over_instance_method():
    dispatcher = SimpleXMLRPCDispatcher(False, None)
    dispatcher.register_instance(LessonAPI())
    dispatcher.register_function(lambda: "function pong", "ping")

    assert call_instance_dispatcher(dispatcher, "ping") == "function pong"


def test_instance_dispatch_hook_receives_unresolved_name_and_parameter_tuple():
    dispatcher = SimpleXMLRPCDispatcher(False, None)
    instance = CustomDispatchAPI()
    dispatcher.register_instance(instance)

    result = call_instance_dispatcher(dispatcher, "anything.nested", 1, 2)

    assert result == "custom:anything.nested:2"
    assert instance.calls == [("anything.nested", (1, 2))]


# 服务端 introspection API、帮助/签名回退与 system.multicall 的逐项隔离。
#
# introspection 和 multicall 都要显式注册。listMethods 包含系统方法并排序；Python 实现不
# 声明 XML-RPC 签名时返回说明字符串。批处理中单项失败变 fault dict，其他调用仍可成功。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.register_introspection_functions
# polyglot-covers: python.xmlrpc.server.system.listMethods
# polyglot-covers: python.xmlrpc.server.system.methodHelp
# polyglot-covers: python.xmlrpc.server.system.methodSignature
# polyglot-covers: python.xmlrpc.server.introspection-methods-explicit-opt-in
# polyglot-covers: python.xmlrpc.server.register_multicall_functions
# polyglot-covers: python.xmlrpc.server.system.multicall
# polyglot-covers: python.xmlrpc.server.multicall-success-singleton-list
# polyglot-covers: python.xmlrpc.server.multicall-failure-fault-dict
# polyglot-covers: python.xmlrpc.server.multicall-recursion-rejected


def call_introspection_dispatcher(dispatcher, method, *params):
    request = dumps(params, methodname=method)
    response = dispatcher._marshaled_dispatch(request)
    values, _ = loads(response)
    return values[0]


def make_introspection_dispatcher():
    dispatcher = SimpleXMLRPCDispatcher(False, None)

    def add(left, right):
        """返回两个数字之和。"""
        return left + right

    def fail():
        raise ValueError("planned failure")

    dispatcher.register_function(add)
    dispatcher.register_function(fail)
    dispatcher.register_introspection_functions()
    dispatcher.register_multicall_functions()
    return dispatcher


def test_introspection_lists_methods_and_exposes_docstring_with_signature_fallback():
    dispatcher = make_introspection_dispatcher()

    methods = call_introspection_dispatcher(dispatcher, "system.listMethods")

    assert methods == sorted(methods)
    assert "add" in methods
    assert "system.listMethods" in methods
    assert "system.multicall" in methods
    assert call_introspection_dispatcher(dispatcher, "system.methodHelp", "add") == "返回两个数字之和。"
    assert call_introspection_dispatcher(dispatcher, "system.methodHelp", "missing") == ""
    assert call_introspection_dispatcher(dispatcher, "system.methodSignature", "add") == (
        "signatures not supported"
    )


def test_multicall_keeps_successes_and_faults_in_corresponding_result_slots():
    dispatcher = make_introspection_dispatcher()
    calls = [
        {"methodName": "add", "params": [2, 3]},
        {"methodName": "fail", "params": []},
        {"methodName": "missing", "params": []},
        {"methodName": "system.multicall", "params": [[]]},
    ]

    results = call_introspection_dispatcher(dispatcher, "system.multicall", calls)

    assert results[0] == [5]
    assert results[1]["faultCode"] == 1
    assert "ValueError:planned failure" in results[1]["faultString"]
    assert results[2]["faultCode"] == 1
    assert "not supported" in results[2]["faultString"]
    assert results[3]["faultCode"] == 1
    assert "recursive" in results[3]["faultString"].lower()


# SimpleXMLRPCServer 构造参数传递、延迟绑定，以及请求路径/Accept-Encoding 解析。
#
# bind_and_activate=False 允许绑定前调整服务器属性。处理器默认只接收 / 与 /RPC2；
# Accept-Encoding 的 q 值会转为 float，响应压缩只应在 gzip 权重大于零时考虑。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCServer
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCServer-is-TCPServer
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCServer-logRequests
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCServer-allow_none-encoding
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCServer-use_builtin_types-3.3
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCServer-bind_and_activate
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCRequestHandler.rpc_paths
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCRequestHandler.is_rpc_path_valid
# polyglot-covers: python.xmlrpc.server.empty-rpc-paths-allow-all
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCRequestHandler.accept_encodings
# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCRequestHandler.encode_threshold


class AllPathsHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ()


def bare_handler(handler_type, path, accept_encoding=""):
    handler = object.__new__(handler_type)
    handler.path = path
    handler.headers = Message()
    if accept_encoding:
        handler.headers["Accept-Encoding"] = accept_encoding
    return handler


def test_server_constructor_forwards_address_handler_and_delayed_bind(monkeypatch):
    received = []

    def fake_tcp_init(self, address, handler, bind_and_activate=True):
        self.server_address = address
        self.RequestHandlerClass = handler
        received.append((address, handler, bind_and_activate))

    monkeypatch.setattr(socketserver.TCPServer, "__init__", fake_tcp_init)

    server = SimpleXMLRPCServer(
        ("127.0.0.1", 0),
        requestHandler=AllPathsHandler,
        logRequests=False,
        allow_none=True,
        encoding="utf-8",
        bind_and_activate=False,
        use_builtin_types=True,
    )

    assert isinstance(server, socketserver.TCPServer)
    assert received == [(("127.0.0.1", 0), AllPathsHandler, False)]
    assert server.logRequests is False
    assert server.allow_none is True
    assert server.encoding == "utf-8"
    assert server.use_builtin_types is True


def test_default_paths_are_exact_but_empty_path_policy_accepts_everything():
    assert SimpleXMLRPCRequestHandler.rpc_paths == ("/", "/RPC2")
    assert bare_handler(SimpleXMLRPCRequestHandler, "/").is_rpc_path_valid()
    assert bare_handler(SimpleXMLRPCRequestHandler, "/RPC2").is_rpc_path_valid()
    assert not bare_handler(
        SimpleXMLRPCRequestHandler,
        "/rpc2",
    ).is_rpc_path_valid()
    assert bare_handler(AllPathsHandler, "/tenant/custom").is_rpc_path_valid()


def test_accept_encoding_parser_preserves_weights_for_compression_choice():
    handler = bare_handler(
        SimpleXMLRPCRequestHandler,
        "/RPC2",
        "br;q=0.4, gzip; q=1.0, identity;q=0",
    )

    assert handler.accept_encodings() == {
        "br": 0.4,
        "gzip": 1.0,
        "identity": 0.0,
    }
    assert SimpleXMLRPCRequestHandler.encode_threshold == 1400


# SimpleXMLRPCRequestHandler.do_POST 的 HTTP 200 调用/Fault 与路径 404。
#
# 合法 RPC 即使方法不存在或 XML 解析失败，也用 HTTP 200 携带 XML-RPC Fault；路径不在
# rpc_paths 才是 HTTP 404。应用故障与传输故障分层，是客户端 Fault/ProtocolError 的来源。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.SimpleXMLRPCRequestHandler.do_POST
# polyglot-covers: python.xmlrpc.server.http-post-content-length-read
# polyglot-covers: python.xmlrpc.server.http-post-marshaled-dispatch
# polyglot-covers: python.xmlrpc.server.http-success-text-xml-response
# polyglot-covers: python.xmlrpc.server.rpc-fault-still-http-200
# polyglot-covers: python.xmlrpc.server.malformed-xml-becomes-rpc-fault
# polyglot-covers: python.xmlrpc.server.invalid-rpc-path-http-404
# polyglot-covers: python.xmlrpc.server.report-404-no-such-page
# polyglot-covers: python.xmlrpc.server.logRequests-false


class MemoryRequestHandler(SimpleXMLRPCRequestHandler):
    protocol_version = "HTTP/1.1"
    encode_threshold = None

    def __init__(self, server, path, body):
        self.server = server
        self.path = path
        self.command = "POST"
        self.request_version = "HTTP/1.1"
        self.requestline = f"POST {path} HTTP/1.1"
        self.headers = Message()
        self.headers["Content-Length"] = str(len(body))
        self.rfile = BytesIO(body)
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.120", 1234)
        self.close_connection = False

    def log_message(self, format, *args):
        pass


def make_http_dispatcher():
    dispatcher = SimpleXMLRPCDispatcher(False, None)
    dispatcher.logRequests = False
    dispatcher.register_function(lambda left, right: left + right, "add")
    return dispatcher


def split_http_response(handler):
    return handler.wfile.getvalue().split(b"\r\n\r\n", 1)


def test_valid_post_returns_xml_response_with_result_and_exact_length():
    request = dumps((2, 3), methodname="add").encode()
    handler = MemoryRequestHandler(make_http_dispatcher(), "/RPC2", request)

    handler.do_POST()

    head, body = split_http_response(handler)
    params, method = loads(body)
    assert head.startswith(b"HTTP/1.1 200 OK\r\n")
    assert b"Content-type: text/xml\r\n" in head
    assert f"Content-length: {len(body)}".encode() in head
    assert (params, method) == ((5,), None)


def test_unknown_method_and_malformed_xml_are_rpc_faults_inside_http_200():
    cases = [
        dumps((), methodname="missing").encode(),
        b"<methodCall><broken>",
    ]

    for request in cases:
        handler = MemoryRequestHandler(make_http_dispatcher(), "/RPC2", request)
        handler.do_POST()
        head, body = split_http_response(handler)

        assert head.startswith(b"HTTP/1.1 200 OK\r\n")
        with pytest.raises(Fault):
            loads(body)


def test_unregistered_http_path_returns_plain_404_without_dispatch():
    request = dumps((2, 3), methodname="add").encode()
    handler = MemoryRequestHandler(make_http_dispatcher(), "/not-rpc", request)

    handler.do_POST()

    head, body = split_http_response(handler)
    assert head.startswith(b"HTTP/1.1 404 Not Found\r\n")
    assert b"Content-type: text/plain\r\n" in head
    assert body == b"No such page"
    assert handler.rfile.tell() == 0


# XML-RPC HTTP 处理器的 gzip 请求解码、响应协商与内容编码错误。
#
# 请求 Content-Encoding=gzip 会先解压再分派；响应只有超过阈值且客户端接受 gzip 才压缩。
# 损坏 gzip 映射 400，未知编码映射 501，二者都返回长度为零的 HTTP 错误而非 RPC Fault。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.decode_request_content
# polyglot-covers: python.xmlrpc.server.gzip-request-decoding
# polyglot-covers: python.xmlrpc.server.gzip-response-accept-encoding
# polyglot-covers: python.xmlrpc.server.gzip-response-threshold
# polyglot-covers: python.xmlrpc.server.gzip-response-content-encoding
# polyglot-covers: python.xmlrpc.server.invalid-gzip-http-400
# polyglot-covers: python.xmlrpc.server.unsupported-content-encoding-http-501
# polyglot-covers: python.xmlrpc.server.content-encoding-error-zero-body


class GzipRequestHandler(SimpleXMLRPCRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, server, body, headers=None, threshold=None):
        self.server = server
        self.path = "/RPC2"
        self.command = "POST"
        self.request_version = "HTTP/1.1"
        self.requestline = "POST /RPC2 HTTP/1.1"
        self.headers = Message()
        self.headers["Content-Length"] = str(len(body))
        for name, value in (headers or {}).items():
            self.headers[name] = value
        self.rfile = BytesIO(body)
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.121", 1234)
        self.close_connection = False
        self.encode_threshold = threshold

    def log_message(self, format, *args):
        pass


def make_gzip_dispatcher():
    dispatcher = SimpleXMLRPCDispatcher(False, None)
    dispatcher.logRequests = False
    dispatcher.register_function(lambda text: text.upper(), "upper")
    return dispatcher


def split_gzip_response(handler):
    return handler.wfile.getvalue().split(b"\r\n\r\n", 1)


def test_gzip_request_is_decoded_before_rpc_dispatch():
    request = dumps(("hello",), methodname="upper").encode()
    handler = GzipRequestHandler(
        make_gzip_dispatcher(),
        gzip_encode(request),
        {"Content-Encoding": "gzip"},
    )

    handler.do_POST()

    head, body = split_gzip_response(handler)
    assert head.startswith(b"HTTP/1.1 200 OK\r\n")
    assert loads(body) == (("HELLO",), None)


def test_large_response_is_gzipped_only_when_client_accepts_it():
    request = dumps(("compress me",), methodname="upper").encode()
    handler = GzipRequestHandler(
        make_gzip_dispatcher(),
        request,
        {"Accept-Encoding": "gzip"},
        threshold=0,
    )

    handler.do_POST()

    head, compressed = split_gzip_response(handler)
    body = gzip_decode(compressed)
    assert b"Content-Encoding: gzip\r\n" in head
    assert f"Content-length: {len(compressed)}".encode() in head
    assert loads(body) == (("COMPRESS ME",), None)


def test_bad_gzip_and_unknown_encoding_return_empty_http_errors():
    cases = [
        (b"not gzip", "gzip", b"HTTP/1.1 400 error decoding gzip content"),
        (b"payload", "br", b"HTTP/1.1 501 encoding 'br' not supported"),
    ]

    for body, encoding, status in cases:
        handler = GzipRequestHandler(
            make_gzip_dispatcher(),
            body,
            {"Content-Encoding": encoding},
        )
        handler.do_POST()
        head, response_body = split_gzip_response(handler)

        assert head.startswith(status)
        assert b"Content-length: 0\r\n" in head
        assert response_body == b""


# MultiPathXMLRPCServer 的路径→Dispatcher 映射、虚拟服务隔离与缺失路径 Fault。
#
# 同一 HTTP 服务可以按 path 选择完全不同的注册表；请求处理器仍必须把这些路径加入
# rpc_paths。add_dispatcher 返回原对象便于链式配置，未知路径会被包装为 XML-RPC Fault。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.MultiPathXMLRPCServer
# polyglot-covers: python.xmlrpc.server.MultiPathXMLRPCServer.add_dispatcher
# polyglot-covers: python.xmlrpc.server.MultiPathXMLRPCServer.get_dispatcher
# polyglot-covers: python.xmlrpc.server.multipath-marshaled-dispatch-by-path
# polyglot-covers: python.xmlrpc.server.multipath-independent-registries
# polyglot-covers: python.xmlrpc.server.multipath-missing-path-fault
# polyglot-covers: python.xmlrpc.server.multipath-handler-rpc-path-coordination


def make_path_dispatcher(label):
    dispatcher = SimpleXMLRPCDispatcher(False, None)
    dispatcher.register_function(lambda: label, "identity")
    return dispatcher


def call_path(server, path):
    request = dumps((), methodname="identity")
    response = server._marshaled_dispatch(request, path=path)
    values, _ = loads(response)
    return values[0]


def test_paths_select_independent_dispatchers_without_binding_socket(monkeypatch):
    def fake_tcp_init(self, address, handler, bind_and_activate=True):
        self.server_address = address
        self.RequestHandlerClass = handler

    monkeypatch.setattr(socketserver.TCPServer, "__init__", fake_tcp_init)
    server = MultiPathXMLRPCServer(
        ("127.0.0.1", 0),
        bind_and_activate=False,
    )
    first = make_path_dispatcher("first")
    second = make_path_dispatcher("second")

    assert server.add_dispatcher("/first", first) is first
    server.add_dispatcher("/second", second)

    assert server.get_dispatcher("/first") is first
    assert call_path(server, "/first") == "first"
    assert call_path(server, "/second") == "second"

    with pytest.raises(Fault) as missing:
        call_path(server, "/missing")
    assert "/missing" in missing.value.faultString


# CGIXMLRPCRequestHandler 的显式请求、stdin 长度读取、stdout 头/正文与 GET 错误。
#
# CGI 版本不监听端口：POST 数据来自参数或 CONTENT_LENGTH 限定的 stdin，结果把文本头写到
# stdout、XML bytes 写到 stdout.buffer。基础处理器的 GET 返回 400，因为 XML-RPC 使用 POST。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.CGIXMLRPCRequestHandler
# polyglot-covers: python.xmlrpc.server.CGIXMLRPCRequestHandler.handle_request
# polyglot-covers: python.xmlrpc.server.CGIXMLRPCRequestHandler.handle_xmlrpc
# polyglot-covers: python.xmlrpc.server.cgi-request-explicit-text
# polyglot-covers: python.xmlrpc.server.cgi-content-length-stdin-read
# polyglot-covers: python.xmlrpc.server.cgi-content-type-length-stdout
# polyglot-covers: python.xmlrpc.server.CGIXMLRPCRequestHandler.handle_get
# polyglot-covers: python.xmlrpc.server.cgi-get-http-400


class CapturedStdout:
    def __init__(self):
        self.text = StringIO()
        self.buffer = BytesIO()

    def write(self, value):
        return self.text.write(value)

    def flush(self):
        pass


def make_handler():
    handler = CGIXMLRPCRequestHandler()
    handler.register_function(lambda left, right: left + right, "add")
    return handler


def test_explicit_request_text_writes_cgi_headers_and_xml_body(monkeypatch):
    output = CapturedStdout()
    request = dumps((2, 3), methodname="add")

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        make_handler().handle_request(request)

    response = output.buffer.getvalue()
    assert output.text.getvalue().startswith("Content-Type: text/xml\n")
    assert f"Content-Length: {len(response)}\n\n" in output.text.getvalue()
    assert loads(response) == ((5,), None)


def test_post_without_argument_reads_only_declared_stdin_length(
    monkeypatch,
):
    output = CapturedStdout()
    request = dumps((4, 5), methodname="add")
    stdin = StringIO(request + "ignored trailing input")

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        patch.setattr(sys, "stdin", stdin)
        patch.setenv("REQUEST_METHOD", "POST")
        patch.setenv("CONTENT_LENGTH", str(len(request)))
        make_handler().handle_request()

    assert loads(output.buffer.getvalue()) == ((9,), None)
    assert stdin.read() == "ignored trailing input"


def test_get_is_reported_as_cgi_status_400_with_html_body(monkeypatch):
    output = CapturedStdout()

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        patch.setenv("REQUEST_METHOD", "GET")
        make_handler().handle_request()

    assert output.text.getvalue().startswith("Status: 400 Bad Request\n")
    assert "Content-Type: text/html;charset=utf-8\n" in output.text.getvalue()
    assert b"Error response" in output.buffer.getvalue()


# XMLRPCDocGenerator 的标题/说明/方法文档，以及 HTTP/CGI 文档服务器组合。
#
# 文档生成器从已注册函数和实例的 introspection 信息构造 HTML，并转义标题。Doc 请求
# 处理器只在合法 RPC path 上用 GET 返回文档；POST 行为仍继承普通 XML-RPC 处理器。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.xmlrpc.server.XMLRPCDocGenerator
# polyglot-covers: python.xmlrpc.server.XMLRPCDocGenerator.set_server_title
# polyglot-covers: python.xmlrpc.server.XMLRPCDocGenerator.set_server_name
# polyglot-covers: python.xmlrpc.server.XMLRPCDocGenerator.set_server_documentation
# polyglot-covers: python.xmlrpc.server.generate_html_documentation
# polyglot-covers: python.xmlrpc.server.documentation-function-signature-docstring
# polyglot-covers: python.xmlrpc.server.DocXMLRPCRequestHandler
# polyglot-covers: python.xmlrpc.server.DocXMLRPCRequestHandler.do_GET
# polyglot-covers: python.xmlrpc.server.DocXMLRPCServer
# polyglot-covers: python.xmlrpc.server.DocCGIXMLRPCRequestHandler


class DocumentedDispatcher(SimpleXMLRPCDispatcher, XMLRPCDocGenerator):
    def __init__(self):
        SimpleXMLRPCDispatcher.__init__(self, False, None)
        XMLRPCDocGenerator.__init__(self)


class MemoryDocHandler(DocXMLRPCRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, server, path="/RPC2"):
        self.server = server
        self.path = path
        self.command = "GET"
        self.request_version = "HTTP/1.1"
        self.requestline = f"GET {path} HTTP/1.1"
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.123", 1234)
        self.close_connection = False

    def log_message(self, format, *args):
        pass


def make_documented_dispatcher():
    dispatcher = DocumentedDispatcher()

    def add(left, right=0):
        """返回两个数字之和。"""
        return left + right

    dispatcher.register_function(add)
    dispatcher.set_server_title("Study <RPC>")
    dispatcher.set_server_name("Polyglot XML-RPC")
    dispatcher.set_server_documentation("用于学习 add() 的接口。")
    return dispatcher


def test_generator_includes_escaped_title_service_text_signature_and_docstring():
    html = make_documented_dispatcher().generate_html_documentation()

    assert "<title>" in html
    assert "Study &lt;RPC&gt;" in html
    assert "Polyglot XML-RPC" in html
    assert "用于学习" in html
    assert ">add<" in html
    assert "(left, right=0)" in html
    assert "返回两个数字之和。" in html


def test_documentation_get_handler_returns_generated_html_on_rpc_path():
    dispatcher = make_documented_dispatcher()
    dispatcher.logRequests = False
    handler = MemoryDocHandler(dispatcher)

    handler.do_GET()

    head, body = handler.wfile.getvalue().split(b"\r\n\r\n", 1)
    assert head.startswith(b"HTTP/1.1 200 OK\r\n")
    assert b"Content-type: text/html\r\n" in head
    assert b"Polyglot XML-RPC" in body


def test_documented_http_and_cgi_classes_combine_rpc_and_doc_behaviors():
    assert issubclass(DocXMLRPCServer, SimpleXMLRPCServer)
    assert issubclass(DocXMLRPCServer, XMLRPCDocGenerator)
    assert issubclass(DocCGIXMLRPCRequestHandler, CGIXMLRPCRequestHandler)
    assert issubclass(DocCGIXMLRPCRequestHandler, XMLRPCDocGenerator)
