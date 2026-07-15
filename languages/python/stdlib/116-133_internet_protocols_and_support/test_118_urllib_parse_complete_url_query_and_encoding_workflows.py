"""118｜学习 urllib.parse 的 URL 结构、重组、查询、百分号编码和表单工作流。

解析结果保留 URL 的结构而不负责业务安全验证。这个测试套把拆分、派生 authority 属性、
结构化结果、重组与 urljoin 放在同一阅读流程中；所有案例都是纯字符串操作。
"""

from urllib.parse import urldefrag
from urllib.parse import parse_qs
from urllib.parse import parse_qsl
from urllib.parse import quote
from urllib.parse import quote_from_bytes
from urllib.parse import quote_plus
from urllib.parse import unquote
from urllib.parse import unquote_plus
from urllib.parse import unquote_to_bytes
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.parse import urlsplit
from urllib.parse import urlencode
from urllib.parse import urlunparse
from urllib.parse import urlunsplit
from urllib.parse import unwrap

import pytest


# polyglot-covers: python.urllib.parse.urlparse
# polyglot-covers: python.urllib.parse.urlparse.six-components
# polyglot-covers: python.urllib.parse.urlparse.params-final-path-segment
# polyglot-covers: python.urllib.parse.urlsplit
# polyglot-covers: python.urllib.parse.urlsplit.params-remain-in-path
# polyglot-covers: python.urllib.parse.netloc-requires-double-slash
# polyglot-covers: python.urllib.parse.percent-escapes-not-expanded-by-parsing
# polyglot-covers: python.urllib.parse.allow_fragments
# polyglot-covers: python.urllib.parse.ParseResult.username
# polyglot-covers: python.urllib.parse.ParseResult.password
# polyglot-covers: python.urllib.parse.ParseResult.hostname
# polyglot-covers: python.urllib.parse.ParseResult.port
# polyglot-covers: python.urllib.parse.userinfo-percent-escapes-not-expanded
# polyglot-covers: python.urllib.parse.ipv6-bracketed-host
# polyglot-covers: python.urllib.parse.port-invalid-delayed-value-error
# polyglot-covers: python.urllib.parse.port-out-of-range-value-error
# polyglot-covers: python.urllib.parse.unmatched-brackets-value-error
# polyglot-covers: python.urllib.parse.netloc-nfkc-delimiter-value-error-3.8
# polyglot-covers: python.urllib.parse.structured-result-tuple
# polyglot-covers: python.urllib.parse.structured-result._replace
# polyglot-covers: python.urllib.parse.structured-result.geturl
# polyglot-covers: python.urllib.parse.geturl-normalizes-scheme
# polyglot-covers: python.urllib.parse.geturl-drops-empty-delimiters
# polyglot-covers: python.urllib.parse.structured-result.encode
# polyglot-covers: python.urllib.parse.structured-result.decode
# polyglot-covers: python.urllib.parse.ascii-bytes-input
# polyglot-covers: python.urllib.parse.mixed-str-bytes-type-error
# polyglot-covers: python.urllib.parse.non-ascii-bytes-unicode-decode-error
# polyglot-covers: python.urllib.parse.urlsplit-ascii-newline-tab-cleanup-3.10
# polyglot-covers: python.urllib.parse.urlsplit-leading-c0-space-cleanup-3.10-backport
# polyglot-covers: python.urllib.parse.url-parsing-is-not-validation
# polyglot-covers: python.urllib.parse.missing-authority-can-parse
# polyglot-covers: python.urllib.parse.caller-validates-scheme
# polyglot-covers: python.urllib.parse.caller-validates-hostname
# polyglot-covers: python.urllib.parse.escaped-path-remains-encoded
# polyglot-covers: python.urllib.parse.urlunparse
# polyglot-covers: python.urllib.parse.urlunsplit
# polyglot-covers: python.urllib.parse.recomposition-equivalent-not-identical
# polyglot-covers: python.urllib.parse.urldefrag
# polyglot-covers: python.urllib.parse.DefragResult
# polyglot-covers: python.urllib.parse.unwrap
# polyglot-covers: python.urllib.parse.unwrap-angle-and-url-prefix
# polyglot-covers: python.urllib.parse.urljoin
# polyglot-covers: python.urllib.parse.urljoin.parent-segment-resolution
# polyglot-covers: python.urllib.parse.urljoin.root-relative
# polyglot-covers: python.urllib.parse.urljoin.query-relative
# polyglot-covers: python.urllib.parse.urljoin.network-path-reference
# polyglot-covers: python.urllib.parse.urljoin.absolute-url-replaces-base
# polyglot-covers: python.urllib.parse.urljoin-untrusted-input-host-injection
# polyglot-covers: python.urllib.parse.urljoin-strip-scheme-netloc-workflow


BASE = "https://example.test/a/b/index.html"


def require_https_target(value):
    """在宽松结构解析之后施加当前应用真正需要的不变量。"""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("需要带主机名的 HTTPS URL")
    return parsed


def join_as_path_on_trusted_origin(base, untrusted_reference):
    """丢弃用户引用中的 scheme/netloc，阻止 urljoin 替换可信源站。"""
    parts = urlsplit(untrusted_reference)
    path_only = urlunsplit(("", "", parts.path, parts.query, parts.fragment))
    return urljoin(base, path_only)


def test_urlparse_and_urlsplit_treat_legacy_path_parameters_differently():
    parsed = urlparse("https://example.test/a;b/c;d?q=python#examples")

    assert parsed == (
        "https",
        "example.test",
        "/a;b/c",
        "d",
        "q=python",
        "examples",
    )
    # urlsplit 不保留历史 params 槽，分号仍是 path 的一部分。
    split = urlsplit("https://example.test/a;b/c;d?q=python#examples")
    assert split.path == "/a;b/c;d"
    assert split.query == "q=python"


def test_authority_needs_double_slashes_and_percent_escapes_stay_encoded():
    without_slashes = urlparse("example.test/a%20b")
    with_slashes = urlparse("//example.test/a%20b")

    assert without_slashes.netloc == ""
    assert without_slashes.path == "example.test/a%20b"
    assert with_slashes.netloc == "example.test"
    assert with_slashes.path == "/a%20b"


def test_disabling_fragments_leaves_hash_in_the_previous_component():
    parsed = urlparse(
        "https://example.test/search?q=python#advanced",
        allow_fragments=False,
    )

    assert parsed.fragment == ""
    assert parsed.query == "q=python#advanced"


def test_authority_properties_separate_userinfo_host_and_port():
    """netloc 保存原文，hostname 才规范化大小写，userinfo 不会百分号解码。"""
    parsed = urlsplit("https://alice:p%40ss@EXAMPLE.TEST:8443/resource")

    assert parsed.netloc == "alice:p%40ss@EXAMPLE.TEST:8443"
    assert parsed.username == "alice"
    assert parsed.password == "p%40ss"
    assert parsed.hostname == "example.test"
    assert parsed.port == 8443


def test_brackets_distinguish_an_ipv6_literal_from_its_port():
    parsed = urlsplit("https://[2001:db8::1]:443/index.html")

    assert parsed.hostname == "2001:db8::1"
    assert parsed.port == 443


def test_bad_ports_are_reported_only_when_port_is_read():
    """拆分成功不代表 authority 已全部验证，端口整数转换采用延迟求值。"""
    nonnumeric = urlsplit("http://example.test:not-a-port/")
    out_of_range = urlsplit("http://example.test:70000/")

    assert nonnumeric.netloc == "example.test:not-a-port"
    with pytest.raises(ValueError):
        _ = nonnumeric.port
    with pytest.raises(ValueError):
        _ = out_of_range.port


def test_structurally_dangerous_netloc_characters_fail_during_splitting():
    with pytest.raises(ValueError):
        urlsplit("https://[2001:db8::1/path")
    # 全角冒号经 NFKC 会变成 authority 分隔符，解析器拒绝这种歧义。
    with pytest.raises(ValueError):
        urlsplit("https://example.test：443/path")


def test_structured_result_supports_tuple_replace_and_normalized_geturl():
    parsed = urlsplit("HTTP://Example.TEST/path?#")

    assert parsed[0] == parsed.scheme == "http"
    assert parsed.netloc == "Example.TEST"
    assert parsed.geturl() == "http://Example.TEST/path"

    changed = parsed._replace(path="/other", query="page=2")
    assert changed.geturl() == "http://Example.TEST/other?page=2"
    assert parsed.path == "/path"


def test_result_encode_and_decode_preserve_ascii_components():
    text_result = urlsplit("https://example.test/a%20b")
    bytes_result = text_result.encode()

    assert bytes_result.geturl() == b"https://example.test/a%20b"
    assert bytes_result.decode() == text_result

    parsed_bytes = urlsplit(b"https://example.test/raw%2Fpath")
    assert parsed_bytes.path == b"/raw%2Fpath"
    assert parsed_bytes.decode().path == "/raw%2Fpath"


def test_text_and_bytes_cannot_mix_or_silently_decode_nonascii():
    with pytest.raises(TypeError):
        urlsplit(b"//example.test/path", scheme="https")
    with pytest.raises(UnicodeDecodeError):
        urlsplit(b"https://example.test/\xff")


def test_documented_control_characters_are_removed_before_component_use():
    parsed = urlsplit("\x00 \thttps://exa\nmple.test/pa\rth")

    assert parsed.scheme == "https"
    assert parsed.hostname == "example.test"
    assert parsed.path == "/path"


def test_successful_splitting_does_not_prove_a_url_is_acceptable():
    missing_host = urlsplit("https:///private/resource")
    custom_scheme = urlsplit("internal:job/42")

    assert missing_host.netloc == ""
    assert missing_host.path == "/private/resource"
    assert custom_scheme.scheme == "internal"
    with pytest.raises(ValueError):
        require_https_target(missing_host.geturl())
    with pytest.raises(ValueError):
        require_https_target(custom_scheme.geturl())


def test_caller_validation_can_keep_an_encoded_path():
    parsed = require_https_target("https://example.test/a%2Fb")

    assert parsed.hostname == "example.test"
    assert parsed.path == "/a%2Fb"


def test_six_and_five_component_sequences_recompose_urls():
    six_parts = (
        "https",
        "example.test",
        "/docs/index.html",
        "v=2",
        "lang=zh",
        "api",
    )
    five_parts = (
        "https",
        "example.test",
        "/search",
        "q=python",
        "results",
    )

    assert urlunparse(six_parts) == (
        "https://example.test/docs/index.html;v=2?lang=zh#api"
    )
    assert urlunsplit(five_parts) == "https://example.test/search?q=python#results"
    assert urlunsplit(("https", "example.test", "/path", "", "")) == (
        "https://example.test/path"
    )


def test_defrag_and_unwrap_return_reusable_url_text():
    result = urldefrag("https://example.test/page?q=1#section-2")

    assert result.url == "https://example.test/page?q=1"
    assert result.fragment == "section-2"
    assert tuple(result) == (result.url, result.fragment)

    url = "https://example.test/path"
    assert unwrap(f"<URL:{url}>") == url
    assert unwrap(f"<{url}>") == url
    assert unwrap(f"URL:{url}") == url
    assert unwrap(url) == url


def test_urljoin_resolves_relative_root_and_query_references():
    assert urljoin(BASE, "../img/logo.png") == (
        "https://example.test/a/img/logo.png"
    )
    assert urljoin(BASE, "/assets/app.js") == "https://example.test/assets/app.js"
    assert urljoin(BASE, "?page=2") == (
        "https://example.test/a/b/index.html?page=2"
    )


def test_absolute_or_network_path_reference_can_replace_the_origin():
    assert urljoin(BASE, "//evil.test/collect") == "https://evil.test/collect"
    assert urljoin(BASE, "http://evil.test/plain") == "http://evil.test/plain"


def test_stripping_scheme_and_netloc_keeps_user_path_on_the_trusted_origin():
    joined = join_as_path_on_trusted_origin(
        BASE,
        "//evil.test/collect?token=visible#result",
    )

    assert joined == "https://example.test/collect?token=visible#result"

# 查询解析、百分号编解码与表单提交。


# polyglot-covers: python.urllib.parse.parse_qs
# polyglot-covers: python.urllib.parse.parse_qs-values-are-lists
# polyglot-covers: python.urllib.parse.parse_qsl
# polyglot-covers: python.urllib.parse.parse_qsl-preserves-order-and-duplicates
# polyglot-covers: python.urllib.parse.keep_blank_values
# polyglot-covers: python.urllib.parse.strict_parsing
# polyglot-covers: python.urllib.parse.query-encoding-errors
# polyglot-covers: python.urllib.parse.query-invalid-octet-replace-default
# polyglot-covers: python.urllib.parse.parse_qs.max_num_fields-3.8
# polyglot-covers: python.urllib.parse.parse_qsl.max_num_fields-3.8
# polyglot-covers: python.urllib.parse.query-field-resource-limit
# polyglot-covers: python.urllib.parse.query-separator-3.10
# polyglot-covers: python.urllib.parse.query-semicolon-not-default-3.10
# polyglot-covers: python.urllib.parse.query-custom-separator-exclusive
# polyglot-covers: python.urllib.parse.query-bytes-input-and-output
# polyglot-covers: python.urllib.parse.quote
# polyglot-covers: python.urllib.parse.quote.default-safe-slash
# polyglot-covers: python.urllib.parse.quote.safe
# polyglot-covers: python.urllib.parse.quote.unreserved-tilde-3.7
# polyglot-covers: python.urllib.parse.quote.encoding
# polyglot-covers: python.urllib.parse.quote_plus
# polyglot-covers: python.urllib.parse.quote_plus-space-plus-and-slash
# polyglot-covers: python.urllib.parse.quote_from_bytes
# polyglot-covers: python.urllib.parse.quote-bytes-reject-encoding
# polyglot-covers: python.urllib.parse.unquote
# polyglot-covers: python.urllib.parse.unquote-bytes-input-3.9
# polyglot-covers: python.urllib.parse.unquote.errors-replace
# polyglot-covers: python.urllib.parse.unquote.errors-strict
# polyglot-covers: python.urllib.parse.unquote-malformed-escape-preserved
# polyglot-covers: python.urllib.parse.unquote_plus
# polyglot-covers: python.urllib.parse.unquote_plus-str-only
# polyglot-covers: python.urllib.parse.unquote_to_bytes
# polyglot-covers: python.urllib.parse.unquote_to_bytes-unescaped-nonascii-utf8
# polyglot-covers: python.urllib.parse.urlencode
# polyglot-covers: python.urllib.parse.urlencode-sequence-order
# polyglot-covers: python.urllib.parse.urlencode-doseq
# polyglot-covers: python.urllib.parse.urlencode-doseq-empty-sequence-omitted
# polyglot-covers: python.urllib.parse.urlencode-without-doseq-stringifies-sequence
# polyglot-covers: python.urllib.parse.urlencode.quote_via
# polyglot-covers: python.urllib.parse.urlencode.safe
# polyglot-covers: python.urllib.parse.urlencode-bytes-values
# polyglot-covers: python.urllib.parse.urlencode-result-is-str
# polyglot-covers: python.urllib.parse.urlencode-post-body-encode-workflow


QUERY = "tag=python&tag=pytest&empty=&flag&word=%E4%B8%AD"


def test_parse_qs_groups_values_while_parse_qsl_preserves_order():
    assert parse_qs(QUERY) == {
        "tag": ["python", "pytest"],
        "word": ["中"],
    }
    assert parse_qsl(QUERY, keep_blank_values=True) == [
        ("tag", "python"),
        ("tag", "pytest"),
        ("empty", ""),
        ("flag", ""),
        ("word", "中"),
    ]


def test_blank_malformed_and_invalid_octets_need_explicit_policies():
    kept = parse_qs(QUERY, keep_blank_values=True)
    assert kept["empty"] == [""]
    assert kept["flag"] == [""]

    with pytest.raises(ValueError):
        parse_qs("ok=1&broken&next=2", strict_parsing=True)
    assert parse_qs("value=%FF") == {"value": ["�"]}
    with pytest.raises(UnicodeDecodeError):
        parse_qs("value=%FF", errors="strict")


def test_field_budget_rejects_queries_above_the_chosen_limit():
    query = "a=1&b=2&c=3"

    with pytest.raises(ValueError):
        parse_qs(query, max_num_fields=2)
    with pytest.raises(ValueError):
        parse_qsl(query, max_num_fields=2)
    assert len(parse_qsl(query, max_num_fields=3)) == 3


def test_python_310_uses_only_the_selected_query_separator():
    mixed = "a=1;b=2&c=3"

    assert parse_qs(mixed) == {"a": ["1;b=2"], "c": ["3"]}
    assert parse_qs(mixed, separator=";") == {
        "a": ["1"],
        "b": ["2&c=3"],
    }


def test_ascii_bytes_query_produces_bytes_keys_and_values():
    parsed = parse_qs(b"tag=one&tag=two&empty=", keep_blank_values=True)
    assert parsed == {b"tag": [b"one", b"two"], b"empty": [b""]}


def test_quote_uses_utf8_and_preserves_slash_unless_safe_is_replaced():
    value = "a b/c?d=é~"

    assert quote(value) == "a%20b/c%3Fd%3D%C3%A9~"
    assert quote(value, safe="") == "a%20b%2Fc%3Fd%3D%C3%A9~"


def test_quote_plus_distinguishes_spaces_from_literal_plus_signs():
    value = "a b/c+d"

    assert quote_plus(value) == "a+b%2Fc%2Bd"
    assert quote_plus(value, safe="/") == "a+b/c%2Bd"


def test_quote_from_bytes_encodes_octets_without_text_decoding():
    assert quote_from_bytes(b"/\xff", safe="/") == "/%FF"
    assert quote(b"/\xff") == "/%FF"
    with pytest.raises(TypeError):
        quote(b"raw", encoding="utf-8")


def test_unquote_decodes_percent_octets_but_not_form_plus_signs():
    assert unquote("a%20b%2Fc+d") == "a b/c+d"
    assert unquote(b"a%20b") == "a b"
    assert unquote("literal%ZZescape") == "literal%ZZescape"


def test_unquote_error_policy_controls_invalid_utf8_octets():
    assert unquote("%FF") == "�"
    with pytest.raises(UnicodeDecodeError):
        unquote("%FF", errors="strict")


def test_unquote_plus_is_text_form_specific_and_to_bytes_preserves_octets():
    assert unquote_plus("a+b%2Bc") == "a b+c"
    with pytest.raises(TypeError):
        unquote_plus(b"a+b")

    assert unquote_to_bytes("%E4%B8%AD") == "中".encode("utf-8")
    assert unquote_to_bytes("é%20") == b"\xc3\xa9 "


def test_urlencode_doseq_expands_values_in_input_order():
    fields = [
        ("q", "a b/c"),
        ("tag", ["python", "pytest"]),
        ("empty-list", []),
    ]

    assert urlencode(fields, doseq=True) == "q=a+b%2Fc&tag=python&tag=pytest"


def test_urlencode_without_doseq_stringifies_a_list_as_one_value():
    encoded = urlencode([("tag", ["python", "pytest"])])

    assert encoded.startswith("tag=%5B")
    assert encoded.count("tag=") == 1


def test_urlencode_quote_via_changes_space_and_safe_character_policy():
    encoded = urlencode(
        [("q", "a b/c")],
        quote_via=quote,
        safe="/",
    )
    assert encoded == "q=a%20b/c"


def test_urlencode_bytes_values_then_encode_the_post_body():
    """urlencode 返回 str，HTTP 请求体需要调用方再明确编码为 bytes。"""
    encoded = urlencode([(b"raw", b"\xff"), ("name", "中文")])
    body = encoded.encode("ascii")

    assert encoded == "raw=%FF&name=%E4%B8%AD%E6%96%87"
    assert isinstance(encoded, str)
    assert body == b"raw=%FF&name=%E4%B8%AD%E6%96%87"
