"""369｜default 扩展点、JSONEncoder 分块输出与循环引用检查。

未知类型会交给 default callable 或 JSONEncoder.default；实现无法识别的对象时必须调用 super，
让基类抛 TypeError，不能返回原对象再次形成循环。iterencode 产生若干 str chunk，适合逐块写入；
它并不提供消息 framing。默认循环检查会把自引用容器转成 ValueError，关闭后可能递归至崩溃。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.default-callback
# polyglot-covers: python.json.JSONEncoder
# polyglot-covers: python.json.JSONEncoder.default
# polyglot-covers: python.json.JSONEncoder.default-call-super-fallback
# polyglot-covers: python.json.JSONEncoder.encode
# polyglot-covers: python.json.JSONEncoder.iterencode
# polyglot-covers: python.json.iterencode-yields-str-chunks
# polyglot-covers: python.json.cls-custom-encoder
# polyglot-covers: python.json.check_circular
# polyglot-covers: python.json.circular-reference-valueerror
# polyglot-covers: python.json.disable-circular-check-recursion-trap

import json

import pytest


class ComplexEncoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, complex):
            return {"__complex__": True, "real": value.real, "imag": value.imag}
        return super().default(value)


def test_default_callable_and_encoder_subclass_convert_unknown_types():
    encoded_by_callback = json.dumps(
        {"number": 3 + 4j},
        default=lambda value: [value.real, value.imag],
    )
    assert json.loads(encoded_by_callback) == {"number": [3.0, 4.0]}

    encoded_by_class = json.dumps(3 + 4j, cls=ComplexEncoder, sort_keys=True)
    assert json.loads(encoded_by_class) == {
        "__complex__": True,
        "imag": 4.0,
        "real": 3.0,
    }
    with pytest.raises(TypeError):
        ComplexEncoder().encode(object())


def test_iterencode_chunks_join_to_the_same_document_as_encode():
    value = {"values": [1, 2, 3]}
    encoder = json.JSONEncoder(sort_keys=True)
    chunks = list(encoder.iterencode(value))
    assert chunks
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert "".join(chunks) == encoder.encode(value)


def test_circular_reference_check_reports_a_clear_error_before_recursion():
    recursive = []
    recursive.append(recursive)
    with pytest.raises(ValueError, match="Circular reference"):
        json.dumps(recursive)
    with pytest.raises(RecursionError):
        json.dumps(recursive, check_circular=False)
