"""时区跳变和日历算术边界。

共同问题：重复或不存在的本地时间如何映射到时间线；
日历字段运算与固定时长运算在时区跳变处是否等价。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: calendar_time_zones_and_arithmetic
# polyglot-related: languages/python/stdlib/043-055_data_types/
# polyglot-related+: test_043_datetime_and_zoneinfo_complete_temporal_workflows.py

import datetime
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")
UTC = datetime.timezone.utc


def test_nonexistent_wall_time_is_constructible_but_does_not_round_trip():
    missing = datetime.datetime(2021, 3, 14, 2, 30, tzinfo=NEW_YORK)
    round_trip = missing.astimezone(UTC).astimezone(NEW_YORK)

    assert missing.hour == 2
    assert round_trip.hour == 3
    assert round_trip.minute == 30

    # zoneinfo 不替构造器拒绝本地时间间隙；需要业务层通过往返或其他策略验证输入。


def test_wall_calendar_day_and_timeline_day_diverge_across_fall_back():
    start = datetime.datetime(2021, 11, 6, 12, tzinfo=NEW_YORK)
    wall_next_day = start + datetime.timedelta(days=1)
    timeline_next_day = (start.astimezone(UTC) + datetime.timedelta(days=1)).astimezone(NEW_YORK)

    assert wall_next_day.hour == 12
    assert wall_next_day.timestamp() - start.timestamp() == 25 * 60 * 60
    assert timeline_next_day.hour == 11
    assert timeline_next_day.timestamp() - start.timestamp() == 24 * 60 * 60
