"""Unicode 字符串、编码单元与用户可见字符。

共同问题：长度和索引按什么单位；编码何时变成字节；组合字符是否等于一个元素；
非法编码如何报告。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/python/builtins/test_021_text_sequence_str.py

import unicodedata

import pytest


def test_string_length_and_index_use_unicode_code_points():
    text = "A😀"

    assert len(text) == 2
    assert text[1] == "😀"
    assert len(text.encode("utf-16-le")) == 6


def test_utf8_encoding_turns_text_into_bytes():
    text = "咖啡"
    encoded = text.encode("utf-8")

    assert len(text) == 2
    assert len(encoded) == 6
    assert encoded.decode("utf-8") == text


def test_combining_sequence_contains_multiple_code_points():
    decomposed = "e\u0301"
    composed = unicodedata.normalize("NFC", decomposed)

    assert len(decomposed) == 2
    assert len(composed) == 1
    assert decomposed != composed


def test_decode_error_policy_is_explicit():
    invalid = b"\xff"

    with pytest.raises(UnicodeDecodeError):
        invalid.decode("utf-8")
    assert invalid.decode("utf-8", errors="replace") == "\ufffd"
