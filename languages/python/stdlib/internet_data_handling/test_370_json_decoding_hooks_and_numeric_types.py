"""370｜object hooks 的分派优先级与数字解析类型。

object_hook 在每个 object 完成后由内向外调用；object_pairs_hook 改收有序 pair 列表，并在两者
同时提供时具有优先级，因此能发现重复名称。parse_float/parse_int 收到原始数字 token 字符串，
可避免先经过二进制 float；parse_constant 只处理 NaN/Infinity 扩展，不处理 null/true/false。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.object_hook
# polyglot-covers: python.json.object-hook-inner-before-outer
# polyglot-covers: python.json.object_pairs_hook
# polyglot-covers: python.json.object-pairs-hook-preserves-duplicate-names
# polyglot-covers: python.json.object-pairs-hook-precedes-object-hook
# polyglot-covers: python.json.parse_float
# polyglot-covers: python.json.parse_int
# polyglot-covers: python.json.parse_constant
# polyglot-covers: python.json.parse-constant-nan-infinity-only
# polyglot-covers: python.json.decimal-number-decoding-workflow

from decimal import Decimal
import json

import pytest


def test_object_hook_replaces_inner_objects_before_their_parent_is_built():
    calls = []

    def hook(value):
        calls.append(value.copy())
        if value.get("type") == "point":
            return (value["x"], value["y"])
        return value

    decoded = json.loads(
        '{"name": "shape", "location": {"type": "point", "x": 2, "y": 3}}',
        object_hook=hook,
    )
    assert decoded == {"name": "shape", "location": (2, 3)}
    assert calls[0] == {"type": "point", "x": 2, "y": 3}
    assert calls[1] == decoded


def test_pairs_hook_sees_duplicates_and_suppresses_object_hook():
    object_calls = []
    pair_calls = []

    def pairs_hook(pairs):
        pair_calls.append(pairs)
        return pairs

    decoded = json.loads(
        '{"x": 1, "x": 2}',
        object_hook=lambda value: object_calls.append(value),
        object_pairs_hook=pairs_hook,
    )
    assert decoded == [("x", 1), ("x", 2)]
    assert pair_calls == [[("x", 1), ("x", 2)]]
    assert object_calls == []


def test_numeric_hooks_receive_lexemes_before_default_number_conversion():
    decoded = json.loads(
        '{"price": 1.10, "count": 7}',
        parse_float=Decimal,
        parse_int=lambda token: ("integer-token", token),
    )
    assert decoded == {
        "price": Decimal("1.10"),
        "count": ("integer-token", "7"),
    }

    seen = []
    assert json.loads("[NaN, Infinity, -Infinity]", parse_constant=seen.append) == [
        None,
        None,
        None,
    ]
    assert seen == ["NaN", "Infinity", "-Infinity"]
    assert json.loads("[null, true, false]", parse_constant=seen.append) == [None, True, False]


def test_parse_constant_can_reject_nonstandard_numeric_tokens():
    def reject(token):
        raise ValueError(f"non-standard number: {token}")

    with pytest.raises(ValueError, match="non-standard number: NaN"):
        json.loads("NaN", parse_constant=reject)
