"""465｜saxutils 文本转义、反转义与可直接拼入标签的属性引用。

``escape`` 始终处理 ``&<>``，附加 entities 只扩充规则，不能覆盖核心 XML 转义。``unescape``
只认识 ``&amp;``/``&lt;``/``&gt;`` 和调用方规则，不是通用实体解析器。``quoteattr`` 连外层引号
一起返回，并选择能减少转义的引号；双/单引号同时出现时使用双引号并转义其中的双引号。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.xml.sax.saxutils.escape
# polyglot-covers: python.xml.sax.saxutils.escape.entities
# polyglot-covers: python.xml.sax.saxutils.unescape
# polyglot-covers: python.xml.sax.saxutils.unescape.entities
# polyglot-covers: python.xml.sax.saxutils.quoteattr
# polyglot-covers: python.xml.sax.saxutils.quoteattr-selects-delimiter
# polyglot-covers: python.xml.sax.saxutils-not-general-translation

from xml.sax import saxutils


def test_escape_always_handles_xml_metacharacters_and_then_custom_entities():
    escaped = saxutils.escape(
        "5 < 6 & 7 > 3 ©",
        {"©": "&copy;"},
    )

    assert escaped == "5 &lt; 6 &amp; 7 &gt; 3 &copy;"


def test_unescape_handles_only_the_builtin_and_explicit_entity_spellings():
    unescaped = saxutils.unescape(
        "&lt;tag&gt;&amp;&copy;&unknown;",
        {"&copy;": "©"},
    )

    assert unescaped == "<tag>&©&unknown;"
    # 单轮顺序不会递归解码：&amp;lt; 先留下 &lt;，不会在同次调用中再变成 '<'。
    assert saxutils.unescape("&amp;lt;") == "&lt;"


def test_quoteattr_returns_delimiters_and_chooses_the_less_costly_quote_style():
    assert saxutils.quoteattr("plain") == '"plain"'
    assert saxutils.quoteattr('has "double"') == "'has \"double\"'"
    assert saxutils.quoteattr("has 'single'") == '"has \'single\'"'
    assert saxutils.quoteattr("both ' and \"") == '"both \' and &quot;"'
