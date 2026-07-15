"""372｜NaN/Infinity、重复名称与顶层 scalar 的兼容性边界。

默认编码器/解码器接受 NaN 与无穷大，这是 JavaScript 风格扩展而非标准 JSON；互操作接口应在
编码侧 allow_nan=False，并在解码侧用 parse_constant 拒绝。重复成员默认保留最后值，可能掩盖
恶意字段；需要 object_pairs_hook 才能检测。RFC 7159 允许顶层 scalar，模块从不强制 object/array。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.allow_nan
# polyglot-covers: python.json.default-encodes-nan-infinity-extension
# polyglot-covers: python.json.default-decodes-nan-infinity-extension
# polyglot-covers: python.json.allow-nan-false-valueerror
# polyglot-covers: python.json.strict-number-decoding-parse-constant-workflow
# polyglot-covers: python.json.repeated-object-names-last-wins
# polyglot-covers: python.json.repeated-name-validation-trap
# polyglot-covers: python.json.top-level-scalar
# polyglot-covers: python.json.nan-not-equal-itself-trap

import json
import math

import pytest


def test_default_nan_and_infinity_extensions_require_opt_in_for_interoperability():
    encoded = json.dumps([math.nan, math.inf, -math.inf])
    assert encoded == "[NaN, Infinity, -Infinity]"
    decoded = json.loads(encoded)
    assert math.isnan(decoded[0])
    assert decoded[1:] == [math.inf, -math.inf]
    assert decoded[0] != decoded[0]

    with pytest.raises(ValueError, match="Out of range float values"):
        json.dumps(math.nan, allow_nan=False)

    def reject(token):
        raise ValueError(token)

    with pytest.raises(ValueError, match="Infinity"):
        json.loads("Infinity", parse_constant=reject)


def test_duplicate_names_default_to_last_value_but_pairs_hook_can_reject_them():
    document = '{"role": "user", "role": "admin"}'
    assert json.loads(document) == {"role": "admin"}

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    with pytest.raises(ValueError, match="duplicate key: role"):
        json.loads(document, object_pairs_hook=unique_object)


@pytest.mark.parametrize(
    ("document", "expected"),
    [("null", None), ("true", True), ('"text"', "text"), ("42", 42)],
)
def test_top_level_value_may_be_a_scalar(document, expected):
    assert json.loads(document) == expected
