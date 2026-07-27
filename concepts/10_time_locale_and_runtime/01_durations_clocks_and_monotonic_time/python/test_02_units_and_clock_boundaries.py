"""时长单位和时钟边界。

共同问题：时长是否携带单位；墙上时间回拨时经过时间如何计算；
数值精度与单位转换由调用方还是类型系统约束。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/python/stdlib/043-055_data_types/
# polyglot-related+: test_043_datetime_and_zoneinfo_complete_temporal_workflows.py
# polyglot-related: languages/python/stdlib/077-087_generic_operating_system_services/
# polyglot-related+: test_081_time_complete_epoch_formatting_clocks_and_timezones.py

import datetime

import pytest


def elapsed(start, finish):
    return finish - start


def test_timedelta_keeps_units_out_of_plain_numeric_arithmetic():
    duration = datetime.timedelta(seconds=1, milliseconds=250)

    assert duration.total_seconds() == 1.25
    assert duration / datetime.timedelta(milliseconds=250) == 5
    with pytest.raises(TypeError):
        duration + 1


def test_negative_timedelta_is_normalized_but_total_seconds_keeps_the_sign():
    duration = datetime.timedelta(microseconds=-1)

    assert duration.days == -1
    assert duration.seconds == 86_399
    assert duration.microseconds == 999_999
    assert duration.total_seconds() == -0.000001


def test_monotonic_samples_measure_progress_even_when_wall_clock_moves_back():
    wall_samples = (1_000.0, 995.0)
    monotonic_samples = (40.0, 42.5)

    assert elapsed(*wall_samples) == -5.0
    assert elapsed(*monotonic_samples) == 2.5

    # 这里注入读数而不修改系统时钟：回拨证明来自时钟语义，不依赖一次真实运行恰好发生校时。
