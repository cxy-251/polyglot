"""524｜学习 http.cookies 的 SimpleCookie、BaseCookie 与 Morsel 完整语义。

SimpleCookie 把 Python 值转换成字符串，并把不适合直接出现在 Cookie 头中的字符转义。
读取 ``value`` 得到逻辑文本，``coded_value`` 才是可以放在线路上的表示；不要自行拼接头部。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.http.cookies.SimpleCookie
# polyglot-covers: python.http.cookies.SimpleCookie-assignment
# polyglot-covers: python.http.cookies.SimpleCookie-stringifies-values
# polyglot-covers: python.http.cookies.SimpleCookie.Morsel-values
# polyglot-covers: python.http.cookies.Morsel.value-vs-coded-value
# polyglot-covers: python.http.cookies.cookie-value-quoting
# polyglot-covers: python.http.cookies.cookie-value-control-character-escaping
# polyglot-covers: python.http.cookies.BaseCookie.output
# polyglot-covers: python.http.cookies.BaseCookie.output-header-separator
# polyglot-covers: python.http.cookies.BaseCookie.output-sorted-by-key
# polyglot-covers: python.http.cookies.encoded-value-round-trip

from http.cookies import BaseCookie, CookieError, Morsel, SimpleCookie

import pytest


def test_assignment_builds_morsels_and_stringifies_non_string_values():
    cookie = SimpleCookie()

    cookie["session"] = "abc123"
    cookie["visits"] = 7

    assert isinstance(cookie["session"], Morsel)
    assert cookie["session"].value == "abc123"
    assert cookie["session"].coded_value == "abc123"
    assert cookie["visits"].value == "7"
    assert cookie["visits"].coded_value == "7"


def test_values_needing_quotes_are_encoded_and_can_be_loaded_back():
    cookie = SimpleCookie()
    cookie["note"] = "space, semicolon; and ünicode\n"

    coded = cookie["note"].coded_value

    # 控制字符和分隔符若原样进入头部，可能截断或注入新的头字段。模块会生成带引号的
    # Cookie 表示，并使用反斜杠转义，而逻辑 value 仍保留原字符串。
    assert coded.startswith('"') and coded.endswith('"')
    assert "\n" not in coded
    assert cookie["note"].value == "space, semicolon; and ünicode\n"

    parsed = SimpleCookie()
    parsed.load(f"note={coded}")

    assert parsed["note"].value == cookie["note"].value


def test_output_supports_custom_header_separator_and_deterministic_key_order():
    cookie = SimpleCookie()
    cookie["zeta"] = "last"
    cookie["alpha"] = "first"

    rendered = cookie.output(header="X-Cookie:", sep="\n")

    assert rendered.splitlines() == [
        "X-Cookie: alpha=first",
        "X-Cookie: zeta=last",
    ]
    assert str(cookie) == cookie.output()

# SimpleCookie.load 的字符串/映射输入、属性归属与非法名称。

# polyglot-covers: python.http.cookies.BaseCookie.load-string
# polyglot-covers: python.http.cookies.BaseCookie.load-mapping
# polyglot-covers: python.http.cookies.SimpleCookie-load-multiple-values
# polyglot-covers: python.http.cookies.cookie-attributes-attach-to-morsel
# polyglot-covers: python.http.cookies.cookie-secure-flag
# polyglot-covers: python.http.cookies.cookie-httponly-flag
# polyglot-covers: python.http.cookies.cookie-samesite-3.8
# polyglot-covers: python.http.cookies.cookie-name-valid-character-colon-3.3
# polyglot-covers: python.http.cookies.CookieError
# polyglot-covers: python.http.cookies.invalid-cookie-name
# polyglot-covers: python.http.cookies.reserved-cookie-name

def test_load_parses_multiple_values_and_attaches_attributes_to_the_right_value():
    cookie = SimpleCookie()

    cookie.load(
        "session=abc; Path=/app; Secure; HttpOnly; SameSite=Lax; theme=dark",
    )

    assert set(cookie) == {"session", "theme"}
    assert cookie["session"].value == "abc"
    assert cookie["session"]["path"] == "/app"
    assert cookie["session"]["secure"] is True
    assert cookie["session"]["httponly"] is True
    assert cookie["session"]["samesite"] == "Lax"
    assert cookie["theme"].value == "dark"
    assert cookie["theme"]["path"] == ""


def test_load_mapping_uses_the_same_value_encoding_pipeline_as_assignment():
    loaded = SimpleCookie()
    assigned = SimpleCookie()

    loaded.load({"count": 3, "label": "hello world"})
    assigned["count"] = 3
    assigned["label"] = "hello world"

    assert loaded.output() == assigned.output()
    assert loaded["count"].value == "3"


def test_cookie_name_accepts_colon_but_rejects_spaces_and_reserved_attributes():
    cookie = SimpleCookie()
    cookie["app:session"] = "ok"

    assert cookie["app:session"].value == "ok"

    with pytest.raises(CookieError):
        cookie["bad name"] = "no"

    # Path 是 Morsel 的属性名，不能同时被当作顶层 Cookie 名，否则输出语义会含糊。
    with pytest.raises(CookieError):
        cookie["path"] = "not-a-cookie"

# BaseCookie 的自定义值编解码钩子、映射加载与 JavaScript 输出。

# polyglot-covers: python.http.cookies.BaseCookie
# polyglot-covers: python.http.cookies.BaseCookie.value_encode
# polyglot-covers: python.http.cookies.BaseCookie.value_decode
# polyglot-covers: python.http.cookies.BaseCookie-custom-typed-values
# polyglot-covers: python.http.cookies.BaseCookie-load-string-custom-codec
# polyglot-covers: python.http.cookies.BaseCookie-load-mapping-custom-codec
# polyglot-covers: python.http.cookies.BaseCookie.js_output
# polyglot-covers: python.http.cookies.Morsel.js_output

class IntegerCookie(BaseCookie):
    """只为展示编解码协议保留整数语义，不实现应用级校验。"""

    def value_encode(self, value):
        number = int(value)
        return number, str(number)

    def value_decode(self, value):
        return int(value), value


def test_custom_codec_keeps_typed_values_for_assignment_and_string_loading():
    cookie = IntegerCookie()

    cookie["assigned"] = 7
    cookie.load("parsed=42")

    assert cookie["assigned"].value == 7
    assert cookie["assigned"].coded_value == "7"
    assert cookie["parsed"].value == 42
    assert cookie["parsed"].coded_value == "42"


def test_mapping_load_also_calls_value_encode_instead_of_value_decode():
    cookie = IntegerCookie()

    cookie.load({"visits": "003"})

    # 映射输入代表 Python 对象，走 encode 后会规范化；字符串输入代表线路文本，走 decode。
    assert cookie["visits"].value == 3
    assert cookie["visits"].coded_value == "3"


def test_javascript_output_uses_each_morsels_rendered_cookie_assignment():
    cookie = IntegerCookie()
    cookie["visits"] = 5
    cookie["visits"]["path"] = "/app"

    script = cookie.js_output(attrs=["path"])

    assert '<script type="text/javascript">' in script
    assert 'document.cookie = "visits=5; Path=/app";' in script

# Morsel 的固定属性表、大小写归一化、布尔标志与选择性渲染。

# polyglot-covers: python.http.cookies.Morsel
# polyglot-covers: python.http.cookies.Morsel.set
# polyglot-covers: python.http.cookies.Morsel-fixed-reserved-attributes
# polyglot-covers: python.http.cookies.Morsel-case-insensitive-attribute-keys
# polyglot-covers: python.http.cookies.Morsel.isReservedKey
# polyglot-covers: python.http.cookies.Morsel.OutputString
# polyglot-covers: python.http.cookies.Morsel.OutputString-attrs-filter
# polyglot-covers: python.http.cookies.Morsel.output
# polyglot-covers: python.http.cookies.Morsel-boolean-flag-rendering
# polyglot-covers: python.http.cookies.Morsel-max-age-path-samesite-rendering

RESERVED_ATTRIBUTES = {
    "expires",
    "path",
    "comment",
    "domain",
    "max-age",
    "secure",
    "version",
    "httponly",
    "samesite",
}


def make_session_morsel():
    morsel = Morsel()
    morsel.set("session", "abc", "abc")
    return morsel


def test_morsel_starts_with_the_fixed_reserved_attribute_mapping():
    morsel = make_session_morsel()

    assert set(morsel) == RESERVED_ATTRIBUTES
    assert all(value == "" for value in morsel.values())
    assert morsel.isReservedKey("Path")
    assert morsel.isReservedKey("HTTPONLY")
    assert not morsel.isReservedKey("priority")


def test_attribute_assignment_is_case_insensitive_and_flags_render_without_values():
    morsel = make_session_morsel()
    morsel["Path"] = "/app"
    morsel["MAX-AGE"] = 60
    morsel["SameSite"] = "Lax"
    morsel["Secure"] = True
    morsel["HttpOnly"] = True

    rendered = morsel.OutputString()

    assert morsel["path"] == "/app"
    assert "Path=/app" in rendered
    assert "Max-Age=60" in rendered
    assert "SameSite=Lax" in rendered
    assert "; Secure" in rendered
    assert "; HttpOnly" in rendered
    assert "Secure=True" not in rendered


def test_output_can_filter_attributes_and_omits_false_flags():
    morsel = make_session_morsel()
    morsel["path"] = "/app"
    morsel["secure"] = False
    morsel["httponly"] = True

    selected = morsel.OutputString(attrs=["PATH", "secure"])
    header = morsel.output(header="Set-Cookie:", attrs=["path", "httponly"])

    assert selected == "session=abc; Path=/app"
    assert header == "Set-Cookie: session=abc; HttpOnly; Path=/app"

# Morsel 的受控更新、复制/相等语义、只读主值与错误边界。

# polyglot-covers: python.http.cookies.Morsel.update-validation-3.5
# polyglot-covers: python.http.cookies.Morsel.setdefault-validation-3.5
# polyglot-covers: python.http.cookies.Morsel.copy-returns-morsel-3.5
# polyglot-covers: python.http.cookies.Morsel.copy-independent-attributes
# polyglot-covers: python.http.cookies.Morsel.equality-includes-key-values-3.5
# polyglot-covers: python.http.cookies.Morsel.key-read-only-3.7
# polyglot-covers: python.http.cookies.Morsel.value-read-only-3.7
# polyglot-covers: python.http.cookies.Morsel.coded_value-read-only-3.7
# polyglot-covers: python.http.cookies.Morsel.set-invalid-key-cookieerror
# polyglot-covers: python.http.cookies.Morsel.set-reserved-key-cookieerror

def make_morsel(key="session", value="abc", coded_value="abc"):
    morsel = Morsel()
    morsel.set(key, value, coded_value)
    return morsel


def test_all_mapping_mutators_reject_unknown_attribute_names():
    morsel = make_morsel()

    with pytest.raises(CookieError):
        morsel.update({"priority": "high"})

    with pytest.raises(CookieError):
        morsel.setdefault("priority", "high")

    assert "priority" not in morsel


def test_copy_is_a_morsel_and_attribute_changes_are_independent():
    original = make_morsel()
    original["path"] = "/"

    copied = original.copy()
    copied["path"] = "/app"

    assert isinstance(copied, Morsel)
    assert original["path"] == "/"
    assert copied["path"] == "/app"
    assert copied != original

    same = original.copy()
    assert same == original
    same.set("other", "abc", "abc")
    assert same != original


def test_primary_fields_are_read_only_and_set_validates_cookie_keys():
    morsel = make_morsel()

    for attribute in ("key", "value", "coded_value"):
        with pytest.raises(AttributeError):
            setattr(morsel, attribute, "changed")

    with pytest.raises(CookieError):
        morsel.set("bad name", "x", "x")

    with pytest.raises(CookieError):
        morsel.set("path", "x", "x")
