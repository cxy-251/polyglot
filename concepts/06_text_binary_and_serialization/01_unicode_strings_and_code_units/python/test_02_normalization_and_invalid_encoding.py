"""规范化、非法编码与无损边界。

共同问题：规范等价文本是否自动相等；非法输入是拒绝、替换还是保留；
字符串模型能否直接表达孤立编码单元。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/python/stdlib/036-040_text_processing/test_037_string_textwrap_unicodedata.py
# polyglot-related: languages/python/stdlib/041-042_binary_data/test_042_codecs_registry_and_streams.py

import unicodedata

import pytest


def test_normalization_is_explicit_and_changes_equality():
    composed = "\u00e9"
    decomposed = "e\u0301"

    assert composed != decomposed
    assert unicodedata.normalize("NFC", decomposed) == composed
    assert unicodedata.normalize("NFD", composed) == decomposed


def test_lone_surrogate_is_a_string_value_but_strict_utf8_rejects_it():
    lone_surrogate = "\ud800"

    assert len(lone_surrogate) == 1
    with pytest.raises(UnicodeEncodeError):
        lone_surrogate.encode("utf-8")

    encoded = lone_surrogate.encode("utf-8", errors="surrogatepass")
    assert encoded == b"\xed\xa0\x80"
    assert encoded.decode("utf-8", errors="surrogatepass") == lone_surrogate

    # surrogatepass 是 Python 专用无损通道，产物不是合法 Unicode UTF-8 文本；跨系统
    # 协议应优先 strict，只有明确保存原始编码单元时才使用该策略。


def test_decode_replacement_is_lossy_but_deterministic():
    invalid = b"a\xffb"

    assert invalid.decode("utf-8", errors="replace") == "a\ufffdb"
    assert invalid.decode("utf-8", errors="ignore") == "ab"
