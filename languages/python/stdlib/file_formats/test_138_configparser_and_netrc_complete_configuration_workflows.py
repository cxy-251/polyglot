"""138｜``configparser`` 映射代理、DEFAULT、类型转换与结构修改。

``ConfigParser`` 的值模型始终以字符串为核心；section access 返回的是连回
parser 的 live proxy，而不是普通字典副本。DEFAULT 会被每个 section 继承，
因此删除 override、
clear section、fallback lookup 等操作都有容易误判的优先级。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.configparser.ConfigParser python.configparser.string-values
# polyglot-covers: python.configparser.sections python.configparser.DEFAULTSECT
# polyglot-covers: python.configparser.case-insensitive-options
# polyglot-covers: python.configparser.case-sensitive-sections
# polyglot-covers: python.configparser.SectionProxy python.configparser.live-section-proxy
# polyglot-covers: python.configparser.inherited-defaults python.configparser.delete-reveals-default
# polyglot-covers: python.configparser.section-clear-defaults
# polyglot-covers: python.configparser.default-delete-error
# polyglot-covers: python.configparser.fallback python.configparser.default-before-fallback
# polyglot-covers: python.configparser.getint python.configparser.getfloat
# polyglot-covers: python.configparser.getboolean python.configparser.invalid-boolean
# polyglot-covers: python.configparser.converters python.configparser.custom-getter
# polyglot-covers: python.configparser.add-section python.configparser.remove-option
# polyglot-covers: python.configparser.remove-section python.configparser.NoSectionError
# polyglot-covers: python.configparser.DuplicateSectionError python.configparser.optionxform




import configparser
from decimal import Decimal
import pytest
import io
import os
from netrc import NetrcParseError, netrc

def test_values_remain_strings_and_default_options_are_inherited():
    """构造参数和 read_dict 会 stringify 值；DEFAULT 不出现在 sections() 中。"""

    parser = configparser.ConfigParser(defaults={"Timeout": 30})
    parser.read_dict(
        {
            "Production": {
                "Port": 8080,
                "Enabled": "YeS",
                "Ratio": 1.25,
            }
        }
    )

    assert parser.sections() == ["Production"]
    assert parser.has_section("DEFAULT") is False
    assert parser.has_section("Production") is True
    assert parser["Production"]["TIMEOUT"] == "30"
    assert parser["Production"]["port"] == "8080"
    assert parser["Production"]["ratio"] == "1.25"
    assert list(parser["Production"])[-1] == "timeout"


def test_section_names_are_case_sensitive_but_option_names_are_not():
    """默认 optionxform=str.lower；section 名则保留大小写并可同时存在。"""

    parser = configparser.ConfigParser()
    parser.read_string("[Prod]\nHost = upper\n[prod]\nHOST = lower\n")

    assert parser.sections() == ["Prod", "prod"]
    assert parser["Prod"]["host"] == "upper"
    assert parser["Prod"]["HOST"] == "upper"
    assert list(parser["prod"]) == ["host"]

    case_sensitive = configparser.ConfigParser()
    case_sensitive.optionxform = str
    case_sensitive.read_string("[service]\nToken = A\ntoken = B\n")
    assert dict(case_sensitive["service"]) == {"Token": "A", "token": "B"}


def test_section_proxy_is_live_and_deleting_override_reveals_default():
    """proxy 修改原 parser；删除 section-local 同名值后，继承值会重新可见。"""

    parser = configparser.ConfigParser()
    parser.read_dict(
        {
            "DEFAULT": {"theme": "dark", "locale": "zh_CN"},
            "app": {"theme": "light", "workers": "4"},
        }
    )
    app = parser["app"]

    app["workers"] = "8"
    assert parser.getint("app", "workers") == 8

    del app["theme"]
    assert app["theme"] == "dark"

    app.clear()
    assert dict(app) == {"theme": "dark", "locale": "zh_CN"}
    with pytest.raises(KeyError, match="locale"):
        del app["locale"]


def test_default_value_has_precedence_over_explicit_fallback():
    """fallback 只处理完全缺失，不能覆盖 section 或 DEFAULT 中已有的 option。"""

    parser = configparser.ConfigParser({"retries": "3"})
    parser.read_dict({"worker": {"name": "alpha"}})
    worker = parser["worker"]

    assert worker.get("retries", "99") == "3"
    assert worker.get("missing", "99") == "99"
    assert parser.get("worker", "missing", fallback=None) is None
    with pytest.raises(configparser.NoOptionError):
        parser.get("worker", "missing")

    # parser-level get 的第三个位置参数不是 dict.get 的 default；
    # 3.2+ 相关参数均为 keyword-only。
    with pytest.raises(TypeError):
        parser.get("worker", "missing", "99")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1", True),
        ("YES", True),
        ("true", True),
        ("On", True),
        ("0", False),
        ("NO", False),
        ("false", False),
        ("Off", False),
    ],
)
def test_getboolean_recognizes_documented_case_insensitive_words(text, expected):
    """不能用 bool('false') 解析配置；非空字符串在 Python 中一律 truthy。"""

    parser = configparser.ConfigParser()
    parser.read_dict({"feature": {"enabled": text}})

    assert parser.getboolean("feature", "enabled") is expected


def test_typed_getters_convert_on_access_and_report_bad_values():
    """内部仍是 str；typed getters 只在读取时转换，失败不会静默 fallback。"""

    parser = configparser.ConfigParser()
    parser.read_dict(
        {"limits": {"workers": "4", "ratio": "0.75", "enabled": "perhaps"}}
    )

    assert parser["limits"]["workers"] == "4"
    assert parser.getint("limits", "workers") == 4
    assert parser["limits"].getfloat("ratio") == 0.75
    with pytest.raises(ValueError, match="Not a boolean"):
        parser.getboolean("limits", "enabled", fallback=True)


def test_custom_converter_adds_getter_to_parser_and_section_proxy():
    """converters 的 key 生成 get<key>，parser 与 SectionProxy 都获得该入口。"""

    parser = configparser.ConfigParser(converters={"decimal": Decimal})
    parser.read_dict({"price": {"amount": "19.95"}})

    assert parser.getdecimal("price", "amount") == Decimal("19.95")
    assert parser["price"].getdecimal("amount") == Decimal("19.95")
    assert parser["price"].getdecimal("missing", Decimal("0")) == Decimal("0")


def test_structural_mutators_report_duplicates_missing_sections_and_absence():
    """remove_* 用 bool 区分是否删除；set 对不存在 section 不会自动创建。"""

    parser = configparser.ConfigParser()
    parser.add_section("service")
    parser.set("service", "port", "8080")

    with pytest.raises(configparser.DuplicateSectionError):
        parser.add_section("service")
    with pytest.raises(configparser.NoSectionError):
        parser.set("missing", "key", "value")

    assert parser.remove_option("service", "port") is True
    assert parser.remove_option("service", "port") is False
    assert parser.remove_section("service") is True
    assert parser.remove_section("service") is False


# 139｜``configparser`` Basic/Extended interpolation、lookup 顺序与延迟错误。
#
# 插值发生在 ``get`` 时而不是 parse 时：原始文本可以先被接受，缺少引用、
# 非法语法和
# 递归过深会在实际读取 option 时暴露。BasicInterpolation 使用 ``%(name)s``，而
# ExtendedInterpolation 使用 ``${section:option}``；两者的转义字符也不同。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.configparser.BasicInterpolation python.configparser.percent-escape
# polyglot-covers: python.configparser.lazy-interpolation python.configparser.raw-get
# polyglot-covers: python.configparser.interpolation-none python.configparser.RawConfigParser
# polyglot-covers: python.configparser.ExtendedInterpolation
# polyglot-covers: python.configparser.cross-section-reference
# polyglot-covers: python.configparser.dollar-escape python.configparser.interpolation-vars
# polyglot-covers: python.configparser.lookup-order python.configparser.InterpolationError
# polyglot-covers: python.configparser.InterpolationMissingOptionError
# polyglot-covers: python.configparser.InterpolationSyntaxError
# polyglot-covers: python.configparser.InterpolationDepthError
# polyglot-covers: python.configparser.MAX_INTERPOLATION_DEPTH




def test_basic_interpolation_resolves_chains_lazily_and_escapes_percent():
    """引用可晚于使用点定义；%% 是 literal percent，raw=True 返回原文。"""

    parser = configparser.ConfigParser()
    parser.read_string(
        """
        [paths]
        pictures = %(home)s/%(user)s/Pictures
        user = alice
        home = /srv
        gain = 80%%
        """
    )

    assert parser.get("paths", "pictures") == "/srv/alice/Pictures"
    assert parser.get("paths", "pictures", raw=True) == "%(home)s/%(user)s/Pictures"
    assert parser["paths"]["gain"] == "80%"


def test_interpolation_is_evaluated_against_current_values_not_cached_output():
    """SectionProxy 每次动态读取；修改依赖值会立即改变派生 option。"""

    parser = configparser.ConfigParser({"root": "/opt/app"})
    parser.read_string("[paths]\ncache = %(root)s/cache\n")

    assert parser["paths"]["cache"] == "/opt/app/cache"
    parser["DEFAULT"]["root"] = "/tmp/app"
    assert parser["paths"]["cache"] == "/tmp/app/cache"


def test_vars_override_section_and_defaults_during_get():
    """get(..., vars=...) 的临时值优先于 section 与 DEFAULT，但不会写回 parser。"""

    parser = configparser.ConfigParser({"root": "/default"})
    parser.read_string("[paths]\nroot = /section\ndata = %(root)s/data\n")

    assert parser.get("paths", "data") == "/section/data"
    assert parser.get("paths", "data", vars={"root": "/request"}) == "/request/data"
    assert parser["paths"]["root"] == "/section"


def test_extended_interpolation_can_reference_other_sections_and_escape_dollar():
    """${section:option} 可跨 section 串联；$$ 是 literal dollar。"""

    parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    parser.read_string(
        """
        [common]
        root = /srv
        [runtime]
        version = 3.10
        lib = ${common:root}/python/${version}
        command = ${lib}/bin/python
        price = $$20
        """
    )

    assert parser["runtime"]["command"] == "/srv/python/3.10/bin/python"
    assert parser["runtime"]["price"] == "$20"


def test_interpolation_can_be_disabled_globally_or_per_get():
    """interpolation=None 是推荐的 raw parser；raw=True 只跳过当前一次展开。"""

    source = "[template]\nvalue = %(literal)s\n"
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(source)
    assert parser["template"]["value"] == "%(literal)s"

    raw_parser = configparser.RawConfigParser()
    raw_parser.read_string(source)
    assert raw_parser.get("template", "value") == "%(literal)s"

    interpolating = configparser.ConfigParser({"literal": "expanded"})
    interpolating.read_string(source)
    assert interpolating.get("template", "value", raw=True) == "%(literal)s"


def test_missing_interpolation_target_fails_only_when_value_is_requested():
    """read_string 成功不代表每个 option 可读取；插值引用在 get 时解析。"""

    parser = configparser.ConfigParser()
    parser.read_string("[paths]\ndata = %(missing)s/data\n")

    assert parser.get("paths", "data", raw=True) == "%(missing)s/data"
    with pytest.raises(configparser.InterpolationMissingOptionError) as caught:
        parser.get("paths", "data")

    assert caught.value.option == "data"
    assert caught.value.reference == "missing"


def test_invalid_percent_syntax_raises_specialized_interpolation_error():
    """literal % 必须写成 %%；错误同样延迟到 get，方便 raw 模式读取原文。"""

    parser = configparser.ConfigParser()
    parser.read_string("[metric]\nusage = 80%\n")

    assert parser.get("metric", "usage", raw=True) == "80%"
    with pytest.raises(configparser.InterpolationSyntaxError):
        parser.get("metric", "usage")


def test_recursive_interpolation_is_bounded_instead_of_looping_forever():
    """循环引用超过 MAX_INTERPOLATION_DEPTH 后产生 InterpolationDepthError。"""

    parser = configparser.ConfigParser()
    parser.read_string("[cycle]\na = %(b)s\nb = %(a)s\n")

    assert configparser.MAX_INTERPOLATION_DEPTH == 10
    with pytest.raises(configparser.InterpolationDepthError) as caught:
        parser.get("cycle", "a")

    assert isinstance(caught.value, configparser.InterpolationError)


# 140｜``configparser`` 多来源合并、INI 变体、序列化与 parse errors。
#
# ``read`` 适合一组“可能存在”的配置文件，会忽略无法打开的路径并按顺序
# overlay；必须存在的来源应由调用方打开后交给 ``read_file``。parser 可适配
# 无值 option、delimiter 和 inline comment 等 INI 方言，但过度启用 inline comment
# 会让值中的字符不可转义。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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


# 141｜``netrc`` credential lookup、default fallback、macdef 与权限保护。
#
# ``netrc`` 把 machine/default 条目映射为三元组，并保留 ``macdef`` 的原始命令行。
# 无参数读取 POSIX ``~/.netrc`` 时会检查 owner/mode，防止其他用户读取
# password；显式路径主要用于调用方指定的文件，并不会触发这项 home-file
# 安全策略。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.netrc.netrc python.netrc.machine
# polyglot-covers: python.netrc.login python.netrc.account
# polyglot-covers: python.netrc.password python.netrc.default
# polyglot-covers: python.netrc.authenticators python.netrc.default-fallback
# polyglot-covers: python.netrc.missing-host python.netrc.hosts
# polyglot-covers: python.netrc.macdef python.netrc.macros
# polyglot-covers: python.netrc.repr python.netrc.comments-discarded
# polyglot-covers: python.netrc.NetrcParseError python.netrc.error-filename-line
# polyglot-covers: python.netrc.utf8-first python.netrc.ascii-password-limit
# polyglot-covers: python.netrc.default-home-file python.netrc.posix-permission-check
# polyglot-covers: python.netrc.explicit-file-no-permission-check




def test_machine_entries_and_default_follow_documented_lookup_order(tmp_path):
    """exact machine 优先；未知 host 回退到 default；两者都没有时返回 None。"""

    path = tmp_path / "credentials.netrc"
    path.write_text(
        """
        machine api.example
          login alice
          account operations
          password p@ss-word!
        machine mirror.example login bob password token-2
        default login guest password anonymous@example.invalid
        """,
        encoding="utf-8",
    )

    credentials = netrc(path)

    assert credentials.authenticators("api.example") == (
        "alice",
        "operations",
        "p@ss-word!",
    )
    assert credentials.authenticators("mirror.example") == ("bob", None, "token-2")
    assert credentials.authenticators("unknown.example") == (
        "guest",
        None,
        "anonymous@example.invalid",
    )
    assert credentials.hosts["default"][0] == "guest"

    without_default = tmp_path / "without-default.netrc"
    without_default.write_text(
        "machine only.example login one password secret\n",
        encoding="utf-8",
    )
    assert netrc(without_default).authenticators("unknown.example") is None


def test_macdef_preserves_command_lines_until_a_blank_line(tmp_path):
    """macro 由空行终止；macros value 是含原 newline 的命令行 list。"""

    path = tmp_path / "macros.netrc"
    path.write_text(
        """machine ftp.example login alice password secret
macdef deploy
cd releases
put app.tar.gz

macdef cleanup
delete app.old

""",
        encoding="utf-8",
    )

    parsed = netrc(path)

    assert parsed.macros == {
        "deploy": ["cd releases\n", "put app.tar.gz\n"],
        "cleanup": ["delete app.old\n"],
    }


def test_password_punctuation_is_allowed_but_whitespace_terminates_token(tmp_path):
    """password 可含 ASCII punctuation；空白会开始下一个 token 并导致错误。"""

    valid = tmp_path / "punctuation.netrc"
    valid.write_text(
        "machine api.example login alice password !#$%&()*+,-./:;=?@[]^_{}~\n",
        encoding="utf-8",
    )
    assert netrc(valid).authenticators("api.example")[2] == "!#$%&()*+,-./:;=?@[]^_{}~"

    invalid = tmp_path / "whitespace.netrc"
    invalid.write_text(
        "machine api.example login alice password two words\n",
        encoding="utf-8",
    )
    with pytest.raises(NetrcParseError, match="bad follower token"):
        netrc(invalid)


def test_repr_serializes_data_but_discards_comments_and_can_be_parsed_again(tmp_path):
    """repr 是 netrc-format dump，不是 source-preserving editor；comment 不会保留。"""

    original = tmp_path / "original.netrc"
    original.write_text(
        "# deployment account\n"
        "machine api.example login alice account ops password secret\n",
        encoding="utf-8",
    )
    parsed = netrc(original)

    dumped = repr(parsed)
    assert "deployment account" not in dumped
    assert "machine api.example" in dumped

    round_trip = tmp_path / "round-trip.netrc"
    round_trip.write_text(dumped, encoding="utf-8")
    assert netrc(round_trip).hosts == parsed.hosts


def test_parse_error_exposes_filename_and_line_for_diagnostics(tmp_path):
    """不完整 machine entry 抛专用异常，并提供 filename/lineno。"""

    path = tmp_path / "broken.netrc"
    path.write_text("machine api.example login\n", encoding="utf-8")

    with pytest.raises(NetrcParseError) as caught:
        netrc(path)

    assert caught.value.filename == path
    # 具体计数由 shlex 的 newline consumption 决定，异常始终携带可展示的行号。
    assert isinstance(caught.value.lineno, int)
    assert caught.value.lineno >= 1
    assert caught.value.msg


def test_explicit_file_uses_utf8_first_and_does_not_enforce_home_mode(tmp_path):
    """3.10 先以 UTF-8 解码；显式 file 即使 mode 0644 也不走 ~/.netrc 检查。"""

    path = tmp_path / "explicit.netrc"
    path.write_text(
        "# UTF-8 注释：部署凭据\n"
        "machine api.example login alice account operations password ascii-secret\n",
        encoding="utf-8",
    )
    path.chmod(0o644)

    assert netrc(path).authenticators("api.example") == (
        "alice",
        "operations",
        "ascii-secret",
    )


@pytest.mark.skipif(os.name != "posix", reason="owner/mode 检查只属于 POSIX")
def test_default_home_file_rejects_group_or_other_access(tmp_path, monkeypatch):
    """无参数才把文件当作用户 secret；0600 通过，0644 因 password 被拒绝。"""

    home_file = tmp_path / ".netrc"
    home_file.write_text(
        "machine api.example login alice password secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))

    home_file.chmod(0o644)
    with pytest.raises(NetrcParseError, match="access too permissive"):
        netrc()

    home_file.chmod(0o600)
    assert netrc().authenticators("api.example") == ("alice", None, "secret")
