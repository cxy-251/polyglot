"""174｜``strftime``/``strptime`` directives、defaults、strict consumption 与 `%y` pivot。

numeric directives 适合稳定案例；weekday/month names 和 `%c/%x/%X` 受 locale 影响。
``strptime`` 未给出的字段从 1900-01-01 defaults 补齐，并要求 input 全部消费；
两位年份遵循固定 69/68 pivot，不是“离当前年份最近”的猜测。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.time.strftime python.time.strftime-directives
# polyglot-covers: python.time.strptime python.time.strptime-struct-time
# polyglot-covers: python.time.strptime-default-fields python.time.strptime-full-consumption
# polyglot-covers: python.time.strptime-two-digit-year-pivot
# polyglot-covers: python.time.strptime-percent-p python.time.strptime-percent-I
# polyglot-covers: python.time.strftime-locale-dependence python.time.literal-percent

import time

import pytest


def test_strftime_numeric_directives_and_literal_percent_are_deterministic():
    """显式 struct_time 让案例不依赖当前时刻；避免断言 locale name。"""

    value = time.struct_time((2024, 2, 29, 23, 5, 7, 3, 60, -1))

    assert time.strftime("%Y-%m-%d %H:%M:%S", value) == "2024-02-29 23:05:07"
    assert time.strftime("day=%j weekday=%w %%", value) == "day=060 weekday=4 %"


def test_strptime_defaults_missing_fields_and_rejects_unconsumed_input():
    """只解析 month/day 时 year/hour 等回落到 documented default tuple。"""

    parsed = time.strptime("03-14", "%m-%d")

    assert parsed[:6] == (1900, 3, 14, 0, 0, 0)
    with pytest.raises(ValueError, match="unconverted data remains"):
        time.strptime("2024-01-02 trailing", "%Y-%m-%d")
    with pytest.raises(ValueError):
        time.strptime("2024-02-30", "%Y-%m-%d")


def test_two_digit_year_uses_posix_pivot_between_68_and_69():
    """00..68 映射 2000..2068，69..99 映射 1969..1999。"""

    assert time.strptime("68", "%y").tm_year == 2068
    assert time.strptime("69", "%y").tm_year == 1969
    assert time.strptime("00", "%y").tm_year == 2000
    assert time.strptime("99", "%y").tm_year == 1999


def test_percent_p_only_adjusts_hour_when_used_with_twelve_hour_directive():
    """`%I %p` 才表达 12-hour clock；把 `%p` 和 `%H` 混用没有转换意义。"""

    assert time.strptime("12 AM", "%I %p").tm_hour == 0
    assert time.strptime("12 PM", "%I %p").tm_hour == 12
    assert time.strptime("01 PM", "%I %p").tm_hour == 13
