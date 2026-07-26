"""映射查找与缺失键。

共同问题：缺失查找返回值还是错误；读取是否可能插入；如何区分缺失与空值；
自定义映射能否提供默认策略。
"""

# polyglot-family: collections_and_iteration
# polyglot-concept: mapping_lookup_and_missing_keys
# polyglot-related: languages/python/builtins/test_024_mapping_dict.py

from collections import defaultdict

import pytest


def test_subscript_raises_while_get_returns_a_default():
    mapping = {"answer": 42}

    assert mapping["answer"] == 42
    assert mapping.get("missing") is None
    assert mapping.get("missing", 0) == 0

    with pytest.raises(KeyError):
        _ = mapping["missing"]


def test_membership_distinguishes_missing_from_present_none():
    mapping = {"value": None}

    assert mapping.get("value") is None
    assert mapping.get("missing") is None
    assert "value" in mapping
    assert "missing" not in mapping


def test_setdefault_and_defaultdict_insert_on_missing_access():
    mapping = {}
    values = mapping.setdefault("items", [])
    values.append(1)

    grouped = defaultdict(list)
    grouped["items"].append(2)

    assert mapping == {"items": [1]}
    assert grouped == {"items": [2]}


def test_missing_protocol_can_compute_a_value_without_inserting():
    class Labels(dict):
        def __missing__(self, key):
            return f"<{key}>"

    labels = Labels()

    assert labels["unknown"] == "<unknown>"
    assert "unknown" not in labels
