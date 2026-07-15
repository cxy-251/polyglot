"""学习 urllib.request 请求对象及 HTTP 预处理产生的 wire framing。

Request 的 URL、方法、头部和 data 都会影响后续 handler 塑形，因此集中展示从构造请求到
生成 Host、Content-Length 或 chunked 头的完整过程。测试不建立网络连接。
"""

import base64
import os
import urllib.request as urllib_request
from email.message import Message
from http.cookiejar import CookieJar
from io import BytesIO
from types import SimpleNamespace
from urllib.error import ContentTooShortError, HTTPError, URLError
from urllib.request import (
    BaseHandler,
    FileHandler,
    HTTPBasicAuthHandler,
    HTTPCookieProcessor,
    HTTPDefaultErrorHandler,
    HTTPDigestAuthHandler,
    HTTPErrorProcessor,
    HTTPHandler,
    HTTPPasswordMgr,
    HTTPPasswordMgrWithDefaultRealm,
    HTTPPasswordMgrWithPriorAuth,
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyDigestAuthHandler,
    ProxyHandler,
    Request,
    UnknownHandler,
    build_opener,
    pathname2url,
    url2pathname,
)
from urllib.response import addinfourl

import pytest


# polyglot-covers: python.urllib.request.Request
# polyglot-covers: python.urllib.request.Request.full_url
# polyglot-covers: python.urllib.request.Request.full_url-property-set-delete
# polyglot-covers: python.urllib.request.Request.type
# polyglot-covers: python.urllib.request.Request.host
# polyglot-covers: python.urllib.request.Request.selector
# polyglot-covers: python.urllib.request.Request.origin_req_host
# polyglot-covers: python.urllib.request.Request.unverifiable
# polyglot-covers: python.urllib.request.Request.data
# polyglot-covers: python.urllib.request.Request.get_method-get-post
# polyglot-covers: python.urllib.request.Request.explicit-method
# polyglot-covers: python.urllib.request.Request.subclass-default-method
# polyglot-covers: python.urllib.request.Request.add_header
# polyglot-covers: python.urllib.request.Request.header-name-canonicalization
# polyglot-covers: python.urllib.request.Request.same-header-overwrites
# polyglot-covers: python.urllib.request.Request.add_unredirected_header
# polyglot-covers: python.urllib.request.Request.has_header
# polyglot-covers: python.urllib.request.Request.get_header
# polyglot-covers: python.urllib.request.Request.get_header-default
# polyglot-covers: python.urllib.request.Request.header_items
# polyglot-covers: python.urllib.request.Request.remove_header-3.4
# polyglot-covers: python.urllib.request.Request.data-change-removes-content-length-3.4
# polyglot-covers: python.urllib.request.HTTPHandler.http_request
# polyglot-covers: python.urllib.request.http-request-default-host
# polyglot-covers: python.urllib.request.http-request-default-user-agent
# polyglot-covers: python.urllib.request.http-request-default-content-type
# polyglot-covers: python.urllib.request.http-request-bytes-content-length
# polyglot-covers: python.urllib.request.http-request-iterable-chunked-3.6
# polyglot-covers: python.urllib.request.http-request-explicit-framing-preserved
# polyglot-covers: python.urllib.request.http-request-str-body-type-error
# polyglot-covers: python.urllib.request.request-body-retry-one-shot-iterator-trap


def make_preprocessor():
    handler = HTTPHandler()
    handler.add_parent(
        SimpleNamespace(addheaders=[("User-agent", "polyglot-reader/1.0")]),
    )
    return handler


def test_request_exposes_url_and_transport_components_separately():
    request = Request(
        "https://example.test:8443/docs/page?q=python#intro",
        origin_req_host="origin.test",
        unverifiable=True,
    )

    assert request.full_url == (
        "https://example.test:8443/docs/page?q=python#intro"
    )
    assert request.get_full_url() == request.full_url
    assert request.type == "https"
    assert request.host == "example.test:8443"
    assert request.selector == "/docs/page?q=python"
    assert request.origin_req_host == "origin.test"
    assert request.unverifiable is True


def test_method_default_follows_body_but_explicit_or_subclass_method_wins():
    get_request = Request("https://example.test/items")
    post_request = Request("https://example.test/items", data=b"q=python")
    put_request = Request(
        "https://example.test/items/1",
        data=b"updated",
        method="PUT",
    )

    class PatchRequest(Request):
        method = "PATCH"

    assert get_request.get_method() == "GET"
    assert post_request.get_method() == "POST"
    assert put_request.get_method() == "PUT"
    assert PatchRequest("https://example.test/items/1").get_method() == "PATCH"


def test_full_url_setter_reparses_components_and_deleter_clears_them():
    request = Request("https://example.test/old")

    request.full_url = "http://other.test/new#part"
    assert (request.type, request.host, request.selector) == (
        "http",
        "other.test",
        "/new",
    )
    assert request.full_url.endswith("#part")

    del request.full_url
    assert request.full_url is None
    assert request.selector == ""


def test_regular_headers_are_canonicalized_and_later_values_overwrite():
    request = Request(
        "https://example.test/",
        headers={"user-agent": "reader/1.0"},
    )
    request.add_header("X-Trace", "first")
    request.add_header("x-trace", "second")

    assert request.get_header("User-agent") == "reader/1.0"
    assert request.get_header("X-trace") == "second"
    assert request.get_header("Missing", "fallback") == "fallback"
    assert dict(request.header_items()) == {
        "User-agent": "reader/1.0",
        "X-trace": "second",
    }


def test_unredirected_headers_participate_in_lookup_and_removal():
    request = Request("https://example.test/private")
    request.add_unredirected_header("Authorization", "Bearer secret")

    assert request.has_header("Authorization")
    assert request.get_header("Authorization") == "Bearer secret"
    request.remove_header("Authorization")
    assert not request.has_header("Authorization")


def test_replacing_data_invalidates_an_old_content_length():
    """继续使用旧长度可能截断请求或等待不存在的字节，setter 会主动删除它。"""
    request = Request("https://example.test/upload", data=b"old")
    request.add_unredirected_header("Content-Length", "3")

    request.data = b"a longer replacement"

    assert request.get_header("Content-length") is None
    assert request.data == b"a longer replacement"


def test_bytes_body_gets_content_length_and_form_content_type():
    request = Request("http://example.test/submit", data=b"q=python")

    processed = make_preprocessor().http_request(request)

    assert processed is request
    assert request.get_header("Host") == "example.test"
    assert request.get_header("User-agent") == "polyglot-reader/1.0"
    assert request.get_header("Content-type") == (
        "application/x-www-form-urlencoded"
    )
    assert request.get_header("Content-length") == "8"
    assert request.get_header("Transfer-encoding") is None


def test_unknown_length_iterator_uses_chunked_framing_without_caching():
    chunks = iter([b"first", b"second"])
    request = Request("http://example.test/upload", data=chunks)

    make_preprocessor().http_request(request)

    assert request.get_header("Content-length") is None
    assert request.get_header("Transfer-encoding") == "chunked"
    # 认证或重定向重试时，一次性迭代器已被消费；调用方必须重新提供内容。
    assert request.data is chunks


def test_explicit_content_headers_are_not_overwritten():
    request = Request(
        "http://example.test/json",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "Content-Length": "2",
        },
    )

    make_preprocessor().http_request(request)

    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Content-length") == "2"


def test_text_body_must_be_encoded_by_the_caller():
    request = Request("http://example.test/submit", data="q=中文")

    with pytest.raises(TypeError):
        make_preprocessor().http_request(request)


# 学习 urllib.request 的代理配置、opener 三阶段管线和全局委托。
#
# 代理是 opener 中的一类 handler；请求预处理、传输 fallback 与响应后处理再由
# OpenerDirector 排序执行。集中阅读可以看清环境配置最终如何进入请求处理管线。


# polyglot-covers: python.urllib.request.pathname2url
# polyglot-covers: python.urllib.request.url2pathname
# polyglot-covers: python.urllib.request.getproxies
# polyglot-covers: python.urllib.request.getproxies-case-insensitive
# polyglot-covers: python.urllib.request.getproxies-lowercase-wins
# polyglot-covers: python.urllib.request.getproxies-cgi-http-proxy-defense
# polyglot-covers: python.urllib.request.ProxyHandler
# polyglot-covers: python.urllib.request.ProxyHandler-empty-disables-autodetection
# polyglot-covers: python.urllib.request.ProxyHandler.proxy_open
# polyglot-covers: python.urllib.request.Request.set_proxy
# polyglot-covers: python.urllib.request.proxy-basic-credentials-header
# polyglot-covers: python.urllib.request.OpenerDirector
# polyglot-covers: python.urllib.request.OpenerDirector.add_handler
# polyglot-covers: python.urllib.request.OpenerDirector.open
# polyglot-covers: python.urllib.request.OpenerDirector.handler_order
# polyglot-covers: python.urllib.request.opener-request-preprocessing-stage
# polyglot-covers: python.urllib.request.opener-default-open-first
# polyglot-covers: python.urllib.request.opener-protocol-open-fallback
# polyglot-covers: python.urllib.request.opener-open-non-none-short-circuit
# polyglot-covers: python.urllib.request.opener-unknown-open-last
# polyglot-covers: python.urllib.request.opener-response-postprocessing-stage
# polyglot-covers: python.urllib.request.BaseHandler.add_parent
# polyglot-covers: python.urllib.request.build_opener
# polyglot-covers: python.urllib.request.build_opener-handler-class-instantiation
# polyglot-covers: python.urllib.request.build_opener-default-handlers
# polyglot-covers: python.urllib.request.build_opener-subclass-replaces-default
# polyglot-covers: python.urllib.request.install_opener
# polyglot-covers: python.urllib.request.install_opener-duck-typed
# polyglot-covers: python.urllib.request.urlopen
# polyglot-covers: python.urllib.request.urlopen-global-opener-delegation


class DemoRequestProcessor(BaseHandler):
    handler_order = 100

    def __init__(self, trace):
        self.trace = trace

    def demo_request(self, request):
        self.trace.append("request")
        request.add_header("X-Prepared", "yes")
        return request


class DefaultDecliner(BaseHandler):
    handler_order = 200

    def __init__(self, trace):
        self.trace = trace

    def default_open(self, request):
        self.trace.append("default")
        return None


class DemoTransport(BaseHandler):
    handler_order = 300

    def __init__(self, trace):
        self.trace = trace

    def demo_open(self, request):
        self.trace.append(("protocol", request.get_header("X-prepared")))
        return BytesIO(b"payload")


class UnknownCatcher(BaseHandler):
    handler_order = 400

    def __init__(self, trace):
        self.trace = trace

    def unknown_open(self, request):
        self.trace.append("unknown")
        return BytesIO(b"fallback")


class DemoResponseProcessor(BaseHandler):
    handler_order = 500

    def __init__(self, trace):
        self.trace = trace

    def demo_response(self, request, response):
        self.trace.append("response")
        response.processed = True
        return response


class MemoryHandler(BaseHandler):
    constructed = 0

    def __init__(self):
        type(self).constructed += 1

    def memory_open(self, request):
        return BytesIO(request.selector.encode("ascii"))


class OfflineResponse(BytesIO):
    code = 200
    msg = "OK"

    def info(self):
        return Message()


class OfflineHTTPHandler(HTTPHandler):
    def http_open(self, request):
        return OfflineResponse(b"offline")


def test_posix_path_conversion_quotes_only_the_path_component():
    path = "/tmp/有 空格.txt"
    encoded = pathname2url(path)

    assert encoded == "/tmp/%E6%9C%89%20%E7%A9%BA%E6%A0%BC.txt"
    assert url2pathname(encoded) == path


def test_lowercase_environment_proxy_wins_over_uppercase(monkeypatch):
    monkeypatch.setattr(
        os,
        "environ",
        {
            "HTTP_PROXY": "http://upper.test:8000",
            "http_proxy": "http://lower.test:8001",
            "HTTPS_PROXY": "http://secure.test:8443",
        },
    )

    proxies = urllib_request.getproxies()

    assert proxies["http"] == "http://lower.test:8001"
    assert proxies["https"] == "http://secure.test:8443"


def test_cgi_ignores_only_the_injectable_uppercase_http_proxy(monkeypatch):
    monkeypatch.setattr(
        os,
        "environ",
        {
            "REQUEST_METHOD": "GET",
            "HTTP_PROXY": "http://attacker.test:8000",
            "HTTPS_PROXY": "http://secure.test:8443",
        },
    )

    proxies = urllib_request.getproxies()

    assert "http" not in proxies
    assert proxies["https"] == "http://secure.test:8443"


def test_empty_proxy_mapping_disables_discovery():
    handler = ProxyHandler({})

    assert handler.proxies == {}
    assert not hasattr(handler, "http_open")


def test_explicit_proxy_rewrites_target_and_adds_credentials(monkeypatch):
    monkeypatch.setattr(urllib_request, "proxy_bypass", lambda host: False)
    handler = ProxyHandler(
        {"http": "http://alice:secret@proxy.test:8080"},
    )
    request = Request("http://origin.test/path?q=1")

    assert handler.http_open(request) is None

    expected = base64.b64encode(b"alice:secret").decode("ascii")
    assert request.host == "proxy.test:8080"
    assert request.selector == "http://origin.test/path?q=1"
    assert request.get_header("Proxy-authorization") == f"Basic {expected}"


def test_opener_runs_three_stages_and_short_circuits_after_success():
    trace = []
    opener = OpenerDirector()
    for handler in (
        DemoResponseProcessor(trace),
        UnknownCatcher(trace),
        DemoTransport(trace),
        DefaultDecliner(trace),
        DemoRequestProcessor(trace),
    ):
        opener.add_handler(handler)

    response = opener.open("demo://example.test/resource")

    assert response.read() == b"payload"
    assert response.processed is True
    assert trace == [
        "request",
        "default",
        ("protocol", "yes"),
        "response",
    ]


def test_unknown_open_runs_only_after_default_and_protocol_decline():
    trace = []
    opener = OpenerDirector()
    opener.add_handler(DefaultDecliner(trace))
    opener.add_handler(UnknownCatcher(trace))

    response = opener.open("missing://example.test/resource")

    assert response.read() == b"fallback"
    assert trace == ["default", "unknown"]


def test_build_opener_instantiates_classes_and_adds_defaults():
    MemoryHandler.constructed = 0
    opener = build_opener(ProxyHandler({}), MemoryHandler)

    assert MemoryHandler.constructed == 1
    assert opener.open("memory://example.test/value").read() == b"/value"
    assert any(type(handler) is HTTPHandler for handler in opener.handlers)


def test_custom_subclass_replaces_its_corresponding_default_handler():
    opener = build_opener(ProxyHandler({}), OfflineHTTPHandler)
    http_handlers = [
        handler
        for handler in opener.handlers
        if isinstance(handler, HTTPHandler)
    ]

    assert len(http_handlers) == 1
    assert type(http_handlers[0]) is OfflineHTTPHandler
    assert opener.open("http://example.test/").read() == b"offline"


def test_urlopen_delegates_to_an_installed_duck_typed_opener(monkeypatch):
    calls = []
    sentinel = object()

    class DuckOpener:
        def open(self, url, data, timeout):
            calls.append((url, data, timeout))
            return sentinel

    monkeypatch.setattr(urllib_request, "_opener", None)
    urllib_request.install_opener(DuckOpener())

    result = urllib_request.urlopen(
        "memory://example.test/resource",
        data=b"body",
        timeout=2.5,
    )

    assert result is sentinel
    assert calls == [
        ("memory://example.test/resource", b"body", 2.5),
    ]


# 学习 urllib.request 的本地资源 handler、下载落盘、短读与清理流程。


# polyglot-covers: python.urllib.request.DataHandler
# polyglot-covers: python.urllib.request.DataHandler.data_open
# polyglot-covers: python.urllib.request.data-url-default-media-type
# polyglot-covers: python.urllib.request.data-url-percent-decoding
# polyglot-covers: python.urllib.request.data-url-base64
# polyglot-covers: python.urllib.request.data-url-base64-whitespace
# polyglot-covers: python.urllib.request.data-url-missing-padding-value-error
# polyglot-covers: python.urllib.request.data-url-media-control-char-rejected
# polyglot-covers: python.urllib.request.FileHandler
# polyglot-covers: python.urllib.request.FileHandler.file_open
# polyglot-covers: python.urllib.request.file-url-local-workflow
# polyglot-covers: python.urllib.request.file-url-remote-host-rejected
# polyglot-covers: python.urllib.request.local-response-is-bytes
# polyglot-covers: python.urllib.request.urlretrieve
# polyglot-covers: python.urllib.request.urlretrieve-explicit-filename
# polyglot-covers: python.urllib.request.urlretrieve-return-filename-headers
# polyglot-covers: python.urllib.request.urlretrieve-reporthook-initial-and-block
# polyglot-covers: python.urllib.request.urlretrieve-content-length-lower-bound
# polyglot-covers: python.urllib.request.urlretrieve-short-read-error
# polyglot-covers: python.urllib.request.urlretrieve-partial-file-remains
# polyglot-covers: python.urllib.request.urlcleanup
# polyglot-covers: python.urllib.request.urlcleanup-managed-tempfiles


class MemoryResponse(BytesIO):
    def __init__(self, body, headers):
        super().__init__(body)
        self._headers = headers

    def info(self):
        return self._headers


def test_data_url_defaults_to_plain_ascii_and_returns_bytes():
    opener = build_opener(ProxyHandler({}))

    with opener.open("data:,hello%20world") as response:
        assert response.read() == b"hello world"
        assert response.headers["Content-type"] == (
            "text/plain;charset=US-ASCII"
        )
        assert response.headers["Content-length"] == "11"


def test_base64_data_url_ignores_wrapping_whitespace():
    opener = build_opener(ProxyHandler({}))

    with opener.open(
        "data:application/octet-stream;base64,AAEC\n/w==",
    ) as response:
        assert response.read() == b"\x00\x01\x02\xff"
        assert response.headers.get_content_type() == "application/octet-stream"


def test_bad_base64_padding_and_control_char_media_type_are_rejected():
    opener = build_opener(ProxyHandler({}))

    with pytest.raises(ValueError):
        opener.open("data:text/plain;base64,SGVsbG8")
    with pytest.raises(ValueError):
        opener.open("data:text/plain\nevil,content")


def test_file_url_reads_only_a_local_temporary_file(tmp_path):
    target = tmp_path / "中文 example.txt"
    target.write_bytes("本地内容".encode("utf-8"))
    opener = build_opener(ProxyHandler({}))

    with opener.open(target.as_uri()) as response:
        assert response.read().decode("utf-8") == "本地内容"
        assert int(response.headers["Content-length"]) == target.stat().st_size


def test_file_handler_rejects_a_nonlocal_authority_without_dns(monkeypatch):
    handler = FileHandler()
    monkeypatch.setattr(handler, "get_names", lambda: ("127.0.0.1",))
    request = Request("file://remote.test/private/file.txt")

    with pytest.raises(URLError):
        handler.file_open(request)


def test_urlretrieve_writes_data_url_and_reports_initial_and_read_blocks(tmp_path):
    """reporthook 在读前收到 block 0，此后每次读块再调用一次。"""
    destination = tmp_path / "download.txt"
    progress = []

    filename, headers = urllib_request.urlretrieve(
        "data:text/plain;charset=utf-8,%E4%B8%AD%E6%96%87",
        str(destination),
        reporthook=lambda count, size, total: progress.append(
            (count, size, total),
        ),
    )

    assert filename == str(destination)
    assert destination.read_bytes() == "中文".encode("utf-8")
    assert headers.get_content_type() == "text/plain"
    assert progress[0] == (0, 8192, 6)
    assert progress[-1] == (1, 8192, 6)


def test_short_read_keeps_partial_filename_and_headers(tmp_path, monkeypatch):
    """Content-Length 是下限，少读会抛错但保留已写文件供诊断或恢复。"""
    headers = Message()
    headers["Content-Length"] = "10"
    monkeypatch.setattr(
        urllib_request,
        "urlopen",
        lambda url, data=None: MemoryResponse(b"abc", headers),
    )
    destination = tmp_path / "partial.bin"

    with pytest.raises(ContentTooShortError) as captured:
        urllib_request.urlretrieve(
            "http://example.test/file",
            str(destination),
        )

    partial_name, partial_headers = captured.value.content
    assert partial_name == str(destination)
    assert partial_headers is headers
    assert destination.read_bytes() == b"abc"


def test_urlcleanup_removes_only_registered_temporary_files(tmp_path, monkeypatch):
    managed = tmp_path / "managed.tmp"
    unrelated = tmp_path / "unrelated.tmp"
    managed.write_bytes(b"temporary")
    unrelated.write_bytes(b"keep")
    registered = [str(managed)]
    monkeypatch.setattr(urllib_request, "_url_tempfiles", registered)
    monkeypatch.setattr(urllib_request, "_opener", object())

    urllib_request.urlcleanup()

    assert not managed.exists()
    assert unrelated.exists()
    assert registered == []
    assert urllib_request._opener is None


# 学习 urllib.request 中会跨请求传递状态的重定向与 Cookie handler。


# polyglot-covers: python.urllib.request.HTTPRedirectHandler
# polyglot-covers: python.urllib.request.HTTPRedirectHandler.redirect_request
# polyglot-covers: python.urllib.request.redirect-post-301-302-303-becomes-get
# polyglot-covers: python.urllib.request.redirect-post-content-headers-removed
# polyglot-covers: python.urllib.request.redirect-regular-headers-copied
# polyglot-covers: python.urllib.request.redirect-unredirected-headers-not-copied
# polyglot-covers: python.urllib.request.redirect-307-post-http-error
# polyglot-covers: python.urllib.request.redirect-relative-urljoin
# polyglot-covers: python.urllib.request.redirect-space-percent-encoding
# polyglot-covers: python.urllib.request.redirect-response-consumed-and-closed
# polyglot-covers: python.urllib.request.redirect-scheme-security
# polyglot-covers: python.urllib.request.HTTPCookieProcessor
# polyglot-covers: python.urllib.request.HTTPCookieProcessor.cookiejar
# polyglot-covers: python.urllib.request.HTTPCookieProcessor.http_request
# polyglot-covers: python.urllib.request.HTTPCookieProcessor.http_response
# polyglot-covers: python.urllib.request.cookie-response-extraction
# polyglot-covers: python.urllib.request.cookie-subsequent-request-replay
# polyglot-covers: python.urllib.request.cookie-handler-chain-memory-workflow


class MemoryHTTPTransport(BaseHandler):
    handler_order = 100

    def __init__(self):
        self.requests = []

    def http_open(self, request):
        self.requests.append(dict(request.header_items()))
        headers = Message()
        if len(self.requests) == 1:
            headers["Set-Cookie"] = "session=abc123; Path=/"
        response = addinfourl(
            BytesIO(b"ok"),
            headers,
            request.full_url,
            code=200,
        )
        response.msg = "OK"
        return response


def test_post_302_becomes_get_and_drops_entity_and_sensitive_headers():
    request = Request(
        "https://example.test/submit",
        data=b"name=python",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": "11",
            "X-Trace": "keep",
        },
    )
    request.add_unredirected_header("Authorization", "Bearer secret")

    redirected = HTTPRedirectHandler().redirect_request(
        request,
        BytesIO(),
        302,
        "Found",
        Message(),
        "https://example.test/result",
    )

    assert redirected.get_method() == "GET"
    assert redirected.data is None
    assert redirected.get_header("X-trace") == "keep"
    assert redirected.get_header("Content-type") is None
    assert redirected.get_header("Content-length") is None
    assert redirected.get_header("Authorization") is None
    assert redirected.unverifiable is True


def test_post_307_is_not_automatically_replayed():
    """默认 handler 不会擅自重放可能是一次性的请求体。"""
    request = Request("https://example.test/upload", data=b"one-shot")

    with pytest.raises(HTTPError):
        HTTPRedirectHandler().redirect_request(
            request,
            BytesIO(),
            307,
            "Temporary Redirect",
            Message(),
            "https://example.test/new-target",
        )


def test_http_error_302_resolves_relative_location_and_closes_old_response():
    opened = []
    sentinel = object()

    class Parent:
        def open(self, request, timeout):
            opened.append((request, timeout))
            return sentinel

    handler = HTTPRedirectHandler()
    handler.add_parent(Parent())
    request = Request("https://example.test/a/start")
    request.timeout = 4
    response_body = BytesIO(b"discarded")
    headers = Message()
    headers["Location"] = "../next page"

    result = handler.http_error_302(
        request,
        response_body,
        302,
        "Found",
        headers,
    )

    assert result is sentinel
    assert opened[0][0].full_url == "https://example.test/next%20page"
    assert opened[0][1] == 4
    assert response_body.closed


def test_redirect_to_a_non_network_scheme_is_rejected():
    request = Request("https://example.test/start")
    headers = Message()
    headers["Location"] = "file:///etc/passwd"

    with pytest.raises(HTTPError):
        HTTPRedirectHandler().http_error_302(
            request,
            BytesIO(),
            302,
            "Found",
            headers,
        )


def test_cookie_processor_extracts_then_replays_cookie_on_the_next_request():
    """响应后处理写入 CookieJar，请求预处理再按域和路径选择 Cookie。"""
    jar = CookieJar()
    processor = HTTPCookieProcessor(jar)
    transport = MemoryHTTPTransport()
    opener = build_opener(ProxyHandler({}), transport, processor)

    with opener.open("http://example.test/login") as response:
        assert response.read() == b"ok"
    with opener.open("http://example.test/account") as response:
        assert response.read() == b"ok"

    assert processor.cookiejar is jar
    assert [(cookie.name, cookie.value) for cookie in jar] == [
        ("session", "abc123"),
    ]
    assert "Cookie" not in transport.requests[0]
    assert transport.requests[1]["Cookie"] == "session=abc123"


# 学习 urllib.request 的凭据作用域、Basic/Digest challenge 和预认证状态。


# polyglot-covers: python.urllib.request.HTTPPasswordMgr
# polyglot-covers: python.urllib.request.HTTPPasswordMgr.add_password
# polyglot-covers: python.urllib.request.HTTPPasswordMgr.uri-sequence
# polyglot-covers: python.urllib.request.HTTPPasswordMgr.find_user_password
# polyglot-covers: python.urllib.request.HTTPPasswordMgr.super-uri-scope
# polyglot-covers: python.urllib.request.HTTPPasswordMgr.sibling-path-isolation
# polyglot-covers: python.urllib.request.HTTPPasswordMgr.default-port-normalization
# polyglot-covers: python.urllib.request.HTTPPasswordMgr.missing-pair
# polyglot-covers: python.urllib.request.HTTPPasswordMgrWithDefaultRealm
# polyglot-covers: python.urllib.request.HTTPPasswordMgrWithDefaultRealm.none-fallback
# polyglot-covers: python.urllib.request.HTTPBasicAuthHandler
# polyglot-covers: python.urllib.request.HTTPBasicAuthHandler.http_error_401
# polyglot-covers: python.urllib.request.basic-auth-realm-challenge
# polyglot-covers: python.urllib.request.basic-auth-base64-credentials
# polyglot-covers: python.urllib.request.basic-auth-authorization-unredirected
# polyglot-covers: python.urllib.request.basic-auth-retry-through-parent
# polyglot-covers: python.urllib.request.basic-auth-unsupported-scheme-value-error
# polyglot-covers: python.urllib.request.HTTPPasswordMgrWithPriorAuth
# polyglot-covers: python.urllib.request.HTTPPasswordMgrWithPriorAuth.add_password
# polyglot-covers: python.urllib.request.HTTPPasswordMgrWithPriorAuth.is_authenticated
# polyglot-covers: python.urllib.request.HTTPPasswordMgrWithPriorAuth.update_authenticated
# polyglot-covers: python.urllib.request.basic-auth-prior-request
# polyglot-covers: python.urllib.request.basic-auth-response-updates-prior-state
# polyglot-covers: python.urllib.request.HTTPDigestAuthHandler
# polyglot-covers: python.urllib.request.HTTPDigestAuthHandler.http_error_401
# polyglot-covers: python.urllib.request.digest-auth-challenge-fields
# polyglot-covers: python.urllib.request.digest-auth-authorization-header
# polyglot-covers: python.urllib.request.digest-auth-parent-retry
# polyglot-covers: python.urllib.request.digest-auth-handler-before-basic
# polyglot-covers: python.urllib.request.digest-auth-md5-sha-legacy-limit
# polyglot-covers: python.urllib.request.digest-auth-qop-auth-int-unsupported
# polyglot-covers: python.urllib.request.ProxyDigestAuthHandler
# polyglot-covers: python.urllib.request.ProxyDigestAuthHandler.http_error_407


def challenge_headers(value):
    headers = Message()
    headers["WWW-Authenticate"] = value
    return headers


def test_credentials_apply_to_registered_uri_and_descendants_only():
    manager = HTTPPasswordMgr()
    manager.add_password(
        "private",
        [
            "https://example.test/private/",
            "https://mirror.test/secure/",
        ],
        "alice",
        "secret",
    )

    assert manager.find_user_password(
        "private",
        "https://example.test/private/item/1",
    ) == ("alice", "secret")
    assert manager.find_user_password(
        "private",
        "https://mirror.test/secure/file",
    ) == ("alice", "secret")
    assert manager.find_user_password(
        "private",
        "https://example.test/public/",
    ) == (None, None)


def test_default_ports_are_equivalent_during_credential_lookup():
    manager = HTTPPasswordMgr()
    manager.add_password(
        "realm",
        "https://example.test:443/private",
        "alice",
        "secret",
    )

    assert manager.find_user_password(
        "realm",
        "https://example.test/private/child",
    ) == ("alice", "secret")


def test_default_realm_is_used_only_after_the_requested_realm_misses():
    manager = HTTPPasswordMgrWithDefaultRealm()
    manager.add_password(
        None,
        "https://example.test/",
        "fallback-user",
        "fallback-password",
    )
    manager.add_password(
        "admin",
        "https://example.test/admin/",
        "admin-user",
        "admin-password",
    )

    assert manager.find_user_password(
        "admin",
        "https://example.test/admin/panel",
    ) == ("admin-user", "admin-password")
    assert manager.find_user_password(
        "unknown",
        "https://example.test/other",
    ) == ("fallback-user", "fallback-password")


def test_basic_challenge_retries_with_unredirected_authorization():
    manager = HTTPPasswordMgr()
    manager.add_password(
        "private",
        "https://example.test/private/",
        "alice",
        "secret",
    )
    opened = []
    sentinel = object()

    class Parent:
        def open(self, request, timeout):
            opened.append((request, timeout))
            return sentinel

    handler = HTTPBasicAuthHandler(manager)
    handler.add_parent(Parent())
    request = Request("https://example.test/private/item")
    request.timeout = 3

    result = handler.http_error_401(
        request,
        None,
        401,
        "Unauthorized",
        challenge_headers('Basic realm="private"'),
    )

    token = base64.b64encode(b"alice:secret").decode("ascii")
    assert result is sentinel
    assert opened == [(request, 3)]
    assert request.get_header("Authorization") == f"Basic {token}"
    assert request.headers.get("Authorization") is None
    assert request.unredirected_hdrs["Authorization"] == f"Basic {token}"


def test_basic_handler_does_not_treat_an_unknown_scheme_as_basic():
    handler = HTTPBasicAuthHandler(HTTPPasswordMgr())
    request = Request("https://example.test/private")

    with pytest.raises(ValueError):
        handler.http_error_401(
            request,
            None,
            401,
            "Unauthorized",
            challenge_headers('Bearer realm="private"'),
        )


def test_prior_auth_sends_credentials_only_while_uri_is_authenticated():
    manager = HTTPPasswordMgrWithPriorAuth()
    target = "https://example.test/private/item"
    manager.add_password(
        "private",
        target,
        "alice",
        "secret",
        is_authenticated=True,
    )
    handler = HTTPBasicAuthHandler(manager)
    request = Request(target)

    handler.http_request(request)

    token = base64.b64encode(b"alice:secret").decode("ascii")
    assert manager.is_authenticated(request.full_url) is True
    assert request.get_header("Authorization") == f"Basic {token}"

    handler.http_response(request, SimpleNamespace(code=401))
    later = Request(target)
    handler.http_request(later)
    assert manager.is_authenticated(later.full_url) is False
    assert later.get_header("Authorization") is None


def test_successful_response_enables_future_prior_auth_for_descendants():
    manager = HTTPPasswordMgrWithPriorAuth()
    base = "https://example.test/private/"
    manager.add_password("private", base, "alice", "secret")
    handler = HTTPBasicAuthHandler(manager)
    completed = Request(base)

    handler.http_response(completed, SimpleNamespace(code=204))

    future = Request(f"{base}resource")
    handler.http_request(future)
    assert manager.is_authenticated(future.full_url) is True
    assert future.has_header("Authorization")


def test_digest_challenge_builds_header_and_retries_through_parent():
    manager = HTTPPasswordMgr()
    manager.add_password(
        "private",
        "https://example.test/private/",
        "alice",
        "secret",
    )
    opened = []
    sentinel = object()

    class Parent:
        def open(self, request, timeout):
            opened.append((request, timeout))
            return sentinel

    handler = HTTPDigestAuthHandler(manager)
    handler.add_parent(Parent())
    request = Request("https://example.test/private/item")
    request.timeout = 5
    headers = challenge_headers(
        'Digest realm="private", nonce="abc123", qop="auth", '
        'algorithm="MD5", opaque="server-state"'
    )

    result = handler.http_error_401(
        request,
        None,
        401,
        "Unauthorized",
        headers,
    )

    authorization = request.get_header("Authorization")
    assert result is sentinel
    assert opened == [(request, 5)]
    assert authorization.startswith("Digest ")
    for field in (
        'username="alice"',
        'realm="private"',
        'nonce="abc123"',
        'uri="/private/item"',
        "qop=auth",
        "nc=00000001",
        'opaque="server-state"',
    ):
        assert field in authorization


def test_digest_handler_is_ordered_before_basic():
    digest = HTTPDigestAuthHandler()
    basic = HTTPBasicAuthHandler()
    opener = build_opener(ProxyHandler({}), basic, digest)

    assert digest.handler_order < basic.handler_order
    assert opener.handlers.index(digest) < opener.handlers.index(basic)
    assert ProxyDigestAuthHandler().auth_header == "Proxy-Authorization"


def test_legacy_digest_rejects_unsupported_algorithm_and_qop():
    """3.10 的旧实现不等同于支持现代完整 Digest 算法集合。"""
    manager = HTTPPasswordMgr()
    manager.add_password(
        "realm",
        "https://example.test/",
        "alice",
        "secret",
    )
    handler = HTTPDigestAuthHandler(manager)
    request = Request("https://example.test/resource")

    with pytest.raises(ValueError):
        handler.get_algorithm_impls("SHA-256")
    with pytest.raises(URLError):
        handler.get_authorization(
            request,
            {
                "realm": "realm",
                "nonce": "abc123",
                "qop": "auth-int",
                "algorithm": "MD5",
            },
        )


# 学习 urllib 的异常层级、HTTP 状态分派和兼具元数据的可读响应。


# polyglot-covers: python.urllib.error.URLError
# polyglot-covers: python.urllib.error.URLError-is-OSError-3.3
# polyglot-covers: python.urllib.error.URLError.reason-string
# polyglot-covers: python.urllib.error.URLError.reason-exception
# polyglot-covers: python.urllib.error.HTTPError
# polyglot-covers: python.urllib.error.HTTPError-is-URLError
# polyglot-covers: python.urllib.error.HTTPError-file-like
# polyglot-covers: python.urllib.error.HTTPError.code
# polyglot-covers: python.urllib.error.HTTPError.reason
# polyglot-covers: python.urllib.error.HTTPError.headers-3.4
# polyglot-covers: python.urllib.error.ContentTooShortError
# polyglot-covers: python.urllib.error.ContentTooShortError.content
# polyglot-covers: python.urllib.request.HTTPErrorProcessor
# polyglot-covers: python.urllib.request.HTTPErrorProcessor.http_response
# polyglot-covers: python.urllib.request.HTTPErrorProcessor.https_response
# polyglot-covers: python.urllib.request.http-error-2xx-pass-through
# polyglot-covers: python.urllib.request.http-error-non2xx-parent-dispatch
# polyglot-covers: python.urllib.request.OpenerDirector.error
# polyglot-covers: python.urllib.request.http-error-specific-before-default
# polyglot-covers: python.urllib.request.HTTPDefaultErrorHandler
# polyglot-covers: python.urllib.request.HTTPDefaultErrorHandler.http_error_default
# polyglot-covers: python.urllib.request.UnknownHandler
# polyglot-covers: python.urllib.request.UnknownHandler.unknown_open
# polyglot-covers: python.urllib.response.addinfourl
# polyglot-covers: python.urllib.response.addinfourl-file-like
# polyglot-covers: python.urllib.response.addinfourl.url
# polyglot-covers: python.urllib.response.addinfourl.headers
# polyglot-covers: python.urllib.response.addinfourl.status-3.9
# polyglot-covers: python.urllib.response.addinfourl.geturl-deprecated-3.9
# polyglot-covers: python.urllib.response.addinfourl.info-deprecated-3.9
# polyglot-covers: python.urllib.response.addinfourl.code-deprecated-3.9
# polyglot-covers: python.urllib.response.addinfourl.getcode-deprecated-3.9
# polyglot-covers: python.urllib.response.response-context-manager-closes-stream


class StatusResponse(BytesIO):
    def __init__(self, code, message, body=b""):
        super().__init__(body)
        self.code = code
        self.msg = message
        self.headers = Message()

    def info(self):
        return self.headers


def test_urlerror_preserves_string_or_nested_exception_reason():
    message_error = URLError("name lookup failed")
    cause = TimeoutError("timed out")
    nested_error = URLError(cause)

    assert isinstance(message_error, OSError)
    assert message_error.reason == "name lookup failed"
    assert nested_error.reason is cause


def test_httperror_is_both_an_exception_and_readable_response():
    headers = Message()
    headers["Content-Type"] = "application/problem+json"
    error = HTTPError(
        "https://example.test/items/404",
        404,
        "Not Found",
        headers,
        BytesIO(b'{"error":"missing"}'),
    )

    assert isinstance(error, URLError)
    assert error.code == 404
    assert error.reason == "Not Found"
    assert error.headers is headers
    assert error.read() == b'{"error":"missing"}'
    error.close()


def test_content_too_short_error_keeps_partial_content_reference():
    partial = ("/tmp/partial-download", Message())
    error = ContentTooShortError("download incomplete", partial)

    assert isinstance(error, URLError)
    assert error.content is partial


def test_error_processor_passes_2xx_and_dispatches_other_statuses():
    calls = []
    sentinel = object()

    class Parent:
        def error(self, *args):
            calls.append(args)
            return sentinel

    processor = HTTPErrorProcessor()
    processor.add_parent(Parent())
    request = Request("https://example.test/resource")
    success = StatusResponse(204, "No Content")
    missing = StatusResponse(404, "Not Found", b"missing")

    assert processor.https_response(request, success) is success
    assert processor.http_response(request, missing) is sentinel
    assert calls[0][:4] == ("http", request, missing, 404)


def test_opener_error_prefers_a_status_specific_handler():
    class TeapotHandler(BaseHandler):
        def http_error_418(self, request, response, code, message, headers):
            return (code, message, response.read())

    opener = OpenerDirector()
    opener.add_handler(TeapotHandler())
    request = Request("http://example.test/tea")

    result = opener.error(
        "http",
        request,
        BytesIO(b"short and stout"),
        418,
        "I'm a teapot",
        Message(),
    )

    assert result == (418, "I'm a teapot", b"short and stout")


def test_default_error_handler_raises_a_file_like_http_error():
    request = Request("http://example.test/missing")
    body = BytesIO(b"diagnostic")

    with pytest.raises(HTTPError) as captured:
        HTTPDefaultErrorHandler().http_error_default(
            request,
            body,
            404,
            "Not Found",
            Message(),
        )

    assert captured.value.read() == b"diagnostic"


def test_unknown_handler_turns_an_unrecognized_scheme_into_urlerror():
    request = Request("custom://example.test/resource")

    with pytest.raises(URLError):
        UnknownHandler().unknown_open(request)


def test_addinfourl_combines_stream_and_response_metadata():
    raw = BytesIO(b"payload")
    headers = Message()
    headers["Content-Type"] = "application/octet-stream"
    response = addinfourl(
        raw,
        headers,
        "https://example.test/final",
        code=201,
    )

    with response as opened:
        assert opened.read(4) == b"payl"
        assert opened.readline() == b"oad"
        assert opened.url == "https://example.test/final"
        assert opened.headers is headers
        assert opened.status == 201

        # 兼容方法仍返回同一信息，新代码宜直接读现代属性。
        assert opened.geturl() == opened.url
        assert opened.info() is opened.headers
        assert opened.code == opened.status
        assert opened.getcode() == opened.status

    assert raw.closed
