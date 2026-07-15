"""学习 urllib.robotparser 的规则选择、抓取节奏、读取和 HTTP 状态策略。"""

from email.message import Message
from io import BytesIO
import urllib.request as urllib_request
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.robotparser import RobotFileParser

import pytest


# polyglot-covers: python.urllib.robotparser.RobotFileParser
# polyglot-covers: python.urllib.robotparser.RobotFileParser.parse
# polyglot-covers: python.urllib.robotparser.RobotFileParser.can_fetch
# polyglot-covers: python.urllib.robotparser.can-fetch-before-read-denies
# polyglot-covers: python.urllib.robotparser.user-agent-specific-before-default
# polyglot-covers: python.urllib.robotparser.user-agent-product-token-casefold
# polyglot-covers: python.urllib.robotparser.allow-disallow-path-prefix
# polyglot-covers: python.urllib.robotparser.allow-disallow-first-match-trap
# polyglot-covers: python.urllib.robotparser.empty-disallow-allows
# polyglot-covers: python.urllib.robotparser.rule-percent-normalization
# polyglot-covers: python.urllib.robotparser.RobotFileParser.set_url
# polyglot-covers: python.urllib.robotparser.RobotFileParser.mtime
# polyglot-covers: python.urllib.robotparser.RobotFileParser.modified
# polyglot-covers: python.urllib.robotparser.RobotFileParser.crawl_delay-3.6
# polyglot-covers: python.urllib.robotparser.RobotFileParser.request_rate-3.6
# polyglot-covers: python.urllib.robotparser.RequestRate
# polyglot-covers: python.urllib.robotparser.invalid-crawl-metadata-none
# polyglot-covers: python.urllib.robotparser.RobotFileParser.site_maps-3.8
# polyglot-covers: python.urllib.robotparser.RobotFileParser.read
# polyglot-covers: python.urllib.robotparser.read-utf8-lines
# polyglot-covers: python.urllib.robotparser.read-401-403-disallow-all
# polyglot-covers: python.urllib.robotparser.read-other-4xx-allow-all
# polyglot-covers: python.urllib.robotparser.read-5xx-remains-conservative
# polyglot-covers: python.urllib.robotparser.read-urlerror-propagates


ROBOTS = [
    "User-agent: SpecialBot",
    "Allow: /private/public",
    "Disallow: /private",
    "",
    "User-agent: *",
    "Disallow: /tmp",
    "Disallow: /caf%C3%A9",
    "Disallow:",
]


def make_http_error(url, code):
    return HTTPError(url, code, "robots status", Message(), None)


def test_before_parse_access_is_denied_then_specific_and_default_rules_apply():
    parser = RobotFileParser()
    assert not parser.can_fetch("SpecialBot", "https://example.test/public")

    parser.parse(ROBOTS)

    assert parser.can_fetch(
        "specialbot/2.0",
        "https://example.test/private/public/index.html",
    )
    assert not parser.can_fetch(
        "SpecialBot/2.0",
        "https://example.test/private/secret",
    )
    assert not parser.can_fetch("OtherBot", "https://example.test/tmp/cache")
    assert parser.can_fetch("OtherBot", "https://example.test/ordinary")
    assert not parser.can_fetch(
        "OtherBot",
        "https://example.test/caf%C3%A9/menu",
    )


def test_first_matching_rule_wins_instead_of_the_longest_path():
    parser = RobotFileParser()
    parser.parse(
        [
            "User-agent: *",
            "Disallow: /private",
            "Allow: /private/public",
        ],
    )

    # 宽规则先出现后，后面的具体 Allow 不会覆盖它。
    assert not parser.can_fetch("AnyBot", "https://example.test/private/public")


def test_parse_exposes_rate_delay_sitemaps_and_modification_time():
    parser = RobotFileParser("https://example.test/robots.txt")
    assert parser.mtime() == 0
    assert parser.host == "example.test"
    assert parser.path == "/robots.txt"

    parser.parse(
        [
            "Sitemap: https://example.test/sitemap.xml",
            "User-agent: ExampleBot",
            "Crawl-delay: 6",
            "Request-rate: 3/20",
            "Disallow: /private",
            "",
            "User-agent: *",
            "Crawl-delay: invalid",
            "Request-rate: invalid",
            "Disallow:",
        ],
    )

    rate = parser.request_rate("ExampleBot/1.0")
    assert parser.mtime() > 0
    assert parser.crawl_delay("ExampleBot") == 6
    assert (rate.requests, rate.seconds) == (3, 20)
    assert parser.crawl_delay("OtherBot") is None
    assert parser.request_rate("OtherBot") is None
    assert parser.site_maps() == ["https://example.test/sitemap.xml"]


def test_read_decodes_utf8_and_feeds_lines_to_parser(monkeypatch):
    body = "User-agent: *\nDisallow: /私有\n".encode("utf-8")
    monkeypatch.setattr(
        urllib_request,
        "urlopen",
        lambda url: BytesIO(body),
    )
    parser = RobotFileParser("https://example.test/robots.txt")

    parser.read()

    assert not parser.can_fetch("AnyBot", "https://example.test/私有/page")


def test_read_maps_http_statuses_to_conservative_or_permissive_flags(monkeypatch):
    """401/403 全拒绝，其他 4xx 全允许，5xx 保持保守状态。"""

    def failing_urlopen(url):
        code = int(url.rsplit("/", 1)[-1])
        raise make_http_error(url, code)

    monkeypatch.setattr(urllib_request, "urlopen", failing_urlopen)

    forbidden = RobotFileParser("https://example.test/403")
    missing = RobotFileParser("https://example.test/404")
    server_error = RobotFileParser("https://example.test/503")
    forbidden.read()
    missing.read()
    server_error.read()

    assert not forbidden.can_fetch("AnyBot", "https://example.test/")
    assert missing.can_fetch("AnyBot", "https://example.test/")
    assert not server_error.can_fetch("AnyBot", "https://example.test/")


def test_read_does_not_swallow_connection_level_urlerror(monkeypatch):
    def unavailable(url):
        raise URLError("offline")

    monkeypatch.setattr(urllib_request, "urlopen", unavailable)
    parser = RobotFileParser("https://example.test/robots.txt")

    with pytest.raises(URLError):
        parser.read()
