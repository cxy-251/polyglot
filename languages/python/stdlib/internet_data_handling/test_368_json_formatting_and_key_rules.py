"""368｜ensure_ascii、indent、separators、sort_keys 与对象 key 规则。

JSON object 的 key 必须是字符串；编码器会把 int/float/bool/None key 转成字符串，而其他类型默认
报错，skipkeys=True 则静默丢弃。这个转换使 ``loads(dumps(mapping))`` 不保证等于原 mapping。
格式选项只改变文本表示，不应被下游当成业务语义。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.json.ensure_ascii
# polyglot-covers: python.json.ensure-ascii-false-emits-unicode
# polyglot-covers: python.json.indent-int
# polyglot-covers: python.json.indent-string
# polyglot-covers: python.json.separators
# polyglot-covers: python.json.compact-separators-workflow
# polyglot-covers: python.json.sort_keys
# polyglot-covers: python.json.skipkeys
# polyglot-covers: python.json.invalid-dict-key-typeerror
# polyglot-covers: python.json.skipkeys-silently-discards-trap
# polyglot-covers: python.json.nonstring-keys-coerced-to-strings
# polyglot-covers: python.json.mapping-roundtrip-key-type-trap

import json

import pytest


def test_unicode_pretty_and_compact_representations_decode_to_the_same_value():
    value = {"城市": "深圳", "items": [1, 2]}
    escaped = json.dumps(value)
    readable = json.dumps(value, ensure_ascii=False)
    pretty = json.dumps(value, ensure_ascii=False, indent="\t", sort_keys=True)
    compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    assert "城市" not in escaped
    assert "\\u57ce\\u5e02" in escaped
    assert "城市" in readable
    assert '\n\t"城市"' in pretty
    assert compact == '{"城市":"深圳","items":[1,2]}'
    assert all(json.loads(text) == value for text in (escaped, readable, pretty, compact))


def test_sort_keys_makes_mapping_output_deterministic_for_comparable_keys():
    value = {"z": 1, "a": 2, "m": 3}
    assert json.dumps(value, sort_keys=True) == '{"a": 2, "m": 3, "z": 1}'
    assert json.dumps(value, indent=2).startswith('{\n  "z"')


def test_unsupported_keys_raise_or_are_silently_skipped():
    value = {("tuple",): "lost", "kept": 1}
    with pytest.raises(TypeError):
        json.dumps(value)
    assert json.loads(json.dumps(value, skipkeys=True)) == {"kept": 1}


def test_supported_nonstring_keys_do_not_round_trip_their_types():
    original = {1: "integer", None: "none", 2.5: "float"}
    # sort_keys 会先比较原 Python key；None 与数字不可排序，因此混合类型时不要顺带开启它。
    decoded = json.loads(json.dumps(original))
    assert decoded == {"1": "integer", "null": "none", "2.5": "float"}
    assert decoded != original
