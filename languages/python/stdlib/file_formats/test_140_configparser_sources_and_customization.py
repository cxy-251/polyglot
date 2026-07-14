"""140｜``configparser`` 多来源合并、INI 变体、序列化与 parse errors。

``read`` 适合一组“可能存在”的配置文件，会忽略无法打开的路径并按顺序
overlay；必须存在的来源应由调用方打开后交给 ``read_file``。parser 可适配
无值 option、delimiter 和 inline comment 等 INI 方言，但过度启用 inline comment
会让值中的字符不可转义。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.configparser.read python.configparser.optional-files
# polyglot-covers: python.configparser.multiple-file-overlay python.configparser.read-encoding
# polyglot-covers: python.configparser.read-file python.configparser.read-string
# polyglot-covers: python.configparser.read-dict python.configparser.source-name
# polyglot-covers: python.configparser.strict python.configparser.DuplicateOptionError
# polyglot-covers: python.configparser.duplicate-section-source
# polyglot-covers: python.configparser.single-source-duplicates
# polyglot-covers: python.configparser.allow-no-value python.configparser.delimiters
# polyglot-covers: python.configparser.comment-prefixes python.configparser.inline-comment-prefixes
# polyglot-covers: python.configparser.inline-comment-no-escape
# polyglot-covers: python.configparser.multiline-value python.configparser.empty-lines-in-values
# polyglot-covers: python.configparser.write python.configparser.space-around-delimiters
# polyglot-covers: python.configparser.comments-not-preserved python.configparser.default-section
# polyglot-covers: python.configparser.MissingSectionHeaderError python.configparser.ParsingError
# polyglot-covers: python.configparser.error-source-line python.configparser.BOOLEAN_STATES

import configparser
import io

import pytest


def test_read_ignores_missing_paths_and_overlays_existing_files_in_order(tmp_path):
    """read 返回成功读取的路径；后文件只覆盖冲突项，不删除其他 option。"""

    base = tmp_path / "base.ini"
    override = tmp_path / "override.ini"
    missing = tmp_path / "missing.ini"
    base.write_text("[app]\nhost = localhost\nport = 8000\n", encoding="utf-8")
    override.write_text("[app]\nport = 9000\nname = 示例\n", encoding="utf-8")

    parser = configparser.ConfigParser()
    loaded = parser.read([missing, base, override], encoding="utf-8")

    assert loaded == [base, override]
    assert dict(parser["app"]) == {
        "host": "localhost",
        "port": "9000",
        "name": "示例",
    }


def test_read_file_is_for_required_open_stream_and_uses_source_name():
    """read_file 不吞输入错误；source 会进入异常，以报告真正配置来源。"""

    parser = configparser.ConfigParser()
    with pytest.raises(configparser.MissingSectionHeaderError) as caught:
        parser.read_file(io.StringIO("key = value\n"), source="required.ini")

    assert caught.value.source == "required.ini"
    assert caught.value.lineno == 1
    assert isinstance(caught.value, configparser.ParsingError)


def test_strict_mode_rejects_duplicates_within_one_source():
    """canonicalization 后 Key/key 同名；异常记录 source、section 和 option。"""

    parser = configparser.ConfigParser()
    with pytest.raises(configparser.DuplicateOptionError) as caught:
        parser.read_string(
            "[app]\nKey = first\nkey = second\n",
            source="duplicate.ini",
        )

    assert caught.value.source == "duplicate.ini"
    assert caught.value.section == "app"
    assert caught.value.option == "key"
    assert caught.value.lineno == 3

    with pytest.raises(configparser.DuplicateSectionError):
        configparser.ConfigParser().read_string("[app]\na=1\n[app]\nb=2\n")


def test_strict_mode_still_allows_intentional_overlay_from_separate_sources():
    """strict 的 duplicate scope 是一次 read_* 调用，不会阻止 later source override。"""

    parser = configparser.ConfigParser()
    parser.read_string("[app]\nport = 8000\n", source="defaults.ini")
    parser.read_string("[app]\nport = 9000\n", source="local.ini")

    assert parser.getint("app", "port") == 9000


def test_allow_no_value_and_custom_delimiter_support_an_ini_variant():
    """无 delimiter 的 option 只有显式 allow_no_value 才合法，其值为 None。"""

    source = "[flags]\nenabled\npath => /srv/app=>cache\n"
    parser = configparser.ConfigParser(
        allow_no_value=True,
        delimiters=("=>",),
    )
    parser.read_string(source)

    assert parser["flags"]["enabled"] is None
    # delimiter 只按首次出现处分割，所以同样字符可以留在 value 中。
    assert parser["flags"]["path"] == "/srv/app=>cache"

    with pytest.raises(configparser.ParsingError):
        configparser.ConfigParser(delimiters=("=>",)).read_string(source)


def test_inline_comment_prefix_changes_data_and_has_no_escape_mechanism():
    """默认 # 只注释整行；inline 模式会截断值尾 #，且没有 escape。"""

    source = "[shell]\ncolor = #336699\ncommand = run # production\n"
    normal = configparser.ConfigParser()
    normal.read_string(source)
    assert normal["shell"]["color"] == "#336699"
    assert normal["shell"]["command"] == "run # production"

    inline = configparser.ConfigParser(inline_comment_prefixes=("#",))
    inline.read_string(source)
    assert inline["shell"]["color"] == ""
    assert inline["shell"]["command"] == "run"


def test_empty_lines_can_end_a_multiline_value_to_make_hidden_keys_visible():
    """empty_lines_in_values=False 让空行结束 continuation，显出后续 key。"""

    source = "[section]\nkey = first\n  second\n\n  hidden = separate\n"

    permissive = configparser.ConfigParser(empty_lines_in_values=True)
    permissive.read_string(source)
    assert permissive["section"]["key"] == "first\nsecond\n\nhidden = separate"
    assert "hidden" not in permissive["section"]

    split = configparser.ConfigParser(empty_lines_in_values=False)
    split.read_string(source)
    assert split["section"]["key"] == "first\nsecond"
    assert split["section"]["hidden"] == "separate"


def test_write_round_trip_normalizes_format_and_does_not_preserve_comments():
    """write 输出可再次解析，但不保留原 comment 和排版。"""

    parser = configparser.ConfigParser()
    parser.read_string("# heading\n[App]\nMixedCase: value  # data\n")
    output = io.StringIO()

    assert parser.write(output, space_around_delimiters=False) is None
    serialized = output.getvalue()

    assert serialized == "[App]\nmixedcase=value  # data\n\n"
    assert "heading" not in serialized

    restored = configparser.ConfigParser()
    restored.read_string(serialized)
    assert restored["App"]["mixedcase"] == "value  # data"


def test_default_section_name_controls_read_and_can_change_write_spelling():
    """修改 default_section 可把同一 defaults 转写成另一名称。"""

    parser = configparser.ConfigParser(default_section="common")
    parser.read_string("[common]\nroot=/srv\n[app]\npath=%(root)s/app\n")
    assert parser["app"]["path"] == "/srv/app"

    parser.default_section = "DEFAULT"
    output = io.StringIO()
    parser.write(output)
    assert output.getvalue().startswith("[DEFAULT]\nroot = /srv\n")


def test_boolean_states_can_adapt_domain_words_without_global_mutation():
    """在实例上定制 BOOLEAN_STATES，避免修改类级 dict 污染其他 parser。"""

    parser = configparser.ConfigParser()
    parser.BOOLEAN_STATES = {"enabled": True, "disabled": False}
    parser.read_dict({"feature": {"cache": "disabled"}})

    assert parser.getboolean("feature", "cache") is False
