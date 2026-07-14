"""139｜``configparser`` Basic/Extended interpolation、lookup 顺序与延迟错误。

插值发生在 ``get`` 时而不是 parse 时：原始文本可以先被接受，缺少引用、
非法语法和
递归过深会在实际读取 option 时暴露。BasicInterpolation 使用 ``%(name)s``，而
ExtendedInterpolation 使用 ``${section:option}``；两者的转义字符也不同。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

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

import configparser

import pytest


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
