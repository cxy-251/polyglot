"""428｜html.entities 的 HTML5、HTML4 与 XHTML 实体映射表。

html5 的 key 通常含分号，但标准允许省略分号的少数名字会同时出现两种 key；value 可能包含
多个 Unicode 码点，不能假设总能用 chr() 表示。name2codepoint/codepoint2name 是 HTML4
整数映射，entitydefs 则保留 XHTML 1.0 的替换文本，三者并非 html5 的可逆视图。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.html.entities.html5
# polyglot-covers: python.html.entities.html5-semicolon-key
# polyglot-covers: python.html.entities.html5-semicolonless-alias
# polyglot-covers: python.html.entities.html5-multi-codepoint-value
# polyglot-covers: python.html.entities.name2codepoint
# polyglot-covers: python.html.entities.codepoint2name
# polyglot-covers: python.html.entities.entitydefs
# polyglot-covers: python.html.entities-html4-versus-html5
# polyglot-covers: python.html.entities-global-table-do-not-mutate

from html.entities import codepoint2name, entitydefs, html5, name2codepoint


def test_html5_table_includes_semicolon_keys_optional_aliases_and_multi_codepoints():
    assert html5["gt;"] == ">"
    assert html5["copy;"] == "©"
    assert html5["copy"] == "©"
    assert html5["NotEqualTilde;"] == "≂̸"
    assert len(html5["NotEqualTilde;"]) == 2


def test_legacy_tables_map_names_codepoints_and_xhtml_replacement_text():
    assert name2codepoint["nbsp"] == 160
    assert codepoint2name[160] == "nbsp"
    assert entitydefs["nbsp"] == "\xa0"
    assert "NotEqualTilde" not in name2codepoint


def test_global_entity_tables_should_be_copied_before_application_customization():
    local_entities = dict(html5)
    local_entities["project;"] = "P"

    assert local_entities["project;"] == "P"
    assert "project;" not in html5
