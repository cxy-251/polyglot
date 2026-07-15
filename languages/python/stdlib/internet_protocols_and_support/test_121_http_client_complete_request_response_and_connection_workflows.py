"""121｜学习 http.client 的状态/头解析、请求发送、响应读取、复用与隧道完整流程。"""

from email.message import Message
from enum import IntEnum
from http import HTTPStatus
import http.client as http_client
from http.client import BadStatusLine
from http.client import CannotSendHeader
from http.client import CannotSendRequest
from http.client import HTTPConnection
from http.client import HTTPException
from http.client import HTTPMessage
from http.client import HTTPResponse
from http.client import HTTPSConnection
from http.client import IncompleteRead
from http.client import InvalidURL
from http.client import LineTooLong
from http.client import RemoteDisconnected
from http.client import ResponseNotReady
from http.client import UnknownProtocol
from http.client import parse_headers
from io import BytesIO
import ssl

import pytest


# polyglot-covers: python.http.HTTPStatus
# polyglot-covers: python.http.HTTPStatus-is-IntEnum
# polyglot-covers: python.http.HTTPStatus.value
# polyglot-covers: python.http.HTTPStatus.name
# polyglot-covers: python.http.HTTPStatus.phrase
# polyglot-covers: python.http.HTTPStatus.description
# polyglot-covers: python.http.HTTPStatus-integer-comparison
# polyglot-covers: python.http.HTTPStatus-lookup-by-code
# polyglot-covers: python.http.HTTPStatus-unknown-value-error
# polyglot-covers: python.http.client.status-code-constants
# polyglot-covers: python.http.client.responses
# polyglot-covers: python.http.client.HTTP_PORT
# polyglot-covers: python.http.client.HTTPS_PORT
# polyglot-covers: python.http.client.parse_headers
# polyglot-covers: python.http.client.parse_headers-binary-stream
# polyglot-covers: python.http.client.parse_headers-excludes-start-line
# polyglot-covers: python.http.client.parse_headers-leaves-body-position
# polyglot-covers: python.http.client.HTTPMessage
# polyglot-covers: python.http.client.HTTPMessage-is-email-message
# polyglot-covers: python.http.client.header-duplicates-get_all
# polyglot-covers: python.http.client.header-legacy-folding
# polyglot-covers: python.http.client.header-count-limit
# polyglot-covers: python.http.client.header-line-length-limit
# polyglot-covers: python.http.client.LineTooLong


def test_http_status_is_an_integer_enum_with_human_readable_metadata():
    status = HTTPStatus.NOT_FOUND

    assert isinstance(status, IntEnum)
    assert status == 404
    assert status.value == 404
    assert status.name == "NOT_FOUND"
    assert status.phrase == "Not Found"
    assert "Nothing matches" in status.description
    assert HTTPStatus(404) is status


def test_status_families_can_be_classified_by_integer_arithmetic():
    samples = {
        HTTPStatus.EARLY_HINTS: 1,
        HTTPStatus.CREATED: 2,
        HTTPStatus.PERMANENT_REDIRECT: 3,
        HTTPStatus.TOO_MANY_REQUESTS: 4,
        HTTPStatus.SERVICE_UNAVAILABLE: 5,
    }

    assert {status.value // 100 for status in samples} == set(samples.values())


def test_unknown_status_is_not_an_enum_member_but_legacy_mapping_is_available():
    with pytest.raises(ValueError):
        HTTPStatus(599)

    assert http_client.NOT_FOUND == HTTPStatus.NOT_FOUND == 404
    assert http_client.responses[http_client.NOT_FOUND] == "Not Found"
    assert http_client.responses[HTTPStatus.IM_A_TEAPOT] == "I'm a Teapot"
    assert (http_client.HTTP_PORT, http_client.HTTPS_PORT) == (80, 443)


def test_parse_headers_keeps_duplicates_and_leaves_stream_at_body():
    """parse_headers 只读 header 行，不负责消费 HTTP start-line。"""
    stream = BytesIO(
        b"X-Tag: first\r\n"
        b"X-Tag: second\r\n"
        b"X-Long: first\r\n"
        b" continuation\r\n"
        b"\r\n"
        b"body",
    )

    headers = parse_headers(stream)

    assert isinstance(headers, HTTPMessage)
    assert isinstance(headers, Message)
    assert headers.get_all("X-Tag") == ["first", "second"]
    assert headers["X-Long"] == "first\r\n continuation"
    assert headers.get_payload() == ""
    assert stream.read() == b"body"


def test_caller_consumes_status_line_before_parsing_headers():
    stream = BytesIO(
        b"HTTP/1.1 201 Created\r\n"
        b"Content-Length: 0\r\n"
        b"\r\n",
    )

    status_line = stream.readline()
    headers = parse_headers(stream)

    assert status_line == b"HTTP/1.1 201 Created\r\n"
    assert headers["Content-Length"] == "0"


def test_header_count_and_line_length_limits_raise_protocol_errors():
    too_many = BytesIO(
        b"".join(f"X-{index}: value\r\n".encode() for index in range(101))
        + b"\r\n",
    )
    too_long = BytesIO(b"X-Long: " + b"a" * 70_000 + b"\r\n\r\n")

    with pytest.raises(HTTPException):
        parse_headers(too_many)
    with pytest.raises(LineTooLong):
        parse_headers(too_long)

# 请求构造、framing、chunked 与低层发送状态机。


# polyglot-covers: python.http.client.HTTPConnection
# polyglot-covers: python.http.client.HTTPConnection-lazy-connect
# polyglot-covers: python.http.client.HTTPConnection-default-port
# polyglot-covers: python.http.client.HTTPConnection-host-port-splitting
# polyglot-covers: python.http.client.HTTPConnection-explicit-port
# polyglot-covers: python.http.client.HTTPConnection-ipv6-brackets
# polyglot-covers: python.http.client.HTTPConnection.timeout
# polyglot-covers: python.http.client.HTTPConnection.source_address-3.2
# polyglot-covers: python.http.client.HTTPConnection.blocksize-3.7
# polyglot-covers: python.http.client.HTTPSConnection
# polyglot-covers: python.http.client.HTTPSConnection-default-port
# polyglot-covers: python.http.client.empty-embedded-port-uses-default
# polyglot-covers: python.http.client.InvalidURL-nonnumeric-port
# polyglot-covers: python.http.client.HTTPConnection.request
# polyglot-covers: python.http.client.request-http11-line
# polyglot-covers: python.http.client.request-default-host
# polyglot-covers: python.http.client.request-default-accept-encoding-identity
# polyglot-covers: python.http.client.request-extra-headers
# polyglot-covers: python.http.client.request-bytes-content-length
# polyglot-covers: python.http.client.request-str-latin1
# polyglot-covers: python.http.client.request-str-nonlatin1-unicode-error
# polyglot-covers: python.http.client.request-bodyless-post-put-patch-length-zero
# polyglot-covers: python.http.client.request-bodyless-get-no-content-length
# polyglot-covers: python.http.client.request-explicit-content-length-preserved
# polyglot-covers: python.http.client.request-file-auto-chunked-3.6
# polyglot-covers: python.http.client.request-iterable-auto-chunked-3.6
# polyglot-covers: python.http.client.request-transfer-encoding-header
# polyglot-covers: python.http.client.endheaders.encode_chunked-3.6
# polyglot-covers: python.http.client.chunked-one-chunk-per-iteration
# polyglot-covers: python.http.client.chunked-one-chunk-per-file-read
# polyglot-covers: python.http.client.chunked-file-blocksize-3.7
# polyglot-covers: python.http.client.chunked-empty-chunks-ignored
# polyglot-covers: python.http.client.chunked-terminal-zero
# polyglot-covers: python.http.client.explicit-transfer-encoding-caller-responsibility
# polyglot-covers: python.http.client.HTTPConnection.putrequest
# polyglot-covers: python.http.client.HTTPConnection.putrequest.skip_host
# polyglot-covers: python.http.client.HTTPConnection.putrequest.skip_accept_encoding
# polyglot-covers: python.http.client.HTTPConnection.putheader
# polyglot-covers: python.http.client.putheader-multiple-arguments-continuation
# polyglot-covers: python.http.client.HTTPConnection.endheaders
# polyglot-covers: python.http.client.CannotSendHeader
# polyglot-covers: python.http.client.CannotSendRequest
# polyglot-covers: python.http.client.header-name-injection-rejected
# polyglot-covers: python.http.client.header-value-injection-rejected
# polyglot-covers: python.http.client.method-control-char-rejected
# polyglot-covers: python.http.client.url-control-char-invalid-url


class RecordingConnection(HTTPConnection):
    """用内存 transmission 列表代替 socket，同时保留 HTTPConnection 状态机。"""

    def __init__(self, blocksize=8192):
        super().__init__("example.test", blocksize=blocksize)
        self.transmissions = []

    def send(self, data):
        if isinstance(data, str):
            data = data.encode("iso-8859-1")
        self.transmissions.append(bytes(data))

    @property
    def wire(self):
        return b"".join(self.transmissions)


def body_bytes(connection):
    return connection.wire.split(b"\r\n\r\n", 1)[1]


def test_http_connection_parses_host_and_port_without_opening_socket():
    default = HTTPConnection("example.test")
    embedded = HTTPConnection("example.test:8080")
    explicit = HTTPConnection("example.test", 8000, timeout=2)
    ipv6 = HTTPConnection("[2001:db8::1]:9000")

    assert default.sock is None
    assert (default.host, default.port) == ("example.test", 80)
    assert (embedded.host, embedded.port) == ("example.test", 8080)
    assert (explicit.host, explicit.port, explicit.timeout) == (
        "example.test",
        8000,
        2,
    )
    assert (ipv6.host, ipv6.port) == ("2001:db8::1", 9000)


def test_connection_retains_source_blocksize_and_tls_context_configuration():
    connection = HTTPConnection(
        "example.test",
        source_address=("127.0.0.1", 0),
        blocksize=32_768,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    secure = HTTPSConnection("secure.test", context=context)

    assert connection.source_address == ("127.0.0.1", 0)
    assert connection.blocksize == 32_768
    assert secure.sock is None
    assert (secure.host, secure.port) == ("secure.test", 443)
    assert secure._context is context


def test_empty_embedded_port_uses_default_and_nonnumeric_port_is_invalid():
    connection = HTTPConnection("example.test:")
    assert (connection.host, connection.port) == ("example.test", 80)

    with pytest.raises(InvalidURL):
        HTTPConnection("example.test:not-a-port")


def test_bytes_request_gets_default_transport_headers_and_exact_length():
    connection = RecordingConnection()

    connection.request(
        "POST",
        "/submit?q=1",
        body=b"abc",
        headers={"X-Trace": "yes"},
    )

    head, body = connection.wire.split(b"\r\n\r\n", 1)
    assert head.startswith(b"POST /submit?q=1 HTTP/1.1\r\n")
    assert b"Host: example.test" in head
    assert b"Accept-Encoding: identity" in head
    assert b"Content-Length: 3" in head
    assert b"X-Trace: yes" in head
    assert body == b"abc"


def test_text_body_uses_latin1_and_nonlatin1_must_be_encoded_by_caller():
    connection = RecordingConnection()
    connection.request("PUT", "/word", body="café")

    assert b"Content-Length: 4" in connection.wire
    assert connection.wire.endswith(b"caf\xe9")

    with pytest.raises(UnicodeEncodeError):
        RecordingConnection().request("POST", "/text", body="中文")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
def test_body_expected_methods_send_zero_length_for_none(method):
    connection = RecordingConnection()
    connection.request(method, "/resource")
    assert b"Content-Length: 0" in connection.wire


def test_get_omits_length_and_explicit_length_is_not_recalculated():
    get_connection = RecordingConnection()
    get_connection.request("GET", "/resource")
    assert b"Content-Length:" not in get_connection.wire

    post_connection = RecordingConnection()
    post_connection.request(
        "POST",
        "/raw",
        body=b"abc",
        headers={"Content-Length": "99"},
    )
    assert b"Content-Length: 99" in post_connection.wire
    assert b"Content-Length: 3" not in post_connection.wire


def test_iterable_body_is_chunk_encoded_and_empty_items_are_ignored():
    connection = RecordingConnection()

    connection.request(
        "POST",
        "/stream",
        body=iter([b"abc", b"", b"d"]),
    )

    assert b"Transfer-Encoding: chunked" in connection.wire
    assert body_bytes(connection) == b"3\r\nabc\r\n1\r\nd\r\n0\r\n\r\n"


def test_file_body_reads_and_chunks_at_configured_blocksize():
    connection = RecordingConnection(blocksize=3)
    connection.request("POST", "/file", body=BytesIO(b"abcdefg"))

    assert body_bytes(connection) == (
        b"3\r\nabc\r\n"
        b"3\r\ndef\r\n"
        b"1\r\ng\r\n"
        b"0\r\n\r\n"
    )


def test_explicit_transfer_encoding_controls_who_formats_chunks():
    already_encoded = b"3\r\nabc\r\n0\r\n\r\n"
    caller_encoded = RecordingConnection()
    caller_encoded.request(
        "POST",
        "/manual",
        body=already_encoded,
        headers={"Transfer-Encoding": "chunked"},
        encode_chunked=False,
    )
    assert body_bytes(caller_encoded) == already_encoded

    library_encoded = RecordingConnection()
    library_encoded.request(
        "POST",
        "/encoded",
        body=[b"xy"],
        headers={"Transfer-Encoding": "chunked"},
        encode_chunked=True,
    )
    assert body_bytes(library_encoded) == b"2\r\nxy\r\n0\r\n\r\n"


def test_low_level_api_builds_request_and_can_skip_automatic_headers():
    connection = RecordingConnection()

    connection.putrequest(
        "OPTIONS",
        "*",
        skip_host=True,
        skip_accept_encoding=True,
    )
    connection.putheader("Host", "virtual.test")
    connection.putheader("X-Multi", "first", "second")
    connection.endheaders()

    assert connection.wire == (
        b"OPTIONS * HTTP/1.1\r\n"
        b"Host: virtual.test\r\n"
        b"X-Multi: first\r\n\tsecond\r\n"
        b"\r\n"
    )


def test_low_level_call_order_is_enforced_by_connection_state():
    connection = RecordingConnection()

    with pytest.raises(CannotSendHeader):
        connection.putheader("X-Test", "before-request")

    connection.putrequest("GET", "/")
    with pytest.raises(CannotSendRequest):
        connection.putrequest("GET", "/again")


@pytest.mark.parametrize(
    ("operation", "args"),
    [
        ("putrequest", ("GET\r\nX-Evil: yes", "/")),
        ("putrequest", ("GET", "/safe\r\nX-Evil: yes")),
        ("putheader", ("Bad\nName", "value")),
        ("putheader", ("X-Test", "value\r\nInjected: yes")),
    ],
)
def test_control_characters_cannot_inject_request_lines_or_headers(
    operation,
    args,
):
    connection = RecordingConnection()
    if operation == "putheader":
        connection.putrequest("GET", "/")

    with pytest.raises((ValueError, InvalidURL)):
        getattr(connection, operation)(*args)

# HTTPResponse 解析、正文 framing、连接策略与协议错误。


# polyglot-covers: python.http.client.HTTPResponse
# polyglot-covers: python.http.client.HTTPResponse.begin
# polyglot-covers: python.http.client.HTTPResponse.status
# polyglot-covers: python.http.client.HTTPResponse.reason
# polyglot-covers: python.http.client.HTTPResponse.version
# polyglot-covers: python.http.client.HTTPResponse.url
# polyglot-covers: python.http.client.HTTPResponse.headers
# polyglot-covers: python.http.client.HTTPResponse.msg
# polyglot-covers: python.http.client.HTTPResponse.getheader
# polyglot-covers: python.http.client.HTTPResponse.getheader-duplicates-joined
# polyglot-covers: python.http.client.HTTPResponse.getheader-iterable-default
# polyglot-covers: python.http.client.HTTPResponse.getheaders
# polyglot-covers: python.http.client.HTTPResponse.read
# polyglot-covers: python.http.client.HTTPResponse.readinto-3.3
# polyglot-covers: python.http.client.HTTPResponse-content-length-boundary
# polyglot-covers: python.http.client.HTTPResponse-iterable-lines
# polyglot-covers: python.http.client.HTTPResponse-context-manager
# polyglot-covers: python.http.client.HTTPResponse.chunked
# polyglot-covers: python.http.client.response-transfer-encoding-over-content-length
# polyglot-covers: python.http.client.response-chunk-size-hex
# polyglot-covers: python.http.client.response-chunk-extension-ignored
# polyglot-covers: python.http.client.response-chunked-read
# polyglot-covers: python.http.client.response-chunked-readinto
# polyglot-covers: python.http.client.response-chunked-terminal-zero
# polyglot-covers: python.http.client.response-trailers-consumed-not-exposed
# polyglot-covers: python.http.client.response-invalid-chunk-size-incomplete-read
# polyglot-covers: python.http.client.response-short-chunk-incomplete-read
# polyglot-covers: python.http.client.response-head-has-no-body
# polyglot-covers: python.http.client.response-204-has-no-body
# polyglot-covers: python.http.client.response-304-has-no-body
# polyglot-covers: python.http.client.response-content-length-forced-zero
# polyglot-covers: python.http.client.response-100-continue-skipped
# polyglot-covers: python.http.client.response-final-after-interim
# polyglot-covers: python.http.client.response-http11-persistent-default
# polyglot-covers: python.http.client.response-connection-close
# polyglot-covers: python.http.client.response-http10-closes-default
# polyglot-covers: python.http.client.response-http10-keep-alive
# polyglot-covers: python.http.client.response-no-length-forces-close-delimiting
# polyglot-covers: python.http.client.RemoteDisconnected-3.5
# polyglot-covers: python.http.client.RemoteDisconnected-is-ConnectionResetError
# polyglot-covers: python.http.client.RemoteDisconnected-is-BadStatusLine
# polyglot-covers: python.http.client.BadStatusLine
# polyglot-covers: python.http.client.UnknownProtocol
# polyglot-covers: python.http.client.LineTooLong-status-line
# polyglot-covers: python.http.client.IncompleteRead
# polyglot-covers: python.http.client.IncompleteRead.partial
# polyglot-covers: python.http.client.IncompleteRead.expected
# polyglot-covers: python.http.client.fixed-length-unbounded-read-is-strict
# polyglot-covers: python.http.client.fixed-length-bounded-read-short-eof-compatible


class MemorySocket:
    def __init__(self, incoming):
        self.reader = BytesIO(incoming)

    def makefile(self, mode):
        assert mode == "rb"
        return self.reader


def make_response(raw, method="GET", url="https://example.test/resource"):
    response = HTTPResponse(MemorySocket(raw), method=method, url=url)
    response.begin()
    return response


def response_for(raw):
    """构造但不 begin，供验证状态行解析错误使用。"""
    return HTTPResponse(MemorySocket(raw))


def test_fixed_length_response_exposes_metadata_and_buffered_reads():
    response = make_response(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 11\r\n"
        b"X-Tag: first\r\n"
        b"X-Tag: second\r\n"
        b"\r\n"
        b"hello worldEXTRA",
    )

    assert (response.status, response.reason, response.version) == (200, "OK", 11)
    assert response.url == "https://example.test/resource"
    assert isinstance(response.headers, HTTPMessage)
    assert response.msg is response.headers
    assert response.getheader("X-Tag") == "first, second"
    assert response.getheader("Missing", ["one", "two"]) == "one, two"
    assert response.getheaders().count(("X-Tag", "first")) == 1

    assert response.read(5) == b"hello"
    target = bytearray(8)
    count = response.readinto(target)
    assert count == 6
    assert target[:count] == b" world"
    assert response.read() == b""


def test_response_iteration_uses_binary_lines_and_context_closes_stream():
    response = make_response(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 11\r\n"
        b"\r\n"
        b"one\ntwo\nend"
    )

    with response as opened:
        assert list(opened) == [b"one\n", b"two\n", b"end"]
    assert response.closed


def test_chunked_response_ignores_extensions_and_hides_trailers():
    response = make_response(
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"Content-Length: 999\r\n"
        b"X-Origin: yes\r\n"
        b"\r\n"
        b"4;name=value\r\nWiki\r\n"
        b"5\r\npedia\r\n"
        b"0\r\nX-Trailer: discarded\r\n\r\n",
    )

    assert response.chunked is True
    assert response.length is None
    assert response.read() == b"Wikipedia"
    assert response.getheader("X-Origin") == "yes"
    assert response.getheader("X-Trailer") is None


def test_chunked_readinto_crosses_chunk_boundaries():
    response = make_response(
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
        b"2\r\nab\r\n3\r\ncde\r\n0\r\n\r\n",
    )
    target = bytearray(5)

    count = response.readinto(target)

    assert count == 5
    assert target == b"abcde"


def test_invalid_chunk_size_and_short_chunk_raise_incomplete_read():
    invalid_size = make_response(
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
        b"ZZ\r\n",
    )
    short_chunk = make_response(
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
        b"5\r\nabc",
    )

    with pytest.raises(IncompleteRead) as invalid:
        invalid_size.read()
    with pytest.raises(IncompleteRead) as short:
        short_chunk.read()

    # 3.10 只把此前完整 chunk 计入 partial，坏 chunk 的零散字节不会混入。
    assert invalid.value.partial == b""
    assert short.value.partial == b""


def test_head_and_bodyless_statuses_ignore_claimed_content_length():
    head = make_response(
        b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nunread-body",
        method="HEAD",
    )
    no_content = make_response(
        b"HTTP/1.1 204 No Content\r\nContent-Length: 10\r\n\r\n",
    )
    not_modified = make_response(
        b"HTTP/1.1 304 Not Modified\r\nContent-Length: 10\r\n\r\n",
    )

    assert (head.length, no_content.length, not_modified.length) == (0, 0, 0)
    assert head.read() == b""
    assert no_content.read() == b""
    assert not_modified.read() == b""


def test_begin_skips_100_continue_and_uses_the_final_response():
    response = make_response(
        b"HTTP/1.1 100 Continue\r\nX-Interim: ignored\r\n\r\n"
        b"HTTP/1.1 201 Created\r\nContent-Length: 2\r\n\r\nok",
    )

    assert (response.status, response.reason) == (201, "Created")
    assert response.getheader("X-Interim") is None
    assert response.read() == b"ok"


def test_version_headers_and_length_determine_connection_reuse():
    persistent = make_response(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    explicit_close = make_response(
        b"HTTP/1.1 200 OK\r\nConnection: close\r\nContent-Length: 0\r\n\r\n",
    )
    old_default = make_response(b"HTTP/1.0 200 OK\r\nContent-Length: 0\r\n\r\n")
    old_keep_alive = make_response(
        b"HTTP/1.0 200 OK\r\nConnection: Keep-Alive\r\n"
        b"Content-Length: 0\r\n\r\n",
    )
    close_delimited = make_response(b"HTTP/1.1 200 OK\r\n\r\nbody")

    assert persistent.will_close is False
    assert explicit_close.will_close is True
    assert old_default.will_close is True
    assert old_keep_alive.will_close is False
    assert close_delimited.will_close is True
    assert close_delimited.read() == b"body"


def test_empty_peer_response_has_a_specific_multiple_inheritance_error():
    response = response_for(b"")

    with pytest.raises(RemoteDisconnected) as captured:
        response.begin()

    assert isinstance(captured.value, ConnectionResetError)
    assert isinstance(captured.value, BadStatusLine)


@pytest.mark.parametrize(
    ("status_line", "error_type"),
    [
        (b"not-http 200 OK\r\n", BadStatusLine),
        (b"HTTP/1.1 xyz Bad\r\n", BadStatusLine),
        (b"HTTP/2.0 200 OK\r\n", UnknownProtocol),
    ],
)
def test_bad_status_syntax_and_unknown_protocol_are_distinguished(
    status_line,
    error_type,
):
    response = response_for(status_line + b"\r\n")

    with pytest.raises(error_type):
        response.begin()


def test_excessively_long_status_line_is_rejected():
    response = response_for(b"HTTP/1.1 200 " + b"x" * 70_000 + b"\r\n")
    with pytest.raises(LineTooLong):
        response.begin()


def test_unbounded_fixed_length_read_reports_partial_and_missing_count():
    response = make_response(
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nabc",
    )

    with pytest.raises(IncompleteRead) as captured:
        response.read()

    assert captured.value.partial == b"abc"
    assert captured.value.expected == 2


def test_bounded_read_keeps_legacy_short_eof_behavior_without_exception():
    response = make_response(
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nabc",
    )

    assert response.read(5) == b"abc"
    assert response.read(1) == b""

# HTTPConnection 响应状态、复用、断连恢复、关闭与 CONNECT 隧道。


# polyglot-covers: python.http.client.HTTPConnection.getresponse
# polyglot-covers: python.http.client.ResponseNotReady
# polyglot-covers: python.http.client.connection-second-request-after-response-headers
# polyglot-covers: python.http.client.connection-second-response-waits-for-first-body
# polyglot-covers: python.http.client.connection-read-full-response-before-next-response
# polyglot-covers: python.http.client.connection-persistent-reuse
# polyglot-covers: python.http.client.connection-error-resets-for-reconnect-3.5
# polyglot-covers: python.http.client.HTTPConnection.connect-lazy
# polyglot-covers: python.http.client.HTTPConnection.close
# polyglot-covers: python.http.client.HTTPConnection.set_tunnel-3.2
# polyglot-covers: python.http.client.connect-tunnel-proxy-vs-endpoint
# polyglot-covers: python.http.client.connect-tunnel-http10-python310
# polyglot-covers: python.http.client.connect-tunnel-explicit-headers
# polyglot-covers: python.http.client.connect-tunnel-no-auto-host-python310
# polyglot-covers: python.http.client.connect-tunnel-success-200
# polyglot-covers: python.http.client.connect-tunnel-non200-oserror
# polyglot-covers: python.http.client.set-tunnel-after-connect-runtime-error
# polyglot-covers: python.http.client.tunnel-host-control-char-rejected


class SharedReader:
    """关闭响应 reader 时不关闭底层共享输入，模拟持久连接上的下一响应。"""

    def __init__(self, source):
        self.source = source
        self.closed = False

    def read(self, size=-1):
        return self.source.read(size)

    def readline(self, size=-1):
        return self.source.readline(size)

    def readinto(self, target):
        return self.source.readinto(target)

    def read1(self, size=-1):
        return self.source.read(size)

    def peek(self, size=-1):
        position = self.source.tell()
        data = self.source.read() if size < 0 else self.source.read(size)
        self.source.seek(position)
        return data

    def flush(self):
        return None

    def close(self):
        self.closed = True


class DuplexSocket:
    def __init__(self, incoming):
        self.source = BytesIO(incoming)
        self.sent = []
        self.closed = False

    def makefile(self, mode):
        return SharedReader(self.source)

    def sendall(self, data):
        self.sent.append(bytes(data))

    def close(self):
        self.closed = True


class QueueConnection(HTTPConnection):
    def __init__(self, incoming_connections):
        super().__init__("example.test")
        self.pending = [DuplexSocket(data) for data in incoming_connections]
        self.used = []

    def connect(self):
        self.sock = self.pending.pop(0)
        self.used.append(self.sock)


class TunnelSocket:
    def __init__(self, response):
        self.reader = BytesIO(response)
        self.sent = []
        self.closed = False

    def makefile(self, mode):
        return self.reader

    def sendall(self, data):
        self.sent.append(bytes(data))

    def close(self):
        self.closed = True


class TunnelConnection(HTTPConnection):
    def __init__(self, response):
        super().__init__("proxy.test", 8080)
        self.transport = TunnelSocket(response)

    def connect(self):
        self.sock = self.transport
        if self._tunnel_host:
            self._tunnel()


def test_next_request_may_send_after_headers_but_response_waits_for_body():
    incoming = (
        b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\none"
        b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\ntwo"
    )
    connection = QueueConnection([incoming])
    connection.request("GET", "/one")
    first = connection.getresponse()

    connection.request("GET", "/two")
    with pytest.raises(ResponseNotReady):
        connection.getresponse()

    assert first.read() == b"one"
    second = connection.getresponse()
    assert second.read() == b"two"
    assert len(connection.used) == 1


def test_remote_disconnect_resets_for_a_later_lazy_reconnect():
    connection = QueueConnection(
        [
            b"",
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok",
        ],
    )
    connection.request("GET", "/first")

    with pytest.raises(RemoteDisconnected):
        connection.getresponse()

    assert connection.sock is None
    connection.request("GET", "/retry")
    assert connection.getresponse().read() == b"ok"
    assert len(connection.used) == 2


def test_close_releases_socket_and_resets_state():
    connection = QueueConnection([b""])
    connection.request("GET", "/pending")
    socket = connection.used[0]

    connection.close()

    assert connection.sock is None
    assert socket.closed


def test_successful_tunnel_sends_endpoint_and_explicit_proxy_headers():
    connection = TunnelConnection(
        b"HTTP/1.0 200 Connection established\r\n"
        b"Proxy-Agent: memory\r\n\r\n",
    )
    connection.set_tunnel(
        "origin.test",
        443,
        {"Proxy-Authorization": "Basic token"},
    )

    connection.connect()

    wire = b"".join(connection.transport.sent)
    assert wire == (
        b"CONNECT origin.test:443 HTTP/1.0\r\n"
        b"Proxy-Authorization: Basic token\r\n"
        b"\r\n"
    )
    assert b"Host:" not in wire


def test_non_200_tunnel_response_closes_connection_and_reports_status():
    connection = TunnelConnection(
        b"HTTP/1.0 407 Proxy Authentication Required\r\n\r\n",
    )
    connection.set_tunnel("origin.test", 443)

    with pytest.raises(OSError, match="407"):
        connection.connect()

    assert connection.sock is None
    assert connection.transport.closed


def test_tunnel_must_be_configured_before_socket_exists():
    connection = TunnelConnection(b"")
    connection.sock = connection.transport

    with pytest.raises(RuntimeError):
        connection.set_tunnel("origin.test", 443)


def test_tunnel_target_rejects_control_characters_before_sending():
    connection = TunnelConnection(b"")
    connection.set_tunnel("origin.test\r\nX-Evil: yes", 443)

    with pytest.raises(ValueError):
        connection.connect()

    assert connection.transport.sent == []
