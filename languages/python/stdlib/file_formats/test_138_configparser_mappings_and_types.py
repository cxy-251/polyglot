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
