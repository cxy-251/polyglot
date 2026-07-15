"""学习 wsgiref 工具、响应头、验证器、handler 与参考服务器的完整流程。

整个包规模适中且共同服务 WSGI 协议，因此集中在一个测试套。案例通过内存流和注入点运行，
不会绑定真实 socket；Python 测试集仍未统一运行。
"""

import io
from wsgiref import simple_server
from wsgiref import util
from wsgiref.handlers import BaseCGIHandler
from wsgiref.handlers import SimpleHandler
from wsgiref.headers import Headers
from wsgiref.validate import validator

import pytest


# polyglot-covers: python.wsgiref.util.setup_testing_defaults
# polyglot-covers: python.wsgiref.util.setup_testing_defaults-does-not-overwrite
# polyglot-covers: python.wsgiref.util.setup_testing_defaults-test-only
# polyglot-covers: python.wsgiref.util.guess_scheme
# polyglot-covers: python.wsgiref.util.application_uri
# polyglot-covers: python.wsgiref.util.request_uri
# polyglot-covers: python.wsgiref.util.request_uri.include_query
# polyglot-covers: python.wsgiref.util.uri-http-host-precedence
# polyglot-covers: python.wsgiref.util.uri-default-port-omission
# polyglot-covers: python.wsgiref.util.shift_path_info
# polyglot-covers: python.wsgiref.util.shift_path_info-mutates-environ
# polyglot-covers: python.wsgiref.util.shift_path_info-routing-workflow
# polyglot-covers: python.wsgiref.util.shift_path_info-no-segment-none
# polyglot-covers: python.wsgiref.util.shift_path_info-trailing-slash-empty-segment
# polyglot-covers: python.wsgiref.util.FileWrapper
# polyglot-covers: python.wsgiref.util.FileWrapper.__iter__
# polyglot-covers: python.wsgiref.util.FileWrapper.__next__
# polyglot-covers: python.wsgiref.util.FileWrapper.blksize
# polyglot-covers: python.wsgiref.util.FileWrapper-empty-read-stops-nonresumable
# polyglot-covers: python.wsgiref.util.FileWrapper.close
# polyglot-covers: python.wsgiref.util.FileWrapper-sequence-protocol-deprecated-3.8
# polyglot-covers: python.wsgiref.util.is_hop_by_hop
# polyglot-covers: python.wsgiref.headers.Headers
# polyglot-covers: python.wsgiref.headers.Headers-case-insensitive-name
# polyglot-covers: python.wsgiref.headers.Headers.__getitem__
# polyglot-covers: python.wsgiref.headers.Headers.__setitem__
# polyglot-covers: python.wsgiref.headers.Headers.__delitem__
# polyglot-covers: python.wsgiref.headers.Headers.__contains__
# polyglot-covers: python.wsgiref.headers.Headers.get
# polyglot-covers: python.wsgiref.headers.Headers.setdefault
# polyglot-covers: python.wsgiref.headers.Headers.keys-values-items
# polyglot-covers: python.wsgiref.headers.Headers.get_all
# polyglot-covers: python.wsgiref.headers.Headers.add_header
# polyglot-covers: python.wsgiref.headers.Headers.__bytes__
# polyglot-covers: python.wsgiref.validate.validator
# polyglot-covers: python.wsgiref.validate-environ-check
# polyglot-covers: python.wsgiref.validate-start_response-check
# polyglot-covers: python.wsgiref.validate-response-iterable-check
# polyglot-covers: python.wsgiref.validate-response-chunks-must-be-bytes
# polyglot-covers: python.wsgiref.validate-bare-bytes-is-not-response-iterable
# polyglot-covers: python.wsgiref.validate-absence-of-errors-not-proof
# polyglot-covers: python.wsgiref.handlers.BaseHandler
# polyglot-covers: python.wsgiref.handlers.BaseHandler.run
# polyglot-covers: python.wsgiref.handlers.BaseHandler-start_response-write-callable
# polyglot-covers: python.wsgiref.handlers.BaseHandler-closes-response-iterable
# polyglot-covers: python.wsgiref.handlers.SimpleHandler
# polyglot-covers: python.wsgiref.handlers.SimpleHandler-in-memory-streams
# polyglot-covers: python.wsgiref.handlers.BaseCGIHandler
# polyglot-covers: python.wsgiref.handlers.BaseHandler.error_output
# polyglot-covers: python.wsgiref.handlers.BaseHandler.log_exception
# polyglot-covers: python.wsgiref.handlers.BaseHandler.error_status-headers-body
# polyglot-covers: python.wsgiref.simple_server.demo_app
# polyglot-covers: python.wsgiref.simple_server.make_server
# polyglot-covers: python.wsgiref.simple_server.make_server.server_class
# polyglot-covers: python.wsgiref.simple_server.make_server.handler_class
# polyglot-covers: python.wsgiref.simple_server.WSGIServer
# polyglot-covers: python.wsgiref.simple_server.WSGIServer.set_app
# polyglot-covers: python.wsgiref.simple_server.WSGIServer.get_app
# polyglot-covers: python.wsgiref-reference-server-not-production
# polyglot-covers: python.wsgiref-simple-server-no-real-network-test


BASE_ENVIRON = {
    "REQUEST_METHOD": "GET",
    "SCRIPT_NAME": "",
    "PATH_INFO": "/demo",
    "QUERY_STRING": "",
    "SERVER_NAME": "example.test",
    "SERVER_PORT": "80",
    "SERVER_PROTOCOL": "HTTP/1.1",
}


class RecordingBytesIO(io.BytesIO):
    def __init__(self, value):
        super().__init__(value)
        self.read_sizes = []

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


class ClosingIterable:
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    def __iter__(self):
        return iter(self.chunks)

    def close(self):
        self.closed = True


def make_environ():
    environ = {}
    util.setup_testing_defaults(environ)
    return environ


def make_start_response(records):
    def start_response(status, headers, exc_info=None):
        records.append((status, headers, exc_info))
        return lambda data: records.append(("write", data))

    return start_response


def test_setup_testing_defaults_fills_contract_without_overwriting_values():
    environ = {"REQUEST_METHOD": "POST", "HTTP_HOST": "example.test"}

    result = util.setup_testing_defaults(environ)

    assert result is None
    assert environ["REQUEST_METHOD"] == "POST"
    assert environ["HTTP_HOST"] == "example.test"
    assert environ["wsgi.version"] == (1, 0)
    assert environ["wsgi.url_scheme"] == "http"
    assert isinstance(environ["wsgi.input"], io.BytesIO)
    assert isinstance(environ["wsgi.errors"], io.StringIO)
    assert environ["wsgi.multithread"] is False
    assert environ["wsgi.multiprocess"] is False
    assert environ["wsgi.run_once"] is False


def test_guess_scheme_recognizes_only_the_cgi_https_markers():
    assert util.guess_scheme({"HTTPS": "1"}) == "https"
    assert util.guess_scheme({"HTTPS": "yes"}) == "https"
    assert util.guess_scheme({"HTTPS": "on"}) == "https"
    assert util.guess_scheme({"HTTPS": "true"}) == "http"
    assert util.guess_scheme({}) == "http"


def test_request_and_application_uri_separate_mount_resource_and_query():
    environ = {
        "wsgi.url_scheme": "https",
        "HTTP_HOST": "example.test:8443",
        "SERVER_NAME": "ignored.test",
        "SERVER_PORT": "443",
        "SCRIPT_NAME": "/app",
        "PATH_INFO": "/items one",
        "QUERY_STRING": "page=2&sort=name",
    }

    assert util.application_uri(environ) == "https://example.test:8443/app"
    assert util.request_uri(environ) == (
        "https://example.test:8443/app/items%20one?page=2&sort=name"
    )
    assert util.request_uri(environ, include_query=False) == (
        "https://example.test:8443/app/items%20one"
    )


def test_uri_omits_standard_port_and_keeps_a_nonstandard_port():
    base = {
        "wsgi.url_scheme": "https",
        "SERVER_NAME": "example.test",
        "SERVER_PORT": "443",
        "SCRIPT_NAME": "",
        "PATH_INFO": "/",
        "QUERY_STRING": "",
    }

    assert util.request_uri(base) == "https://example.test/"
    assert util.request_uri({**base, "SERVER_PORT": "444"}) == (
        "https://example.test:444/"
    )


def test_shift_path_info_moves_one_segment_for_nested_routing():
    environ = {"SCRIPT_NAME": "/api", "PATH_INFO": "/v1/users"}

    assert util.shift_path_info(environ) == "v1"
    assert environ == {"SCRIPT_NAME": "/api/v1", "PATH_INFO": "/users"}
    assert util.shift_path_info(environ) == "users"
    assert environ == {"SCRIPT_NAME": "/api/v1/users", "PATH_INFO": ""}
    assert util.shift_path_info(environ) is None


def test_shift_path_info_preserves_trailing_slash_and_caller_can_copy_state():
    environ = {"SCRIPT_NAME": "/api/item", "PATH_INFO": "/"}
    assert util.shift_path_info(environ) == ""
    assert environ == {"SCRIPT_NAME": "/api/item/", "PATH_INFO": ""}

    original = {"SCRIPT_NAME": "", "PATH_INFO": "/one/two"}
    delegated = original.copy()
    assert util.shift_path_info(delegated) == "one"
    assert original == {"SCRIPT_NAME": "", "PATH_INFO": "/one/two"}
    assert delegated == {"SCRIPT_NAME": "/one", "PATH_INFO": "/two"}


def test_filewrapper_reads_chunks_stops_at_empty_and_forwards_close():
    stream = RecordingBytesIO(b"abcdefg")
    wrapper = util.FileWrapper(stream, blksize=3)

    assert iter(wrapper) is wrapper
    assert list(wrapper) == [b"abc", b"def", b"g"]
    assert stream.read_sizes == [3, 3, 3, 3]
    assert list(wrapper) == []
    wrapper.close()
    assert stream.closed


def test_hop_by_hop_detection_is_case_insensitive():
    assert util.is_hop_by_hop("Connection")
    assert util.is_hop_by_hop("transfer-encoding")
    assert util.is_hop_by_hop("Upgrade")
    assert not util.is_hop_by_hop("Content-Type")
    assert not util.is_hop_by_hop("Content-Length")


def test_headers_are_case_insensitive_and_preserve_order_and_duplicates():
    raw = [
        ("Content-Type", "text/plain"),
        ("Set-Cookie", "a=1"),
        ("set-cookie", "b=2"),
    ]
    headers = Headers(raw)

    assert headers["content-type"] == "text/plain"
    assert "CONTENT-TYPE" in headers
    assert headers.get_all("SET-cookie") == ["a=1", "b=2"]
    assert len(headers) == 3
    assert headers.items() == raw
    assert headers.keys() == ["Content-Type", "Set-Cookie", "set-cookie"]

    headers["Set-Cookie"] = "c=3"
    assert headers.get_all("set-cookie") == ["c=3"]
    assert headers.items()[-1] == ("Set-Cookie", "c=3")


def test_missing_header_lookup_delete_and_setdefault_are_lenient():
    headers = Headers()

    assert headers["Missing"] is None
    assert headers.get("Missing") is None
    del headers["Missing"]
    assert headers.setdefault("X-Mode", "demo") == "demo"
    assert headers.setdefault("x-mode", "ignored") == "demo"
    assert headers.values() == ["demo"]


def test_add_header_formats_parameters_and_bytes_terminates_header_block():
    headers = Headers([("Content-Type", "text/plain")])
    headers.add_header(
        "Content-Disposition",
        "attachment",
        filename="résumé.txt",
        creation_date=None,
    )

    assert headers["content-disposition"] == (
        'attachment; filename="résumé.txt"; creation-date'
    )
    assert bytes(headers) == (
        b"Content-Type: text/plain\r\n"
        b'Content-Disposition: attachment; filename="r\xe9sum\xe9.txt"; creation-date\r\n'
        b"\r\n"
    )


def test_validator_forwards_a_compliant_application_and_byte_chunks():
    records = []

    def application(environ, start_response):
        assert environ["wsgi.version"] == (1, 0)
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"hello", b" ", b"world"]

    result = validator(application)(make_environ(), make_start_response(records))
    try:
        assert b"".join(result) == b"hello world"
    finally:
        result.close()

    assert records[0] == (
        "200 OK",
        [("Content-Type", "text/plain")],
        None,
    )


def test_validator_rejects_a_bare_bytes_response():
    def invalid_application(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return b"not-a-chunk-iterable"

    with pytest.raises(AssertionError):
        validator(invalid_application)(make_environ(), make_start_response([]))


def test_simple_handler_combines_write_and_iterable_then_closes_result():
    output = io.BytesIO()
    errors = io.StringIO()
    result_holder = []
    observed_environ = {}

    def application(environ, start_response):
        observed_environ.update(environ)
        write = start_response(
            "200 OK",
            [("Content-Type", "text/plain"), ("Content-Length", "5")],
        )
        write(b"he")
        result = ClosingIterable([b"llo"])
        result_holder.append(result)
        return result

    gateway = SimpleHandler(
        io.BytesIO(),
        output,
        errors,
        BASE_ENVIRON.copy(),
        multithread=False,
        multiprocess=False,
    )
    gateway.server_software = "PolyglotTest"
    gateway.run(application)

    wire = output.getvalue()
    assert wire.startswith(b"HTTP/1.0 200 OK\r\n")
    assert b"Content-Type: text/plain\r\n" in wire
    assert wire.endswith(b"\r\n\r\nhello")
    assert result_holder[0].closed
    assert observed_environ["wsgi.multithread"] is False
    assert observed_environ["wsgi.multiprocess"] is False
    assert errors.getvalue() == ""


def test_base_cgi_handler_uses_status_header_not_http_status_line():
    output = io.BytesIO()
    gateway = BaseCGIHandler(
        io.BytesIO(),
        output,
        io.StringIO(),
        BASE_ENVIRON.copy(),
        multithread=True,
        multiprocess=True,
    )

    def application(environ, start_response):
        start_response("204 No Content", [("Content-Length", "0")])
        return []

    gateway.run(application)
    assert output.getvalue().startswith(b"Status: 204 No Content\r\n")


def test_exception_before_headers_generates_generic_500_and_logs_details():
    output = io.BytesIO()
    errors = io.StringIO()
    gateway = SimpleHandler(
        io.BytesIO(),
        output,
        errors,
        BASE_ENVIRON.copy(),
        multithread=False,
        multiprocess=False,
    )

    def broken_application(environ, start_response):
        raise RuntimeError("internal detail")

    gateway.run(broken_application)

    assert b"500 Internal Server Error" in output.getvalue()
    assert gateway.error_body in output.getvalue()
    assert "RuntimeError: internal detail" in errors.getvalue()
    assert b"internal detail" not in output.getvalue()


def test_demo_app_is_a_complete_application_without_a_server():
    environ = {"CUSTOM_KEY": "custom value"}
    util.setup_testing_defaults(environ)
    responses = []

    def start_response(status, headers, exc_info=None):
        responses.append((status, headers, exc_info))
        return lambda data: None

    body = b"".join(simple_server.demo_app(environ, start_response))

    assert responses[0][0] == "200 OK"
    assert ("Content-Type", "text/plain; charset=utf-8") in responses[0][1]
    assert b"Hello world!" in body
    assert b"CUSTOM_KEY = 'custom value'" in body


def test_make_server_accepts_an_injected_non_network_server_class():
    created = []

    class SentinelHandler:
        pass

    class FakeServer:
        def __init__(self, address, handler_class):
            self.address = address
            self.handler_class = handler_class
            self.application = None
            created.append(self)

        def set_app(self, application):
            self.application = application

    def application(environ, start_response):
        return []

    server = simple_server.make_server(
        "127.0.0.1",
        8080,
        application,
        server_class=FakeServer,
        handler_class=SentinelHandler,
    )

    assert server is created[0]
    assert server.address == ("127.0.0.1", 8080)
    assert server.handler_class is SentinelHandler
    assert server.application is application


def test_wsgi_server_stores_application_without_initializing_socket():
    server = object.__new__(simple_server.WSGIServer)
    application = lambda environ, start_response: []

    server.set_app(application)
    assert server.get_app() is application
