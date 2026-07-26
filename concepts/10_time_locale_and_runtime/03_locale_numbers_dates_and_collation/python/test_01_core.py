"""区域化数字、日期与排序。

共同问题：数字和日期如何按区域呈现；文本排序是否等于码点顺序；
区域设置是显式对象还是进程全局状态；缺少区域数据时如何处理。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/python/stdlib/137-137_internationalization/
# polyglot-related+: test_137_gettext_and_locale_complete_i18n_workflows.py

import datetime
import locale


def test_c_locale_formats_numbers_with_stable_ascii_conventions():
    previous = locale.setlocale(locale.LC_ALL)
    try:
        locale.setlocale(locale.LC_ALL, "C")
        assert locale.format_string("%.2f", 1234.5, grouping=True) == "1234.50"
        assert locale.localeconv()["decimal_point"] == "."
    finally:
        locale.setlocale(locale.LC_ALL, previous)


def test_locale_collation_uses_transformed_keys():
    previous = locale.setlocale(locale.LC_COLLATE)
    try:
        locale.setlocale(locale.LC_COLLATE, "C")
        assert sorted(["b", "a"], key=locale.strxfrm) == ["a", "b"]
    finally:
        locale.setlocale(locale.LC_COLLATE, previous)


def test_strftime_locale_fields_depend_on_active_process_locale():
    previous = locale.setlocale(locale.LC_TIME)
    try:
        locale.setlocale(locale.LC_TIME, "C")
        assert datetime.date(2024, 1, 1).strftime("%B") == "January"
    finally:
        locale.setlocale(locale.LC_TIME, previous)


def test_locale_is_global_state_not_an_intl_style_formatter_object():
    assert isinstance(locale.setlocale(locale.LC_NUMERIC), str)

    # Python 标准 locale 包装 C 区域设置并影响整个进程；并发代码不应频繁切换它。
