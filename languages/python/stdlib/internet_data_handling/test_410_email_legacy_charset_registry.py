"""410｜email.charset 的全局 alias、字符集策略与 codec 注册表。

add_alias/add_charset/add_codec 会修改模块级注册表，影响之后构造的每个 Charset；这类全局状态
在测试和长进程中很容易泄漏。本文件用 monkeypatch 替换为副本后再演示注册流程。SHORTEST
只允许用于 header，body 必须选择明确编码或不编码。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.charset.add_alias
# polyglot-covers: python.email.charset.ALIASES-registry
# polyglot-covers: python.email.charset.add_charset
# polyglot-covers: python.email.charset.CHARSETS-registry
# polyglot-covers: python.email.charset.add_codec
# polyglot-covers: python.email.charset.CODEC_MAP-registry
# polyglot-covers: python.email.charset.QP
# polyglot-covers: python.email.charset.BASE64
# polyglot-covers: python.email.charset.SHORTEST
# polyglot-covers: python.email.charset.shortest-not-valid-for-body
# polyglot-covers: python.email.charset.global-registry-isolation

import email.charset as charset_module

import pytest


def isolate_registries(monkeypatch):
    monkeypatch.setattr(charset_module, "ALIASES", dict(charset_module.ALIASES))
    monkeypatch.setattr(charset_module, "CHARSETS", dict(charset_module.CHARSETS))
    monkeypatch.setattr(charset_module, "CODEC_MAP", dict(charset_module.CODEC_MAP))


def test_custom_alias_charset_and_codec_form_one_resolution_pipeline(monkeypatch):
    isolate_registries(monkeypatch)
    charset_module.add_alias("x-demo-alias", "x-demo")
    charset_module.add_charset(
        "x-demo",
        charset_module.QP,
        charset_module.BASE64,
        "utf-8",
    )
    charset_module.add_codec("x-demo", "utf-8")

    configured = charset_module.Charset("x-demo-alias")
    assert configured.input_charset == "x-demo"
    assert configured.output_charset == "utf-8"
    assert configured.header_encoding == charset_module.QP
    assert configured.body_encoding == charset_module.BASE64
    assert configured.input_codec == "utf-8"
    assert configured.output_codec == "utf-8"


def test_shortest_strategy_is_rejected_for_message_bodies(monkeypatch):
    isolate_registries(monkeypatch)
    with pytest.raises(ValueError, match="SHORTEST"):
        charset_module.add_charset(
            "x-invalid",
            charset_module.QP,
            charset_module.SHORTEST,
        )
