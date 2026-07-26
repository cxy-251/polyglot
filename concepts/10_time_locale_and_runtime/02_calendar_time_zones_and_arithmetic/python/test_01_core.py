"""日历、时区与算术。

共同问题：日历字段如何映射到时间线；时区偏移如何参与表示；无效日期和夏令时跳变如何表达；
按时间线增加时长是否等于按墙上日历修改字段。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/python/stdlib/043-055_data_types/
# polyglot-related+: test_043_datetime_and_zoneinfo_complete_temporal_workflows.py

import datetime
from zoneinfo import ZoneInfo

import pytest


def test_aware_datetime_maps_local_fields_to_utc_instant():
    local = datetime.datetime(
        2024,
        1,
        1,
        8,
        tzinfo=datetime.timezone(datetime.timedelta(hours=8)),
    )

    assert local.astimezone(datetime.timezone.utc).hour == 0
    assert local.utcoffset() == datetime.timedelta(hours=8)


def test_invalid_calendar_date_is_rejected():
    with pytest.raises(ValueError):
        datetime.date(2023, 2, 29)

    assert datetime.date(2024, 2, 29) + datetime.timedelta(days=1) == datetime.date(2024, 3, 1)


def test_fold_distinguishes_repeated_wall_times():
    zone = ZoneInfo("America/New_York")
    first = datetime.datetime(2021, 11, 7, 1, 30, tzinfo=zone, fold=0)
    second = first.replace(fold=1)

    assert first.utcoffset() == datetime.timedelta(hours=-4)
    assert second.utcoffset() == datetime.timedelta(hours=-5)
    assert first.timestamp() != second.timestamp()


def test_timeline_arithmetic_can_skip_a_local_clock_hour():
    zone = ZoneInfo("America/New_York")
    before = datetime.datetime(2021, 3, 14, 6, 30, tzinfo=datetime.timezone.utc)
    after = before + datetime.timedelta(hours=1)

    assert before.astimezone(zone).hour == 1
    assert after.astimezone(zone).hour == 3
