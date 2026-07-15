"""427｜html.escape/unescape 的文本、属性与 HTML5 字符引用规则。

escape 默认同时处理 ``&<>`` 和两种引号，适合放入带引号的 HTML 属性；quote=False 只适合
普通文本节点。unescape 按 HTML5 规则接受命名、十进制、十六进制甚至部分缺分号引用，也会把
历史数值区间映射和非法码点修正成 Unicode；它不是 XML 严格实体解析器。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.html.escape
# polyglot-covers: python.html.escape-amp-lt-gt
# polyglot-covers: python.html.escape-quote-true
# polyglot-covers: python.html.escape-quote-false
# polyglot-covers: python.html.escape-attribute-context
# polyglot-covers: python.html.unescape
# polyglot-covers: python.html.unescape-named-reference
# polyglot-covers: python.html.unescape-decimal-reference
# polyglot-covers: python.html.unescape-hex-reference
# polyglot-covers: python.html.unescape-optional-semicolon-html5
# polyglot-covers: python.html.unescape-invalid-codepoint-replacement
# polyglot-covers: python.html.unescape-windows-1252-remap
# polyglot-covers: python.html.unescape-unknown-reference-preserved

from html import escape, unescape


def test_escape_distinguishes_text_content_from_quoted_attribute_context():
    source = 'Tom & <tag title="x">\'s'

    assert escape(source) == "Tom &amp; &lt;tag title=&quot;x&quot;&gt;&#x27;s"
    assert escape(source, quote=False) == 'Tom &amp; &lt;tag title="x"&gt;\'s'


def test_unescape_accepts_named_decimal_hex_and_legacy_semicolonless_references():
    assert unescape("&gt; &#62; &#x3E;") == "> > >"
    assert unescape("Copyright &copy 2024") == "Copyright © 2024"
    assert unescape("&doesnotexist;") == "&doesnotexist;"


def test_unescape_applies_html5_error_recovery_instead_of_strict_unicode_decoding():
    assert unescape("&#0;") == "\ufffd"
    assert unescape("&#xD800;") == "\ufffd"
    # HTML5 为兼容旧页面，把 0x80 映射为 Windows-1252 的 EURO SIGN，而不是 U+0080。
    assert unescape("&#128;") == "€"
