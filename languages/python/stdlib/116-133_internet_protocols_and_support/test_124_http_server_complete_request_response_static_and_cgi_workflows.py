"""124｜学习 http.server 的请求解析、响应、静态文件、CGI 与服务器组合。

处理器从二进制 rfile 解析方法、含查询串的 path、版本和 RFC 风格头，再按大小写敏感的
方法名调用 do_METHOD。HTTP/0.9 兼容请求没有响应状态行，只能用于 GET。

这些案例面向 Python 3.10 当前补丁系列。
"""

from email.message import Message
from email.utils import formatdate
from http.client import HTTPMessage
import http.server as http_server
from http.server import BaseHTTPRequestHandler
from http.server import CGIHTTPRequestHandler
from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler
from http.server import ThreadingHTTPServer
from io import BytesIO
import os
from socketserver import TCPServer
from socketserver import ThreadingMixIn
from urllib.parse import quote

import pytest


# polyglot-covers: python.http.server.BaseHTTPRequestHandler
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.handle_one_request
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.parse_request
# polyglot-covers: python.http.server.request-method-do-star-dispatch
# polyglot-covers: python.http.server.requestline-command-path-version
# polyglot-covers: python.http.server.request-path-includes-query
# polyglot-covers: python.http.server.request-headers-HTTPMessage
# polyglot-covers: python.http.server.request-path-leading-double-slash-collapse
# polyglot-covers: python.http.server.http09-get-request
# polyglot-covers: python.http.server.http09-response-has-no-status-headers



class MemoryHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, request_bytes):
        self.rfile = BytesIO(request_bytes)
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.10", 4321)
        self.server = object()
        self.seen = []

    def do_GET(self):
        self.seen.append(
            (self.command, self.path, self.request_version, self.headers),
        )
        body = b"handled"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def test_handle_one_request_parses_fields_and_dispatches_to_do_method():
    handler = MemoryHandler(
        b"GET /items?limit=2 HTTP/1.1\r\n"
        b"Host: example.test\r\n"
        b"X-Trace: one\r\n"
        b"\r\n",
    )

    handler.handle_one_request()

    [(command, path, version, headers)] = handler.seen
    assert (command, path, version) == (
        "GET",
        "/items?limit=2",
        "HTTP/1.1",
    )
    assert isinstance(headers, HTTPMessage)
    assert headers["Host"] == "example.test"
    assert headers["X-Trace"] == "one"
    assert handler.requestline == "GET /items?limit=2 HTTP/1.1"
    assert handler.wfile.getvalue().endswith(b"\r\n\r\nhandled")


def test_scheme_relative_looking_path_is_collapsed_to_avoid_open_redirects():
    handler = MemoryHandler(
        b"GET //attacker.test/path HTTP/1.1\r\nHost: example.test\r\n\r\n",
    )

    handler.handle_one_request()

    assert handler.seen[0][1] == "/attacker.test/path"


def test_http09_get_dispatches_but_emits_only_the_response_body():
    handler = MemoryHandler(b"GET /legacy\r\n")

    handler.handle_one_request()

    assert handler.request_version == "HTTP/0.9"
    assert handler.close_connection
    assert handler.wfile.getvalue() == b"handled"

# HTTP 请求错误边界：语法、版本、请求行/头长度与未实现方法。
#
# 解析失败会由处理器直接发送错误响应而不进入 do_*。请求行上限为 65536 字节；头字段
# 过长映射到 431。HTTP/0.9 形式只允许 GET，未知的有效方法则映射到 501。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.bad-request-syntax-400
# polyglot-covers: python.http.server.bad-request-version-400
# polyglot-covers: python.http.server.http-version-not-supported-505
# polyglot-covers: python.http.server.http09-non-get-rejected
# polyglot-covers: python.http.server.request-line-limit-65536
# polyglot-covers: python.http.server.request-uri-too-long-414
# polyglot-covers: python.http.server.header-line-too-long-431
# polyglot-covers: python.http.server.unsupported-method-501
# polyglot-covers: python.http.server.parse-failure-skips-method-dispatch



class ErrorCapturingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, request_bytes):
        self.rfile = BytesIO(request_bytes)
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.20", 1234)
        self.server = object()
        self.dispatched = False

    def do_GET(self):
        self.dispatched = True

    def log_message(self, format, *args):
        pass


def response_bytes(request):
    handler = ErrorCapturingHandler(request)
    handler.handle_one_request()
    return handler, handler.wfile.getvalue()


def test_bad_request_shapes_are_rejected_before_dispatch():
    cases = [
        b"GET / extra words HTTP/1.1\r\n\r\n",
        b"GET / HTTP/one\r\n\r\n",
        b"POST /legacy\r\n",
    ]

    for request in cases:
        handler, response = response_bytes(request)
        assert not handler.dispatched
        assert b"Error response" in response


def test_http2_request_line_is_rejected_by_this_http1_server():
    handler, response = response_bytes(b"GET / HTTP/2.0\r\n\r\n")

    assert not handler.dispatched
    assert b"Invalid HTTP version" in response


def test_oversized_request_line_maps_to_414():
    request = b"GET /" + (b"x" * 65_532) + b" HTTP/1.1\r\n\r\n"

    handler, response = response_bytes(request)

    assert not handler.dispatched
    assert response.startswith(b"HTTP/1.1 414 Request-URI Too Long\r\n")


def test_oversized_header_line_maps_to_431():
    request = (
        b"GET / HTTP/1.1\r\n"
        b"X-Large: "
        + (b"x" * 65_536)
        + b"\r\n\r\n"
    )

    handler, response = response_bytes(request)

    assert not handler.dispatched
    assert response.startswith(
        b"HTTP/1.1 431 Line too long\r\n",
    )


def test_valid_but_unimplemented_method_maps_to_501():
    handler, response = response_bytes(
        b"PATCH /items/1 HTTP/1.1\r\nHost: example.test\r\n\r\n",
    )

    assert not handler.dispatched
    assert response.startswith(b"HTTP/1.1 501 Unsupported method")

# HTTP/1.1 持久连接、Connection 指令与 Expect: 100-continue。
#
# 处理器只有在双方均支持 HTTP/1.1 时默认保持连接，并会在同一 rfile 中继续解析请求。
# Expect 钩子必须先决定是否允许客户端发送正文；拒绝时返回最终错误且不能调用 do_POST。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.http11-persistent-connection
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.handle-loop
# polyglot-covers: python.http.server.Connection-close
# polyglot-covers: python.http.server.Connection-keep-alive-http10
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.close_connection
# polyglot-covers: python.http.server.Expect-100-continue
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.handle_expect_100
# polyglot-covers: python.http.server.expect-continue-before-body-read
# polyglot-covers: python.http.server.expectation-failed-417
# polyglot-covers: python.http.server.expect-rejection-skips-do-method



class PersistentHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, request_bytes):
        self.rfile = BytesIO(request_bytes)
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.30", 1234)
        self.server = object()
        self.requests = []

    def send_small_response(self, body):
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.requests.append((self.command, self.path))
        self.send_small_response(self.path.encode("ascii"))

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        body = self.rfile.read(size)
        self.requests.append((self.command, body))
        self.send_small_response(body.upper())

    def log_message(self, format, *args):
        pass


class RejectingExpectationHandler(PersistentHandler):
    def handle_expect_100(self):
        self.send_error(417, "Expectation rejected")
        return False


def test_handle_processes_multiple_requests_until_connection_close():
    handler = PersistentHandler(
        b"GET /first HTTP/1.1\r\nHost: example.test\r\n\r\n"
        b"GET /second HTTP/1.1\r\nHost: example.test\r\n"
        b"Connection: close\r\n\r\n",
    )

    handler.handle()

    assert handler.requests == [("GET", "/first"), ("GET", "/second")]
    assert handler.wfile.getvalue().count(b"HTTP/1.1 200 OK\r\n") == 2
    assert handler.close_connection


def test_http10_keep_alive_can_opt_in_when_server_protocol_is_http11():
    handler = PersistentHandler(
        b"GET /legacy HTTP/1.0\r\nConnection: keep-alive\r\n\r\n",
    )

    handler.handle_one_request()

    assert not handler.close_connection


def test_expect_continue_emits_interim_response_before_dispatch_reads_body():
    handler = PersistentHandler(
        b"POST /upload HTTP/1.1\r\n"
        b"Host: example.test\r\n"
        b"Content-Length: 4\r\n"
        b"Expect: 100-continue\r\n\r\n"
        b"data",
    )

    handler.handle_one_request()

    wire = handler.wfile.getvalue()
    assert handler.requests == [("POST", b"data")]
    assert wire.startswith(b"HTTP/1.1 100 Continue\r\n\r\n")
    assert b"HTTP/1.1 200 OK\r\n" in wire
    assert wire.endswith(b"DATA")


def test_expect_hook_can_send_final_error_and_prevent_body_dispatch():
    handler = RejectingExpectationHandler(
        b"POST /upload HTTP/1.1\r\n"
        b"Host: example.test\r\n"
        b"Content-Length: 4\r\n"
        b"Expect: 100-continue\r\n\r\n"
        b"data",
    )

    handler.handle_one_request()

    assert handler.requests == []
    assert handler.wfile.getvalue().startswith(
        b"HTTP/1.1 417 Expectation rejected\r\n",
    )
    assert b"100 Continue" not in handler.wfile.getvalue()

# 响应状态/头缓冲、显式结束、版本字符串、日期与连接状态副作用。
#
# send_response 会加入状态行、Server 和 Date，但直到 end_headers/flush_headers 才写入
# wfile。send_header("Connection", ...) 还会同步改变循环状态；遗漏 end_headers 是常见坑。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.BaseHTTPRequestHandler.send_response
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.send_response_only
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.send_header
# polyglot-covers: python.http.server.response-headers-buffered-3.2
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.end_headers
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.flush_headers-3.3
# polyglot-covers: python.http.server.response-default-server-date-headers
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.version_string
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.date_time_string
# polyglot-covers: python.http.server.send-header-connection-state



class ResponseHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "StudyHTTP/1.0"
    sys_version = "Python/demo"

    def __init__(self):
        self.wfile = BytesIO()
        self.request_version = "HTTP/1.1"
        self.requestline = "GET / HTTP/1.1"
        self.client_address = ("192.0.2.40", 1234)
        self.close_connection = False
        self.logged = []

    def date_time_string(self, timestamp=None):
        if timestamp is None:
            return "Sun, 06 Nov 1994 08:49:37 GMT"
        return super().date_time_string(timestamp)

    def log_request(self, code="-", size="-"):
        self.logged.append((code, size))


def test_send_response_buffers_standard_and_custom_headers_until_end_headers():
    handler = ResponseHandler()

    handler.send_response(201)
    handler.send_header("Content-Type", "text/plain")

    assert handler.wfile.getvalue() == b""
    assert handler.logged == [(201, "-")]

    handler.end_headers()

    assert handler.wfile.getvalue() == (
        b"HTTP/1.1 201 Created\r\n"
        b"Server: StudyHTTP/1.0 Python/demo\r\n"
        b"Date: Sun, 06 Nov 1994 08:49:37 GMT\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
    )


def test_flush_headers_writes_current_buffer_without_adding_the_blank_line():
    handler = ResponseHandler()
    handler.send_response_only(100)
    handler.send_header("X-Stage", "interim")

    handler.flush_headers()

    assert handler.wfile.getvalue() == (
        b"HTTP/1.1 100 Continue\r\nX-Stage: interim\r\n"
    )
    assert handler._headers_buffer == []


def test_connection_header_updates_close_state_as_well_as_rendering_text():
    handler = ResponseHandler()

    handler.send_header("Connection", "close")
    assert handler.close_connection

    handler.send_header("Connection", "keep-alive")
    assert not handler.close_connection


def test_version_date_and_address_helpers_have_protocol_specific_formats():
    handler = ResponseHandler()

    assert handler.version_string() == "StudyHTTP/1.0 Python/demo"
    assert handler.date_time_string(784_111_777) == (
        "Sun, 06 Nov 1994 08:49:37 GMT"
    )
    assert handler.address_string() == "192.0.2.40"

# send_error 的完整响应、HTML 转义、HEAD/无正文状态与未知状态码。
#
# 错误页会计算 Content-Length 并强制关闭连接；自定义 message/explain 进入 HTML 前会转义。
# HEAD 保留与 GET 相同的长度头但不写正文，1xx、204、205、304 则根本不生成错误正文。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.BaseHTTPRequestHandler.send_error
# polyglot-covers: python.http.server.send-error-default-response-mapping
# polyglot-covers: python.http.server.send-error-html-escaping
# polyglot-covers: python.http.server.send-error-content-length-3.4
# polyglot-covers: python.http.server.send-error-connection-close
# polyglot-covers: python.http.server.send-error-head-no-body
# polyglot-covers: python.http.server.send-error-1xx-no-body
# polyglot-covers: python.http.server.send-error-204-205-304-no-body
# polyglot-covers: python.http.server.send-error-unknown-code-fallback



class ErrorResponseHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "Study/1"
    sys_version = ""

    def __init__(self, command="GET"):
        self.wfile = BytesIO()
        self.command = command
        self.request_version = "HTTP/1.1"
        self.requestline = f"{command} / HTTP/1.1"
        self.client_address = ("192.0.2.50", 1234)
        self.close_connection = False

    def date_time_string(self, timestamp=None):
        return "Sun, 06 Nov 1994 08:49:37 GMT"

    def log_message(self, format, *args):
        pass


def split_error_response(handler):
    head, body = handler.wfile.getvalue().split(b"\r\n\r\n", 1)
    return head, body


def error_header_value(head, name):
    prefix = name.lower().encode("ascii") + b":"
    for line in head.split(b"\r\n")[1:]:
        if line.lower().startswith(prefix):
            return line.split(b":", 1)[1].strip()
    return None


def test_error_page_escapes_untrusted_text_and_length_matches_encoded_body():
    handler = ErrorResponseHandler()

    handler.send_error(404, "<missing>", "Use <safe> & retry")

    head, body = split_error_response(handler)
    assert head.startswith(b"HTTP/1.1 404 <missing>")
    assert b"&lt;missing&gt;" in body
    assert b"Use &lt;safe&gt; &amp; retry" in body
    assert b"<safe>" not in body
    assert int(error_header_value(head, "Content-Length")) == len(body)
    assert error_header_value(head, "Connection") == b"close"
    assert handler.close_connection


def test_head_keeps_representation_length_but_omits_the_error_body():
    get_handler = ErrorResponseHandler("GET")
    head_handler = ErrorResponseHandler("HEAD")

    get_handler.send_error(404)
    head_handler.send_error(404)

    get_head, get_body = split_error_response(get_handler)
    head_head, head_body = split_error_response(head_handler)
    assert head_body == b""
    assert error_header_value(head_head, "Content-Length") == str(
        len(get_body),
    ).encode("ascii")
    assert error_header_value(get_head, "Content-Length") == error_header_value(
        head_head,
        "Content-Length",
    )


def test_bodyless_statuses_do_not_emit_entity_headers_or_body():
    for code in (100, 204, 205, 304):
        handler = ErrorResponseHandler()
        handler.send_error(code)

        head, body = split_error_response(handler)
        assert body == b""
        assert error_header_value(head, "Content-Type") is None
        assert error_header_value(head, "Content-Length") is None


def test_unknown_status_uses_question_mark_fallback_text():
    handler = ErrorResponseHandler()

    handler.send_error(599)

    head, body = split_error_response(handler)
    assert head.startswith(b"HTTP/1.1 599 ???")
    assert b"Message: ???." in body

# SimpleHTTPRequestHandler 的 URL→本地路径转换、MIME 推断与目录参数。
#
# translate_path 会丢弃查询/片段、URL 解码并把结果限制在配置目录内；它不是直接拼接用户
# 路径。自 Python 3.9 起 directory 接受 PathLike，extensions_map 只保存自定义覆盖项。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.SimpleHTTPRequestHandler
# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.directory-3.7
# polyglot-covers: python.http.server.simple-directory-pathlike-3.9
# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.translate_path
# polyglot-covers: python.http.server.translate-path-drops-query-fragment
# polyglot-covers: python.http.server.translate-path-percent-decodes
# polyglot-covers: python.http.server.translate-path-normalizes-parent-components
# polyglot-covers: python.http.server.translate-path-preserves-trailing-slash
# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.guess_type
# polyglot-covers: python.http.server.extensions-map-overrides-only-3.9
# polyglot-covers: python.http.server.guess-type-case-insensitive-extension
# polyglot-covers: python.http.server.guess-type-octet-stream-fallback



class TypeHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".study": "application/x-study",
    }


def bare_handler(handler_type, directory):
    handler = object.__new__(handler_type)
    handler.directory = os.fspath(directory)
    return handler


def test_translate_path_decodes_url_and_never_escapes_the_configured_root(tmp_path):
    root = tmp_path / "public"
    root.mkdir()
    handler = bare_handler(TypeHandler, root)

    translated = handler.translate_path(
        "/docs/../assets/%E8%B5%84%E6%96%99.txt?download=1#ignored",
    )
    attempted_escape = handler.translate_path("/../../outside.txt")

    assert translated == os.path.join(root, "assets", "资料.txt")
    assert attempted_escape == os.path.join(root, "outside.txt")
    assert os.path.commonpath((root, attempted_escape)) == os.fspath(root)


def test_translate_path_preserves_an_explicit_directory_trailing_slash(tmp_path):
    handler = bare_handler(TypeHandler, tmp_path)

    translated = handler.translate_path("/docs/")

    assert translated == os.path.join(tmp_path, "docs") + os.sep


def test_guess_type_uses_case_insensitive_overrides_then_generic_fallback(tmp_path):
    handler = bare_handler(TypeHandler, tmp_path)

    assert handler.guess_type("lesson.study") == "application/x-study"
    assert handler.guess_type("lesson.STUDY") == "application/x-study"
    assert handler.guess_type("payload.unknown-polyglot") == (
        "application/octet-stream"
    )
    assert SimpleHTTPRequestHandler.extensions_map == {
        ".gz": "application/gzip",
        ".Z": "application/octet-stream",
        ".bz2": "application/x-bzip2",
        ".xz": "application/x-xz",
    }


def test_constructor_converts_pathlike_directory_before_base_initialization(
    tmp_path,
    monkeypatch,
):
    received = []

    def fake_base_init(self, *args, **kwargs):
        received.append((args, kwargs))

    monkeypatch.setattr(BaseHTTPRequestHandler, "__init__", fake_base_init)

    handler = SimpleHTTPRequestHandler(
        object(),
        ("192.0.2.1", 1),
        object(),
        directory=tmp_path,
    )

    assert handler.directory == os.fspath(tmp_path)
    assert len(received) == 1

# SimpleHTTPRequestHandler 的 GET/HEAD 文件工作流与二进制复制。
#
# send_head 负责打开文件并发送 Content-Type、精确长度和 Last-Modified；do_GET 再复制
# 二进制内容，do_HEAD 只关闭文件。即使扩展名是文本，也按 rb 打开，避免平台换行转换。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.do_GET
# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.do_HEAD
# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.send_head
# polyglot-covers: python.http.server.simple-file-content-type
# polyglot-covers: python.http.server.simple-file-content-length
# polyglot-covers: python.http.server.simple-file-last-modified
# polyglot-covers: python.http.server.simple-file-binary-open
# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.copyfile
# polyglot-covers: python.http.server.head-same-headers-no-body
# polyglot-covers: python.http.server.simple-url-decoded-filename



class MemorySimpleHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, directory, path, command):
        self.directory = os.fspath(directory)
        self.path = path
        self.command = command
        self.request_version = "HTTP/1.1"
        self.requestline = f"{command} {path} HTTP/1.1"
        self.headers = Message()
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.60", 1234)
        self.close_connection = False

    def log_message(self, format, *args):
        pass


def split_file_response(handler):
    return handler.wfile.getvalue().split(b"\r\n\r\n", 1)


def file_header_value(head, name):
    prefix = name.lower().encode("ascii") + b":"
    for line in head.split(b"\r\n")[1:]:
        if line.lower().startswith(prefix):
            return line.split(b":", 1)[1].strip()
    return None


def test_get_returns_file_metadata_and_exact_binary_content(tmp_path):
    content = b"first\r\nsecond\x00\xff"
    path = tmp_path / "资料.txt"
    path.write_bytes(content)
    handler = MemorySimpleHandler(tmp_path, quote("/资料.txt"), "GET")

    handler.do_GET()

    head, body = split_file_response(handler)
    assert head.startswith(b"HTTP/1.1 200 OK\r\n")
    assert file_header_value(head, "Content-Type").startswith(b"text/plain")
    assert file_header_value(head, "Content-Length") == str(len(content)).encode()
    assert file_header_value(head, "Last-Modified") is not None
    assert body == content


def test_head_returns_get_metadata_without_copying_the_file_body(tmp_path):
    content = b"body that must not be sent"
    (tmp_path / "lesson.bin").write_bytes(content)
    get_handler = MemorySimpleHandler(tmp_path, "/lesson.bin", "GET")
    head_handler = MemorySimpleHandler(tmp_path, "/lesson.bin", "HEAD")

    get_handler.do_GET()
    head_handler.do_HEAD()

    get_head, get_body = split_file_response(get_handler)
    head_head, head_body = split_file_response(head_handler)
    assert get_body == content
    assert head_body == b""
    assert file_header_value(head_head, "Content-Length") == str(len(content)).encode()
    for name in ("Content-Type", "Content-Length", "Last-Modified"):
        assert file_header_value(head_head, name) == file_header_value(get_head, name)

# 静态目录的斜杠重定向、首页优先级与安全转义列表。
#
# 目录 URL 缺少末尾斜杠时返回 301 并保留查询串；有斜杠后优先 index.html，再找
# index.htm。没有首页才生成按名称排序的 HTML 列表，链接要 URL 编码、显示名要 HTML 转义。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.simple-directory-trailing-slash-redirect
# polyglot-covers: python.http.server.simple-directory-redirect-preserves-query
# polyglot-covers: python.http.server.simple-directory-redirect-zero-length
# polyglot-covers: python.http.server.simple-directory-index-html-priority
# polyglot-covers: python.http.server.simple-directory-index-htm-fallback
# polyglot-covers: python.http.server.SimpleHTTPRequestHandler.list_directory
# polyglot-covers: python.http.server.directory-list-case-insensitive-sort
# polyglot-covers: python.http.server.directory-list-url-quotes-links
# polyglot-covers: python.http.server.directory-list-html-escapes-display-name
# polyglot-covers: python.http.server.directory-list-directory-suffix



class DirectoryHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, directory, path):
        self.directory = os.fspath(directory)
        self.path = path
        self.command = "GET"
        self.request_version = "HTTP/1.1"
        self.requestline = f"GET {path} HTTP/1.1"
        self.headers = Message()
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.70", 1234)
        self.close_connection = False

    def log_message(self, format, *args):
        pass


def split_directory_response(handler):
    return handler.wfile.getvalue().split(b"\r\n\r\n", 1)


def test_directory_without_slash_redirects_and_preserves_query(tmp_path):
    (tmp_path / "docs").mkdir()
    handler = DirectoryHandler(tmp_path, "/docs?view=compact")

    handler.do_GET()

    head, body = split_directory_response(handler)
    assert head.startswith(b"HTTP/1.1 301 Moved Permanently\r\n")
    assert b"Location: /docs/?view=compact\r\n" in head
    # split 已移除 header/body 分隔符，最后一个 header 后不再含 CRLF。
    assert b"Content-Length: 0" in head
    assert body == b""


def test_index_html_wins_over_index_htm(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_bytes(b"html winner")
    (docs / "index.htm").write_bytes(b"htm fallback")
    handler = DirectoryHandler(tmp_path, "/docs/")

    handler.do_GET()

    _, body = split_directory_response(handler)
    assert body == b"html winner"


def test_directory_listing_sorts_and_escapes_names_for_two_output_contexts(tmp_path):
    listing = tmp_path / "listing"
    listing.mkdir()
    (listing / "b.txt").write_text("b", encoding="utf-8")
    (listing / "A & one.txt").write_text("a", encoding="utf-8")
    (listing / "child").mkdir()
    handler = DirectoryHandler(tmp_path, "/listing/")

    handler.do_GET()

    head, body = split_directory_response(handler)
    text = body.decode(errors="surrogateescape")
    assert head.startswith(b"HTTP/1.1 200 OK\r\n")
    assert b"Content-type: text/html; charset=" in head
    assert 'href="A%20%26%20one.txt"' in text
    assert "A &amp; one.txt" in text
    assert 'href="child/"' in text
    assert "child/" in text
    assert text.index("A &amp; one.txt") < text.index("b.txt")

# 静态文件的 If-Modified-Since、If-None-Match 优先规则与 404 边界。
#
# 有效 UTC 日期且文件不晚于条件时间时返回 304；存在 If-None-Match 时该实现不再处理
# If-Modified-Since。非法日期被忽略。缺失文件和“文件名后带斜杠”都映射为 404。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.simple-if-modified-since-3.7
# polyglot-covers: python.http.server.simple-if-modified-since-utc-comparison
# polyglot-covers: python.http.server.simple-not-modified-304
# polyglot-covers: python.http.server.simple-if-none-match-bypasses-ims
# polyglot-covers: python.http.server.simple-invalid-ims-ignored
# polyglot-covers: python.http.server.simple-file-open-oserror-404
# polyglot-covers: python.http.server.simple-file-trailing-slash-404
# polyglot-covers: python.http.server.simple-404-file-not-found-message



class ConditionalHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, directory, path, headers=None):
        self.directory = os.fspath(directory)
        self.path = path
        self.command = "GET"
        self.request_version = "HTTP/1.1"
        self.requestline = f"GET {path} HTTP/1.1"
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.80", 1234)
        self.close_connection = False

    def log_message(self, format, *args):
        pass


def split_conditional_response(handler):
    return handler.wfile.getvalue().split(b"\r\n\r\n", 1)


def make_fixed_file(tmp_path):
    path = tmp_path / "asset.txt"
    path.write_bytes(b"current")
    timestamp = 1_600_000_000
    os.utime(path, (timestamp, timestamp))
    return path, timestamp


def test_not_modified_response_has_no_file_body(tmp_path):
    _, timestamp = make_fixed_file(tmp_path)
    handler = ConditionalHandler(
        tmp_path,
        "/asset.txt",
        {"If-Modified-Since": formatdate(timestamp, usegmt=True)},
    )

    handler.do_GET()

    head, body = split_conditional_response(handler)
    assert head.startswith(b"HTTP/1.1 304 Not Modified\r\n")
    assert b"Content-Length:" not in head
    assert body == b""


def test_if_none_match_presence_disables_this_modules_date_shortcut(tmp_path):
    _, timestamp = make_fixed_file(tmp_path)
    handler = ConditionalHandler(
        tmp_path,
        "/asset.txt",
        {
            "If-Modified-Since": formatdate(timestamp, usegmt=True),
            "If-None-Match": '"some-etag"',
        },
    )

    handler.do_GET()

    head, body = split_conditional_response(handler)
    assert head.startswith(b"HTTP/1.1 200 OK\r\n")
    assert body == b"current"


def test_invalid_date_is_ignored_instead_of_becoming_bad_request(tmp_path):
    make_fixed_file(tmp_path)
    handler = ConditionalHandler(
        tmp_path,
        "/asset.txt",
        {"If-Modified-Since": "not a valid HTTP date"},
    )

    handler.do_GET()

    head, body = split_conditional_response(handler)
    assert head.startswith(b"HTTP/1.1 200 OK\r\n")
    assert body == b"current"


def test_missing_file_and_file_with_trailing_slash_are_not_served(tmp_path):
    make_fixed_file(tmp_path)

    for path in ("/missing.txt", "/asset.txt/"):
        handler = ConditionalHandler(tmp_path, path)
        handler.do_GET()

        head, body = split_conditional_response(handler)
        assert head.startswith(b"HTTP/1.1 404 File not found\r\n")
        assert b"File not found" in body

# CGIHTTPRequestHandler 的目录式识别、路径折叠、POST 限制与 Python 后缀。
#
# CGI 不是按任意文件后缀启用，而是只识别 cgi_directories 下的路径；识别前会解码并折叠
# 点段。POST 到普通静态路径返回 501。该服务器会执行程序，不适合作为生产安全边界。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.CGIHTTPRequestHandler
# polyglot-covers: python.http.server.CGIHTTPRequestHandler.cgi_directories
# polyglot-covers: python.http.server.CGIHTTPRequestHandler.is_cgi
# polyglot-covers: python.http.server.cgi-directory-boundary-match
# polyglot-covers: python.http.server.cgi-path-percent-decode-and-dot-collapse
# polyglot-covers: python.http.server.cgi-path-info-and-query-preserved
# polyglot-covers: python.http.server.cgi-too-many-parent-segments-indexerror
# polyglot-covers: python.http.server.CGIHTTPRequestHandler.do_POST
# polyglot-covers: python.http.server.cgi-post-non-script-501
# polyglot-covers: python.http.server.CGIHTTPRequestHandler.send_head-dispatch
# polyglot-covers: python.http.server.CGIHTTPRequestHandler.is_python




class MemoryCGIHandler(CGIHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, path, command="GET"):
        self.path = path
        self.command = command
        self.request_version = "HTTP/1.1"
        self.requestline = f"{command} {path} HTTP/1.1"
        self.headers = Message()
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.90", 1234)
        self.close_connection = False
        self.ran = False

    def run_cgi(self):
        self.ran = True
        return None

    def log_message(self, format, *args):
        pass


def test_is_cgi_matches_only_configured_directory_boundary_and_records_remainder():
    handler = MemoryCGIHandler("/cgi-bin/tool.py/extra?mode=fast")

    assert handler.is_cgi()
    assert handler.cgi_info == (
        "/cgi-bin",
        "tool.py/extra?mode=fast",
    )

    assert not MemoryCGIHandler("/prefix/cgi-bin/tool.py").is_cgi()
    assert not MemoryCGIHandler("/cgi-binary/tool.py").is_cgi()


def test_cgi_detection_decodes_and_collapses_dot_segments_before_matching():
    handler = MemoryCGIHandler(
        "/cgi-bin/other/%2e%2e/tool.py?mode=fast",
    )

    assert handler.is_cgi()
    assert handler.cgi_info == ("/cgi-bin", "tool.py?mode=fast")

    with pytest.raises(IndexError):
        MemoryCGIHandler("/../../tool.py").is_cgi()


def test_send_head_dispatches_cgi_path_to_run_cgi_without_opening_static_file():
    handler = MemoryCGIHandler("/cgi-bin/tool.py")

    result = handler.send_head()

    assert result is None
    assert handler.ran


def test_post_to_non_cgi_path_returns_not_implemented():
    handler = MemoryCGIHandler("/forms/submit", command="POST")

    handler.do_POST()

    assert not handler.ran
    assert handler.wfile.getvalue().startswith(
        b"HTTP/1.1 501 Can only POST to CGI scripts\r\n",
    )


def test_python_script_detection_is_case_insensitive_but_extension_specific():
    handler = MemoryCGIHandler("/")

    assert handler.is_python("task.py")
    assert handler.is_python("task.PYW")
    assert not handler.is_python("task.py.txt")
    assert not handler.is_python("task.sh")

# HTTPServer 类组合、绑定元数据、日志控制字符清洗与符号链接风险。
#
# ThreadingHTTPServer 通过 mixin 组合并使用守护线程。3.10.9 起默认日志转义控制字符；
# SimpleHTTPRequestHandler 仍会跟随符号链接，所以配置目录不是可靠的文件系统沙箱。
#
# 这些案例面向 Python 3.10 当前补丁系列。

# polyglot-covers: python.http.server.HTTPServer
# polyglot-covers: python.http.server.HTTPServer-is-TCPServer
# polyglot-covers: python.http.server.HTTPServer.allow_reuse_address
# polyglot-covers: python.http.server.HTTPServer.server_bind-name-port
# polyglot-covers: python.http.server.ThreadingHTTPServer-3.7
# polyglot-covers: python.http.server.ThreadingHTTPServer-ThreadingMixIn
# polyglot-covers: python.http.server.ThreadingHTTPServer.daemon_threads
# polyglot-covers: python.http.server.log-message-control-scrubbing-3.10.9
# polyglot-covers: python.http.server.BaseHTTPRequestHandler.address_string-no-dns-3.3
# polyglot-covers: python.http.server.simple-handler-follows-symbolic-links
# polyglot-covers: python.http.server.simple-handler-not-filesystem-sandbox



class SymlinkHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, directory, path):
        self.directory = os.fspath(directory)
        self.path = path
        self.command = "GET"
        self.request_version = "HTTP/1.1"
        self.requestline = f"GET {path} HTTP/1.1"
        self.headers = Message()
        self.wfile = BytesIO()
        self.client_address = ("192.0.2.100", 1234)
        self.close_connection = False

    def log_message(self, format, *args):
        pass


def test_http_server_classes_expose_expected_tcp_and_threading_composition():
    assert issubclass(HTTPServer, TCPServer)
    assert HTTPServer.allow_reuse_address == 1
    assert issubclass(ThreadingHTTPServer, ThreadingMixIn)
    assert issubclass(ThreadingHTTPServer, HTTPServer)
    assert ThreadingHTTPServer.daemon_threads is True


def test_server_bind_records_resolved_name_and_actual_bound_port(monkeypatch):
    server = object.__new__(HTTPServer)
    server.server_address = ("127.0.0.1", 8123)
    monkeypatch.setattr(TCPServer, "server_bind", lambda self: None)
    monkeypatch.setattr(
        http_server.socket,
        "getfqdn",
        lambda host: "loopback.example",
    )

    server.server_bind()

    assert server.server_name == "loopback.example"
    assert server.server_port == 8123


def test_default_log_message_escapes_terminal_control_characters(capsys):
    handler = object.__new__(BaseHTTPRequestHandler)
    handler.client_address = ("192.0.2.101", 1234)
    handler.log_date_time_string = lambda: "01/Jan/2000 00:00:00"

    handler.log_message("path=%s", "/safe\ncolor\x1b[31m")

    stderr = capsys.readouterr().err
    assert "path=/safe\\x0acolor\\x1b[31m" in stderr
    assert stderr.count("\n") == 1
    assert handler.address_string() == "192.0.2.101"


def test_static_handler_follows_symlink_outside_served_directory(tmp_path):
    root = tmp_path / "public"
    root.mkdir()
    secret = tmp_path / "outside.txt"
    secret.write_bytes(b"outside root")
    (root / "link.txt").symlink_to(secret)
    handler = SymlinkHandler(root, "/link.txt")

    handler.do_GET()

    _, body = handler.wfile.getvalue().split(b"\r\n\r\n", 1)
    assert body == b"outside root"
