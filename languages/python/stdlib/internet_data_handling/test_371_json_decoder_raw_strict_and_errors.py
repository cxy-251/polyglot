"""371｜JSONDecoder.raw_decode、strict 控制字符与结构化错误位置。

decode/loads 要求输入只含一个完整文档；raw_decode 返回值和结束索引，适合由上层 framing 逻辑
从缓冲区取一个值，但它不会自动越过开头空白。strict=False 仅允许字符串中的 U+0000..U+001F
原始控制字符，不会放宽缺引号、尾逗号等其他语法。JSONDecodeError 保存原文和精确行列。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.JSONDecoder
# polyglot-covers: python.json.JSONDecoder.decode
# polyglot-covers: python.json.JSONDecoder.raw_decode
# polyglot-covers: python.json.raw-decode-returns-end-index
# polyglot-covers: python.json.raw-decode-does-not-skip-leading-whitespace
# polyglot-covers: python.json.JSONDecoder.strict
# polyglot-covers: python.json.strict-false-allows-control-characters
# polyglot-covers: python.json.JSONDecodeError
# polyglot-covers: python.json.JSONDecodeError.msg
# polyglot-covers: python.json.JSONDecodeError.doc
# polyglot-covers: python.json.JSONDecodeError.pos
# polyglot-covers: python.json.JSONDecodeError.lineno
# polyglot-covers: python.json.JSONDecodeError.colno
# polyglot-covers: python.json.trailing-data-error

import json

import pytest


def test_raw_decode_returns_the_first_value_and_exact_buffer_end_index():
    decoder = json.JSONDecoder()
    text = '{"a": 1} trailing'
    value, end = decoder.raw_decode(text)
    assert value == {"a": 1}
    assert end == len('{"a": 1}')
    assert text[end:] == " trailing"

    with pytest.raises(json.JSONDecodeError) as leading_error:
        decoder.raw_decode("  1")
    assert leading_error.value.pos == 0
    value, end = decoder.raw_decode("  1", idx=2)
    assert (value, end) == (1, 3)


def test_strict_false_only_relaxes_raw_control_characters_inside_strings():
    document = '"left\tright"'
    with pytest.raises(json.JSONDecodeError):
        json.loads(document)
    assert json.JSONDecoder(strict=False).decode(document) == "left\tright"
    with pytest.raises(json.JSONDecodeError):
        json.JSONDecoder(strict=False).decode('{"a": 1,}')


def test_decode_error_exposes_message_document_offset_line_and_column():
    document = '{"a": 1,}'
    with pytest.raises(json.JSONDecodeError) as raised:
        json.loads(document)
    error = raised.value
    assert isinstance(error, ValueError)
    assert error.msg == "Expecting property name enclosed in double quotes"
    assert error.doc == document
    assert error.pos == 8
    assert error.lineno == 1
    assert error.colno == 9

    with pytest.raises(json.JSONDecodeError, match="Extra data"):
        json.loads("1 2")
