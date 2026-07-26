"""空值、缺失状态与可选值。

共同问题：语言有几种空状态；缺失成员如何区分；默认值是否会吞掉有效假值；
读取空状态时在何处失败。
"""

# polyglot-family: values_and_comparison
# polyglot-concept: null_missing_and_optional_values
# polyglot-related: languages/python/language/test_001_truth_value_testing.py
# polyglot-related: languages/python/builtins/test_024_mapping_dict.py

import pytest


def test_none_is_one_runtime_value_not_a_missing_binding():
    value = None

    assert value is None
    assert "value" in locals()
    with pytest.raises(NameError):
        eval("missing_name")


def test_mapping_membership_distinguishes_missing_from_present_none():
    settings = {"timeout": None}

    assert settings.get("timeout") is None
    assert settings.get("missing") is None
    assert "timeout" in settings
    assert "missing" not in settings


def test_unique_sentinel_preserves_all_user_values():
    missing = object()
    payload = {"count": 0}

    assert payload.get("count", missing) == 0
    assert payload.get("label", missing) is missing


def test_none_check_does_not_replace_valid_falsy_values():
    def default_only_none(value, fallback):
        return fallback if value is None else value

    assert default_only_none(0, 10) == 0
    assert default_only_none("", "fallback") == ""
    assert (0 or 10) == 10

    # JavaScript 的 nullish 合并有专用运算符；Python 应显式用 `is None` 表达同一意图。

