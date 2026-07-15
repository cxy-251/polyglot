"""367｜JSON 转换表、顺序保持与文本/二进制流 API。

JSON 的 object/array/null/boolean/number 分别映射到 Python dict/list/None/bool/int 或 float；tuple
编码后也变成 array，往返会得到 list。dumps/dump 始终产生或写入 str，load 则能从 text stream
或包含 UTF-8/16/32 的 binary stream 读取。对象成员顺序在底层容器有序时保持。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.dumps
# polyglot-covers: python.json.loads
# polyglot-covers: python.json.dump
# polyglot-covers: python.json.load
# polyglot-covers: python.json.python-json-conversion-table
# polyglot-covers: python.json.tuple-encodes-array-decodes-list
# polyglot-covers: python.json.output-is-str-not-bytes
# polyglot-covers: python.json.dump-requires-text-writer
# polyglot-covers: python.json.load-text-stream
# polyglot-covers: python.json.load-binary-stream
# polyglot-covers: python.json.object-order-preserved

import io
import json

import pytest


def test_basic_python_hierarchy_round_trips_with_documented_type_conversions():
    value = {
        "nothing": None,
        "flags": (True, False),
        "numbers": [3, 2.5],
        "nested": {"name": "polyglot"},
    }
    encoded = json.dumps(value)
    assert isinstance(encoded, str)
    assert json.loads(encoded) == {
        "nothing": None,
        "flags": [True, False],
        "numbers": [3, 2.5],
        "nested": {"name": "polyglot"},
    }


def test_dump_writes_text_and_load_accepts_text_or_binary_streams():
    value = {"first": 1, "second": 2}
    text_stream = io.StringIO()
    assert json.dump(value, text_stream) is None
    assert text_stream.getvalue() == '{"first": 1, "second": 2}'

    text_stream.seek(0)
    assert json.load(text_stream) == value
    assert json.load(io.BytesIO(text_stream.getvalue().encode("utf-8"))) == value

    with pytest.raises(TypeError):
        json.dump(value, io.BytesIO())


def test_input_object_order_survives_encoding_and_decoding():
    value = {"z": 1, "a": 2, "m": 3}
    encoded = json.dumps(value)
    assert encoded == '{"z": 1, "a": 2, "m": 3}'
    assert list(json.loads(encoded)) == ["z", "a", "m"]
