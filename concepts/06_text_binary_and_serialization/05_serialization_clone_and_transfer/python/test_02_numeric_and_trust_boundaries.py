"""数值模型、类型恢复与信任边界。

共同问题：通用数据格式是否保留语言数值类型；非标准数值如何处理；
自定义反序列化如何限制可构造类型和字段。
"""

# polyglot-family: text_binary_and_serialization
# polyglot-concept: serialization_clone_and_transfer
# polyglot-related: languages/python/stdlib/104-110_internet_data_handling/
# polyglot-related+: test_104_json_complete_encoding_decoding_streaming_and_cli_workflows.py

import json

import pytest


def test_json_keeps_python_integer_precision_but_changes_other_python_types():
    large = 9_007_199_254_740_993
    original = {1: (large,)}

    decoded = json.loads(json.dumps(original))

    assert decoded == {"1": [large]}
    assert decoded["1"][0] == large

    # Python int 可精确恢复该值，但 JSON number 没有统一精度上限；JavaScript Number
    # 消费者会丢精度。键和 tuple 也已分别变为字符串与 list。


def test_non_finite_numbers_require_an_explicit_interoperability_policy():
    assert json.dumps(float("nan")) == "NaN"

    with pytest.raises(ValueError, match="compliant"):
        json.dumps(float("nan"), allow_nan=False)

    # 默认 NaN 是 Python 扩展，不是标准 JSON；跨语言协议应使用 allow_nan=False。


def test_object_hook_restores_only_a_whitelisted_shape():
    class Point:
        def __init__(self, x):
            self.x = x

    def restore(value):
        if value.get("type") != "Point":
            return value
        if set(value) != {"type", "x"} or not isinstance(value["x"], int):
            raise ValueError("invalid Point payload")
        return Point(value["x"])

    decoded = json.loads('{"type":"Point","x":3}', object_hook=restore)
    assert isinstance(decoded, Point)
    assert decoded.x == 3

    with pytest.raises(ValueError, match="payload"):
        json.loads('{"type":"Point","x":"3","extra":true}', object_hook=restore)

    # object_hook 不应按输入名称动态 import/eval 类型；先验证标签、字段集合与值域。
