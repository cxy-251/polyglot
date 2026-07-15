"""529｜学习 CookieJar 的提取、策略、生命周期、Cookie 对象与文件持久化。

CookieJar 不负责发起网络请求；它只依赖 urllib.request.Request 与具有 info() 的响应对象。
提取和返回是两个策略检查阶段，Secure Cookie 不会回送到 HTTP，Path 也不是普通前缀匹配。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

from email.message import Message
from http.cookiejar import Cookie
from http.cookiejar import CookieJar
from http.cookiejar import DefaultCookiePolicy
from http.cookiejar import LoadError
from http.cookiejar import LWPCookieJar
from http.cookiejar import MozillaCookieJar
from urllib.request import Request

import pytest


# polyglot-covers: python.http.cookiejar.CookieJar
# polyglot-covers: python.http.cookiejar.CookieJar.extract_cookies
# polyglot-covers: python.http.cookiejar.CookieJar.add_cookie_header
# polyglot-covers: python.http.cookiejar.response-info-interface
# polyglot-covers: python.http.cookiejar.urllib-request-interface
# polyglot-covers: python.http.cookiejar.netscape-set-cookie-default
# polyglot-covers: python.http.cookiejar.cookie-default-discard
# polyglot-covers: python.http.cookiejar.cookie-domain-from-origin
# polyglot-covers: python.http.cookiejar.cookie-secure-return-filter
# polyglot-covers: python.http.cookiejar.cookie-path-return-filter
# polyglot-covers: python.http.cookiejar.httponly-nonstandard-attribute
# polyglot-covers: python.http.cookiejar.existing-cookie-header-not-overwritten



class ExtractionCookieResponse:
    def __init__(self, *header_values):
        self.headers = Message()
        for value in header_values:
            self.headers.add_header("Set-Cookie", value)

    def info(self):
        return self.headers


def test_extract_cookies_builds_a_session_cookie_from_response_metadata():
    jar = CookieJar()
    origin = Request("https://example.test/app/login")
    response = ExtractionCookieResponse("session=abc; Path=/app; Secure; HttpOnly")

    jar.extract_cookies(response, origin)

    [cookie] = list(jar)
    assert cookie.name == "session"
    assert cookie.value == "abc"
    assert cookie.domain == "example.test"
    assert not cookie.domain_specified
    assert cookie.path == "/app"
    assert cookie.secure
    assert cookie.discard
    assert cookie.has_nonstandard_attr("HttpOnly")


def cookie_header_for(jar, url):
    request = Request(url)
    jar.add_cookie_header(request)
    return request.get_header("Cookie")


def test_add_cookie_header_applies_secure_and_path_boundary_rules():
    jar = CookieJar()
    jar.extract_cookies(
        ExtractionCookieResponse("session=abc; Path=/app; Secure"),
        Request("https://example.test/app/login"),
    )

    assert cookie_header_for(jar, "https://example.test/app") == "session=abc"
    assert cookie_header_for(jar, "https://example.test/app/page") == "session=abc"
    assert cookie_header_for(jar, "http://example.test/app/page") is None

    # /app 是目录边界；若只做 startswith，/application 会被错误地视为匹配。
    assert cookie_header_for(jar, "https://example.test/application") is None
    assert cookie_header_for(jar, "https://example.test/other") is None


def test_add_cookie_header_preserves_an_explicit_caller_header():
    jar = CookieJar()
    jar.extract_cookies(
        ExtractionCookieResponse("stored=value; Path=/"),
        Request("http://example.test/"),
    )
    request = Request(
        "http://example.test/",
        headers={"Cookie": "manual=value"},
    )

    jar.add_cookie_header(request)

    assert request.get_header("Cookie") == "manual=value"

# 530｜CookieJar 的身份键、替换、精确清除、会话清除与过期清理。
#
# Cookie 的身份由 domain/path/name 三元组决定：同三元组会替换，不同 Path 可同名共存。
# discard 表示随会话丢弃，与 expires 是否存在是不同维度；两个清理 API 不应混为一谈。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.http.cookiejar.CookieJar.set_cookie
# polyglot-covers: python.http.cookiejar.CookieJar-identity-domain-path-name
# polyglot-covers: python.http.cookiejar.CookieJar-replaces-same-identity
# polyglot-covers: python.http.cookiejar.CookieJar-same-name-different-path
# polyglot-covers: python.http.cookiejar.CookieJar.__iter__
# polyglot-covers: python.http.cookiejar.CookieJar.__len__
# polyglot-covers: python.http.cookiejar.CookieJar.clear
# polyglot-covers: python.http.cookiejar.CookieJar.clear-keyerror
# polyglot-covers: python.http.cookiejar.CookieJar.clear_session_cookies
# polyglot-covers: python.http.cookiejar.CookieJar.clear_expired_cookies
# polyglot-covers: python.http.cookiejar.Cookie.discard-vs-expires




def make_lifecycle_cookie(
    name,
    value,
    *,
    path="/",
    discard=True,
    expires=None,
):
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain="example.test",
        domain_specified=False,
        domain_initial_dot=False,
        path=path,
        path_specified=True,
        secure=False,
        expires=expires,
        discard=discard,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def test_same_identity_replaces_value_while_different_paths_coexist():
    jar = CookieJar()
    jar.set_cookie(make_lifecycle_cookie("theme", "light"))
    jar.set_cookie(make_lifecycle_cookie("theme", "dark"))
    jar.set_cookie(make_lifecycle_cookie("theme", "admin", path="/admin"))

    assert len(jar) == 2
    assert {(cookie.path, cookie.value) for cookie in jar} == {
        ("/", "dark"),
        ("/admin", "admin"),
    }


def test_clear_targets_an_exact_identity_and_missing_identity_raises_keyerror():
    jar = CookieJar()
    jar.set_cookie(make_lifecycle_cookie("theme", "root"))
    jar.set_cookie(make_lifecycle_cookie("theme", "admin", path="/admin"))

    jar.clear("example.test", "/admin", "theme")

    assert [(cookie.path, cookie.value) for cookie in jar] == [("/", "root")]
    with pytest.raises(KeyError):
        jar.clear("example.test", "/missing", "theme")


def test_session_and_expiry_cleanup_use_different_cookie_flags():
    jar = CookieJar()
    jar.set_cookie(make_lifecycle_cookie("session", "temporary", discard=True))
    jar.set_cookie(
        make_lifecycle_cookie(
            "persistent",
            "future",
            discard=False,
            expires=4_102_444_800,
        ),
    )
    jar.set_cookie(make_lifecycle_cookie("stale", "old", discard=False, expires=1))

    jar.clear_session_cookies()

    assert {cookie.name for cookie in jar} == {"persistent", "stale"}

    jar.clear_expired_cookies()

    assert [cookie.name for cookie in jar] == ["persistent"]

# 531｜CookieJar.make_cookies 的协议版本、RFC 2109 降级与受策略/无策略写入。
#
# 默认策略只启用 Netscape Set-Cookie，并把 RFC 2109 的 Version=1 表示降为版本 0；
# RFC 2965 必须显式开启。make_cookies 只解析，set_cookie_if_ok 才检查来源策略。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.http.cookiejar.CookieJar.make_cookies
# polyglot-covers: python.http.cookiejar.Set-Cookie-netscape-default
# polyglot-covers: python.http.cookiejar.Set-Cookie2-rfc2965-opt-in
# polyglot-covers: python.http.cookiejar.rfc2109-cookie-marker
# polyglot-covers: python.http.cookiejar.rfc2109-as-netscape-default-downgrade
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.rfc2965
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.rfc2109_as_netscape
# polyglot-covers: python.http.cookiejar.CookieJar.set_cookie_if_ok
# polyglot-covers: python.http.cookiejar.CookieJar.set_cookie-bypasses-policy



class VersionedCookieResponse:
    def __init__(self):
        self.headers = Message()
        self.headers.add_header(
            "Set-Cookie",
            "legacy=one; Version=1; Path=/",
        )
        self.headers.add_header(
            "Set-Cookie2",
            'modern=two; Version=1; Path="/"',
        )

    def info(self):
        return self.headers


def make_foreign_cookie():
    return Cookie(
        version=0,
        name="foreign",
        value="value",
        port=None,
        port_specified=False,
        domain="other.test",
        domain_specified=True,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def test_default_make_cookies_ignores_cookie2_and_downgrades_rfc2109():
    jar = CookieJar()

    cookies = jar.make_cookies(
        VersionedCookieResponse(),
        Request("http://example.test/"),
    )

    assert len(jar) == 0
    assert [cookie.name for cookie in cookies] == ["legacy"]
    assert cookies[0].version == 0
    assert cookies[0].rfc2109


def test_opted_in_policy_parses_both_version_one_header_families():
    policy = DefaultCookiePolicy(
        rfc2965=True,
        rfc2109_as_netscape=False,
    )
    jar = CookieJar(policy)

    cookies = jar.make_cookies(
        VersionedCookieResponse(),
        Request("http://example.test/"),
    )

    assert {cookie.name: cookie.version for cookie in cookies} == {
        "legacy": 1,
        "modern": 1,
    }
    assert next(cookie for cookie in cookies if cookie.name == "legacy").rfc2109


def test_checked_insertion_rejects_foreign_domain_but_set_cookie_is_unconditional():
    jar = CookieJar()
    cookie = make_foreign_cookie()
    origin = Request("http://example.test/")

    jar.set_cookie_if_ok(cookie, origin)
    assert len(jar) == 0

    # set_cookie 是给已受信任调用方的底层入口，不再重跑 CookiePolicy。
    jar.set_cookie(cookie)
    assert list(jar) == [cookie]

# 532｜DefaultCookiePolicy 的阻止/允许域名列表、点前缀语义与动态替换。
#
# 列表项不是 shell 通配符：无前导点只匹配完全相同的域；“.example.test”匹配更深子域，
# 却不匹配裸 example.test。设置允许列表后，未命中的域会被拒绝，容易误伤预期主机。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.blocked_domains
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.set_blocked_domains
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.is_blocked
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.allowed_domains
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.set_allowed_domains
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.is_not_allowed
# polyglot-covers: python.http.cookiejar.policy-domain-exact-entry
# polyglot-covers: python.http.cookiejar.policy-domain-leading-dot-subdomains-only
# polyglot-covers: python.http.cookiejar.policy-ip-address-exact-match
# polyglot-covers: python.http.cookiejar.policy-domain-list-set-cookie-if-ok



def make_domain_cookie(domain):
    return Cookie(
        version=0,
        name="id",
        value=domain,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=False,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def test_blocked_domain_entries_distinguish_exact_hosts_and_subdomains():
    policy = DefaultCookiePolicy(
        blocked_domains=("ads.test", ".tracker.test", "192.0.2.10"),
    )

    assert policy.is_blocked("ads.test")
    assert not policy.is_blocked("sub.ads.test")
    assert not policy.is_blocked("tracker.test")
    assert policy.is_blocked("pixel.tracker.test")
    assert policy.is_blocked("192.0.2.10")
    assert not policy.is_blocked("x.192.0.2.10")

    policy.set_blocked_domains(("new.test",))
    assert policy.blocked_domains() == ("new.test",)
    assert not policy.is_blocked("ads.test")


def test_allowed_list_rejects_every_domain_not_matching_an_entry():
    policy = DefaultCookiePolicy(
        allowed_domains=("example.test", ".partner.test"),
    )

    assert not policy.is_not_allowed("example.test")
    assert policy.is_not_allowed("api.example.test")
    assert policy.is_not_allowed("partner.test")
    assert not policy.is_not_allowed("api.partner.test")
    assert policy.is_not_allowed("unlisted.test")

    policy.set_allowed_domains(None)
    assert policy.allowed_domains() is None
    assert not policy.is_not_allowed("unlisted.test")


def test_domain_lists_participate_in_set_cookie_if_ok():
    policy = DefaultCookiePolicy(blocked_domains=("blocked.test",))
    jar = CookieJar(policy)

    jar.set_cookie_if_ok(
        make_domain_cookie("blocked.test"),
        Request("http://blocked.test/"),
    )
    jar.set_cookie_if_ok(
        make_domain_cookie("example.test"),
        Request("http://example.test/"),
    )

    assert [cookie.domain for cookie in jar] == ["example.test"]

# 533｜CookiePolicy 的域回送严格度、路径边界、Secure 与第三方不可验证请求。
#
# Python 的 Netscape 默认域回送策略较宽松：未带 Domain 的 Cookie 也可能送往子域；开启
# DomainStrictNonDomain 才限制为来源主机。不可验证的第三方请求也可按策略拒绝写入。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.strict_ns_domain
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.DomainLiberal
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.DomainStrictNonDomain
# polyglot-covers: python.http.cookiejar.host-only-cookie-liberal-subdomain-return
# polyglot-covers: python.http.cookiejar.host-only-cookie-strict-exact-return
# polyglot-covers: python.http.cookiejar.CookiePolicy.path_return_ok
# polyglot-covers: python.http.cookiejar.CookiePolicy.return_ok
# polyglot-covers: python.http.cookiejar.cookie-secure-protocol-filter
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.secure_protocols
# polyglot-covers: python.http.cookiejar.DefaultCookiePolicy.strict_ns_unverifiable
# polyglot-covers: python.http.cookiejar.third-party-unverifiable-cookie-rejection



class PolicyCookieResponse:
    def __init__(self, value):
        self.headers = Message()
        self.headers.add_header("Set-Cookie", value)

    def info(self):
        return self.headers


def make_policy_cookie(*, path="/", secure=False):
    return Cookie(
        version=0,
        name="session",
        value="abc",
        port=None,
        port_specified=False,
        domain="example.test",
        domain_specified=False,
        domain_initial_dot=False,
        path=path,
        path_specified=True,
        secure=secure,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def header_for(jar, url):
    request = Request(url)
    jar.add_cookie_header(request)
    return request.get_header("Cookie")


def test_strict_non_domain_mode_prevents_host_only_cookie_leaking_to_subdomains():
    liberal = CookieJar(DefaultCookiePolicy())
    strict = CookieJar(
        DefaultCookiePolicy(
            strict_ns_domain=DefaultCookiePolicy.DomainStrictNonDomain,
        ),
    )
    liberal.set_cookie(make_policy_cookie())
    strict.set_cookie(make_policy_cookie())

    assert header_for(liberal, "http://sub.example.test/") == "session=abc"
    assert header_for(strict, "http://sub.example.test/") is None
    assert header_for(strict, "http://example.test/") == "session=abc"


def test_path_and_secure_filters_are_both_applied_when_returning_cookies():
    jar = CookieJar()
    jar.set_cookie(make_policy_cookie(path="/app", secure=True))

    assert header_for(jar, "https://example.test/app/page") == "session=abc"
    assert header_for(jar, "https://example.test/application") is None
    assert header_for(jar, "http://example.test/app/page") is None


def test_strict_policy_rejects_netscape_cookie_from_unverifiable_third_party():
    request = Request(
        "http://tracker.test/pixel",
        origin_req_host="example.test",
        unverifiable=True,
    )
    response = PolicyCookieResponse("id=tracking; Path=/")
    liberal = CookieJar(DefaultCookiePolicy(strict_ns_unverifiable=False))
    strict = CookieJar(DefaultCookiePolicy(strict_ns_unverifiable=True))

    liberal.extract_cookies(response, request)
    strict.extract_cookies(response, request)

    assert [cookie.name for cookie in liberal] == ["id"]
    assert len(strict) == 0

# 534｜Cookie 值对象的标准字段、端口/域标记、扩展属性与显式过期判断。
#
# Cookie 是 CookieJar 使用的结构化值：specified/initial_dot 等字段记录“如何声明”，不只是
# 最终字符串。未标准化的扩展属性保存在 rest 中，名称区分大小写；is_expired 可传入时间。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.http.cookiejar.Cookie
# polyglot-covers: python.http.cookiejar.Cookie-standard-attributes
# polyglot-covers: python.http.cookiejar.Cookie.port_specified
# polyglot-covers: python.http.cookiejar.Cookie.domain_specified
# polyglot-covers: python.http.cookiejar.Cookie.domain_initial_dot
# polyglot-covers: python.http.cookiejar.Cookie.path_specified
# polyglot-covers: python.http.cookiejar.Cookie.rfc2109
# polyglot-covers: python.http.cookiejar.Cookie.has_nonstandard_attr
# polyglot-covers: python.http.cookiejar.Cookie.get_nonstandard_attr
# polyglot-covers: python.http.cookiejar.Cookie.set_nonstandard_attr
# polyglot-covers: python.http.cookiejar.Cookie-nonstandard-name-case-sensitive
# polyglot-covers: python.http.cookiejar.Cookie.is_expired-explicit-now



def make_versioned_cookie():
    return Cookie(
        version=1,
        name="session",
        value="abc",
        port="80,8080",
        port_specified=True,
        domain=".example.test",
        domain_specified=True,
        domain_initial_dot=True,
        path="/app",
        path_specified=True,
        secure=True,
        expires=100,
        discard=False,
        comment="demonstration",
        comment_url="https://example.test/cookie-info",
        rest={"HttpOnly": None, "SameSite": "Lax"},
        rfc2109=True,
    )


def test_cookie_exposes_wire_value_and_how_scope_attributes_were_declared():
    cookie = make_versioned_cookie()

    assert (cookie.version, cookie.name, cookie.value) == (1, "session", "abc")
    assert (cookie.port, cookie.port_specified) == ("80,8080", True)
    assert (cookie.domain, cookie.domain_specified) == (".example.test", True)
    assert cookie.domain_initial_dot
    assert (cookie.path, cookie.path_specified) == ("/app", True)
    assert cookie.secure and cookie.rfc2109
    assert not cookie.discard


def test_nonstandard_attributes_are_case_sensitive_and_mutable():
    cookie = make_versioned_cookie()

    assert cookie.has_nonstandard_attr("HttpOnly")
    assert not cookie.has_nonstandard_attr("httponly")
    assert cookie.get_nonstandard_attr("SameSite") == "Lax"
    assert cookie.get_nonstandard_attr("Priority", "default") == "default"

    cookie.set_nonstandard_attr("Priority", "High")

    assert cookie.get_nonstandard_attr("Priority") == "High"


def test_is_expired_uses_less_than_or_equal_and_accepts_a_deterministic_now():
    cookie = make_versioned_cookie()

    assert not cookie.is_expired(now=99)
    assert cookie.is_expired(now=100)
    assert cookie.is_expired(now=101)

# 535｜MozillaCookieJar 的 Netscape 文件格式、持久/会话过滤与 PathLike 文件名。
#
# save/load 默认跳过 discard 会话 Cookie 和已过期 Cookie；需要快照会话状态时，写入和读取
# 两端都要显式 ignore_discard。该文本格式便于交换，但不能无损保存所有现代 Cookie 属性。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.http.cookiejar.FileCookieJar
# polyglot-covers: python.http.cookiejar.FileCookieJar.filename-pathlike-3.8
# polyglot-covers: python.http.cookiejar.FileCookieJar.save
# polyglot-covers: python.http.cookiejar.FileCookieJar.load
# polyglot-covers: python.http.cookiejar.FileCookieJar.ignore_discard
# polyglot-covers: python.http.cookiejar.FileCookieJar.ignore_expires
# polyglot-covers: python.http.cookiejar.MozillaCookieJar
# polyglot-covers: python.http.cookiejar.MozillaCookieJar-netscape-text-format
# polyglot-covers: python.http.cookiejar.MozillaCookieJar-persistent-default
# polyglot-covers: python.http.cookiejar.MozillaCookieJar-session-opt-in



def make_mozilla_cookie(name, *, discard, expires):
    return Cookie(
        version=0,
        name=name,
        value="value",
        port=None,
        port_specified=False,
        domain="example.test",
        domain_specified=False,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=expires,
        discard=discard,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def mozilla_names(jar):
    return {cookie.name for cookie in jar}


def test_default_save_and_load_keep_only_unexpired_persistent_cookies(tmp_path):
    path = tmp_path / "cookies.txt"
    jar = MozillaCookieJar(path)
    jar.set_cookie(
        make_mozilla_cookie("persistent", discard=False, expires=4_102_444_800),
    )
    jar.set_cookie(make_mozilla_cookie("session", discard=True, expires=None))
    jar.set_cookie(make_mozilla_cookie("expired", discard=False, expires=1))

    jar.save()

    assert jar.filename == str(path)
    assert path.read_text(encoding="utf-8").startswith(
        "# Netscape HTTP Cookie File",
    )
    loaded = MozillaCookieJar(path)
    loaded.load()
    assert mozilla_names(loaded) == {"persistent"}


def test_ignore_flags_must_be_used_when_session_or_expired_entries_are_desired(tmp_path):
    path = tmp_path / "snapshot.txt"
    jar = MozillaCookieJar(path)
    jar.set_cookie(
        make_mozilla_cookie("persistent", discard=False, expires=4_102_444_800),
    )
    jar.set_cookie(make_mozilla_cookie("session", discard=True, expires=None))
    jar.set_cookie(make_mozilla_cookie("expired", discard=False, expires=1))

    jar.save(ignore_discard=True, ignore_expires=True)

    default_load = MozillaCookieJar(path)
    default_load.load()
    assert mozilla_names(default_load) == {"persistent"}

    snapshot_load = MozillaCookieJar(path)
    snapshot_load.load(ignore_discard=True, ignore_expires=True)
    assert mozilla_names(snapshot_load) == {"persistent", "session", "expired"}

# 536｜LWPCookieJar 的 Set-Cookie3 文本、load 合并、revert 替换与原子失败。
#
# load 把文件内容合并进现有 Jar；revert 则先以文件替换内存状态。revert 若遇到非法文件，会
# 恢复调用前状态。LoadError 是 OSError 子类，适合并入普通文件读取错误处理。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.http.cookiejar.LWPCookieJar
# polyglot-covers: python.http.cookiejar.LWPCookieJar-set-cookie3-format
# polyglot-covers: python.http.cookiejar.FileCookieJar.load-merges
# polyglot-covers: python.http.cookiejar.FileCookieJar.revert-replaces
# polyglot-covers: python.http.cookiejar.FileCookieJar.revert-atomic-on-error
# polyglot-covers: python.http.cookiejar.LoadError
# polyglot-covers: python.http.cookiejar.LoadError-is-OSError
# polyglot-covers: python.http.cookiejar.invalid-cookie-file-loaderror




def make_lwp_cookie(name):
    return Cookie(
        version=0,
        name=name,
        value="value",
        port=None,
        port_specified=False,
        domain="example.test",
        domain_specified=False,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=4_102_444_800,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def lwp_names(jar):
    return {cookie.name for cookie in jar}


def write_saved_jar(path):
    jar = LWPCookieJar(path)
    jar.set_cookie(make_lwp_cookie("saved"))
    jar.save()


def test_lwp_file_has_set_cookie3_header_and_load_merges_existing_state(tmp_path):
    path = tmp_path / "cookies.lwp"
    write_saved_jar(path)
    jar = LWPCookieJar(path)
    jar.set_cookie(make_lwp_cookie("local"))

    jar.load()

    assert path.read_text(encoding="utf-8").startswith("#LWP-Cookies-2.0")
    assert lwp_names(jar) == {"local", "saved"}


def test_revert_replaces_memory_state_with_the_file_snapshot(tmp_path):
    path = tmp_path / "cookies.lwp"
    write_saved_jar(path)
    jar = LWPCookieJar(path)
    jar.set_cookie(make_lwp_cookie("temporary"))

    jar.revert()

    assert lwp_names(jar) == {"saved"}


def test_failed_revert_raises_loaderror_and_restores_previous_memory_state(tmp_path):
    path = tmp_path / "cookies.lwp"
    path.write_text("not an LWP cookie file\n", encoding="utf-8")
    jar = LWPCookieJar(path)
    jar.set_cookie(make_lwp_cookie("keep"))

    assert issubclass(LoadError, OSError)
    with pytest.raises(LoadError):
        jar.revert()

    assert lwp_names(jar) == {"keep"}
