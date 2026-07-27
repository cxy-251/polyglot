"""区域可用性和状态边界。

共同问题：区域数据缺失时如何失败；排序是否等于代码点顺序；
区域配置属于显式对象还是可泄漏到其他代码的进程状态。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/python/stdlib/137-137_internationalization/
# polyglot-related+: test_137_gettext_and_locale_complete_i18n_workflows.py

import locale

import pytest


def test_missing_named_locale_fails_without_changing_the_current_setting():
    previous = locale.setlocale(locale.LC_NUMERIC)

    with pytest.raises(locale.Error):
        locale.setlocale(locale.LC_NUMERIC, "polyglot_LOCALE_that_does_not_exist")

    assert locale.setlocale(locale.LC_NUMERIC) == previous


def test_locale_formatting_reads_process_state_while_format_has_explicit_rules():
    previous = locale.setlocale(locale.LC_NUMERIC)
    try:
        locale.setlocale(locale.LC_NUMERIC, "C")

        assert locale.format_string("%.1f", 1234.5, grouping=True) == "1234.5"
        assert format(1234.5, ",.1f") == "1,234.5"
    finally:
        locale.setlocale(locale.LC_NUMERIC, previous)


def test_c_locale_collation_matches_bytewise_order_only_for_this_locale():
    previous = locale.setlocale(locale.LC_COLLATE)
    try:
        locale.setlocale(locale.LC_COLLATE, "C")
        values = ["z", "ä"]

        assert sorted(values, key=locale.strxfrm) == sorted(values)
    finally:
        locale.setlocale(locale.LC_COLLATE, previous)

    # 这个结果来自显式 C locale；不能推广为自然语言排序规则。
