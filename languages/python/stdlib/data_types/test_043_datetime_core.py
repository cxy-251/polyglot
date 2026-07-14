"""043｜``datetime`` 日期、时刻、duration 与固定偏移时区示例。

``datetime`` 同时包含两种不同抽象：``date`` / ``time`` 表示日历或墙上时间字段，
aware ``datetime`` 才能在偏移已知时表示确定时刻。naive 对象的含义完全由应用约定，
库不会自动知道它是 UTC、本地时间还是业务时间。

本文件只使用 UTC 和固定偏移 ``timezone``，不读取主机本地时区。IANA 地区规则、DST
gap/fold 的真实转换将在后续 ``zoneinfo`` 文件处理。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.stdlib.datetime python.datetime.constants
# polyglot-covers: python.datetime.timedelta python.datetime.timedelta-normalization
# polyglot-covers: python.datetime.timedelta-arithmetic python.datetime.total_seconds
# polyglot-covers: python.datetime.date python.datetime.date-arithmetic
# polyglot-covers: python.datetime.ordinal python.datetime.iso-calendar
# polyglot-covers: python.datetime.time python.datetime.fold
# polyglot-covers: python.datetime.datetime python.datetime.combine-decompose
# polyglot-covers: python.datetime.naive-aware python.datetime.tzinfo-awareness
# polyglot-covers: python.datetime.timezone python.datetime.fixed-offset
# polyglot-covers: python.datetime.astimezone python.datetime.replace-tzinfo
# polyglot-covers: python.datetime.timestamp python.datetime.fromtimestamp
# polyglot-covers: python.datetime.isoformat python.datetime.fromisoformat
# polyglot-covers: python.datetime.strftime python.datetime.strptime
# polyglot-covers: python.datetime.error-boundaries

from datetime import MAXYEAR
from datetime import MINYEAR
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from datetime import timezone
from datetime import tzinfo

import pytest


def test_type_limits_resolution_immutability_and_hashability():
    """核心类型不可变且可哈希；不同类型的最小分辨率并不相同。"""

    assert (MINYEAR, MAXYEAR) == (1, 9999)
    assert date.min == date(1, 1, 1)
    assert date.max == date(9999, 12, 31)
    assert time.min == time(0, 0)
    assert time.max == time(23, 59, 59, 999_999)
    assert datetime.min == datetime(1, 1, 1)
    assert datetime.max == datetime(9999, 12, 31, 23, 59, 59, 999_999)
    assert timedelta.min == timedelta(days=-999_999_999)
    assert timedelta.max == timedelta(
        days=999_999_999,
        hours=23,
        minutes=59,
        seconds=59,
        microseconds=999_999,
    )
    assert date.resolution == timedelta(days=1)
    assert datetime.resolution == timedelta(microseconds=1)
    assert time.resolution == timedelta(microseconds=1)
    assert timedelta.resolution == timedelta(microseconds=1)

    day = date(2024, 2, 29)
    lookup = {day: "leap-day"}
    assert lookup[date(2024, 2, 29)] == "leap-day"

    with pytest.raises(AttributeError):
        day.year = 2025


def test_timedelta_constructor_normalizes_all_units_into_three_attributes():
    """内部只存 days、seconds、microseconds；其余单位先合并再规范化。"""

    duration = timedelta(
        weeks=1,
        days=2,
        hours=25,
        minutes=61,
        seconds=61,
        milliseconds=1,
        microseconds=2,
    )

    assert duration.days == 10
    assert duration.seconds == 7_321
    assert duration.microseconds == 1_002
    assert duration == timedelta(days=10, seconds=7_321, microseconds=1_002)


def test_negative_timedelta_representation_is_normalized_not_sign_per_field():
    """负一微秒借用前一天表示；``seconds`` 因而绝不是 duration 的总秒数。"""

    duration = timedelta(microseconds=-1)

    assert (duration.days, duration.seconds, duration.microseconds) == (
        -1,
        86_399,
        999_999,
    )
    assert duration.total_seconds() == pytest.approx(-0.000_001)
    assert duration.seconds == 86_399
    assert str(timedelta(hours=-5)) == "-1 day, 19:00:00"
    assert not timedelta(0)
    assert timedelta(microseconds=1)


def test_timedelta_supports_duration_arithmetic_quotients_and_remainders():
    """除以 duration 得比例，整除/取模/divmod 可把总时长拆成固定间隔。"""

    duration = timedelta(hours=5, minutes=40)
    unit = timedelta(hours=1)

    assert duration + timedelta(minutes=20) == timedelta(hours=6)
    assert duration - timedelta(minutes=40) == timedelta(hours=5)
    assert duration * 2 == timedelta(hours=11, minutes=20)
    assert duration / 2 == timedelta(hours=2, minutes=50)
    assert duration / timedelta(minutes=20) == 17.0
    assert duration // unit == 5
    assert duration % unit == timedelta(minutes=40)
    assert divmod(duration, unit) == (5, timedelta(minutes=40))
    assert abs(-duration) == duration


def test_timedelta_float_rounding_uses_microseconds_and_half_even_ties():
    """浮点乘除最终舍入到一微秒；恰好半单位使用 round-half-to-even。"""

    one_microsecond = timedelta(microseconds=1)
    three_microseconds = timedelta(microseconds=3)

    assert one_microsecond * 0.5 == timedelta(0)
    assert three_microseconds * 0.5 == timedelta(microseconds=2)
    assert timedelta(microseconds=3) / 2 == timedelta(microseconds=2)


def test_timedelta_overflow_and_zero_division_are_not_silently_saturated():
    """超出可表示范围直接失败；``-timedelta.max`` 本身也无法表示。"""

    with pytest.raises(OverflowError):
        -timedelta.max
    with pytest.raises(OverflowError):
        timedelta.max + timedelta.resolution
    with pytest.raises(ZeroDivisionError):
        timedelta(days=1) / 0
    with pytest.raises(ZeroDivisionError):
        timedelta(days=1) // timedelta(0)


def test_date_validates_calendar_ranges_and_leap_years():
    """date 使用向前后无限延伸的 Gregorian calendar，但年份限制在 1..9999。"""

    leap_day = date(2024, 2, 29)
    assert (leap_day.year, leap_day.month, leap_day.day) == (2024, 2, 29)

    with pytest.raises(ValueError):
        date(2023, 2, 29)
    with pytest.raises(ValueError):
        date(2024, 13, 1)
    with pytest.raises(ValueError):
        date(0, 1, 1)


def test_date_ordinal_and_iso_text_round_trip_without_platform_timezones():
    """ordinal 与 YYYY-MM-DD 都是纯日历转换，不经过系统 localtime。"""

    day = date(2024, 2, 29)

    assert date.fromordinal(day.toordinal()) == day
    assert date.fromisoformat(day.isoformat()) == day
    assert str(day) == "2024-02-29"

    # Python 3.10 的 date.fromisoformat 只接受 YYYY-MM-DD，不接受 ISO week date。
    with pytest.raises(ValueError):
        date.fromisoformat("2024-W09-4")


def test_iso_calendar_year_can_differ_from_gregorian_year_near_boundaries():
    """ISO week 以周一开始，第一周包含该 ISO 年的首个周四。"""

    monday = date(2003, 12, 29)
    iso = monday.isocalendar()

    assert (iso.year, iso.week, iso.weekday) == (2004, 1, 1)
    assert monday.weekday() == 0
    assert monday.isoweekday() == 1
    assert date.fromisocalendar(2004, 1, 1) == monday

    new_years_day = date(2021, 1, 1)
    assert new_years_day.isocalendar() == (2020, 53, 5)


def test_date_replace_and_timetuple_return_new_views_of_the_same_day():
    """replace 不修改原对象；timetuple 提供 weekday、year-day 和未知 DST 标志。"""

    original = date(2024, 2, 29)
    changed = original.replace(year=2023, day=28)
    fields = original.timetuple()

    assert original == date(2024, 2, 29)
    assert changed == date(2023, 2, 28)
    assert fields[:6] == (2024, 2, 29, 0, 0, 0)
    assert fields.tm_wday == original.weekday()
    assert fields.tm_yday == 60
    assert fields.tm_isdst == -1


def test_date_arithmetic_uses_only_the_normalized_days_component():
    """date 没有时分秒；加 timedelta 时 seconds/microseconds 会被忽略。"""

    day = date(2024, 1, 2)

    assert day + timedelta(hours=23) == day
    assert day + timedelta(hours=47) == date(2024, 1, 3)

    # -1 hour 规范化为 days=-1, seconds=23h，所以 date 会向前一天。
    negative_hour = timedelta(hours=-1)
    assert (negative_hour.days, negative_hour.seconds) == (-1, 82_800)
    assert day + negative_hour == date(2024, 1, 1)
    assert date(2024, 1, 10) - date(2024, 1, 2) == timedelta(days=8)


def test_time_fields_fold_replace_and_isoformat_are_pure_wall_time_operations():
    """time 不带日期；fold 只保存歧义选择，真正的 DST 解释由时区规则完成。"""

    fixed_offset = timezone(timedelta(hours=5, minutes=30), "IST")
    wall_time = time(
        23,
        59,
        58,
        123_456,
        tzinfo=fixed_offset,
        fold=1,
    )

    assert wall_time.isoformat(timespec="microseconds") == "23:59:58.123456+05:30"
    assert wall_time.fold == 1
    assert wall_time.utcoffset() == timedelta(hours=5, minutes=30)
    assert wall_time.tzname() == "IST"
    assert wall_time.replace(second=0, microsecond=0, fold=0) == time(
        23,
        59,
        tzinfo=fixed_offset,
    )

    with pytest.raises(TypeError):
        wall_time + timedelta(seconds=2)


def test_time_comparison_rejects_naive_aware_mixing_but_normalizes_offsets():
    """aware time 可按 UTC 偏移比较；naive time 没有足够信息与它排序。"""

    naive = time(12, 0)
    aware = time(12, 0, tzinfo=timezone.utc)

    assert naive != aware
    with pytest.raises(TypeError):
        naive < aware

    plus_two = timezone(timedelta(hours=2))
    assert time(12, 0, tzinfo=plus_two) == time(10, 0, tzinfo=timezone.utc)


def test_datetime_combine_and_decompose_distinguish_time_from_timetz():
    """time() 去掉 tzinfo，timetz() 保留；两者都保留 fold。"""

    day = date(2024, 10, 27)
    wall_time = time(1, 30, fold=1, tzinfo=timezone.utc)
    combined = datetime.combine(day, wall_time)

    assert combined == datetime(2024, 10, 27, 1, 30, fold=1, tzinfo=timezone.utc)
    assert combined.date() == day
    assert combined.time() == time(1, 30, fold=1)
    assert combined.time().tzinfo is None
    assert combined.timetz() == wall_time


def test_datetime_timedelta_arithmetic_uses_all_duration_components():
    """datetime 与 date 不同，会使用 days、seconds、microseconds 完整推进时钟。"""

    start = datetime(2024, 2, 29, 23, 59, 59, 900_000, tzinfo=timezone.utc)
    end = start + timedelta(microseconds=200_000)

    assert end == datetime(2024, 3, 1, 0, 0, 0, 100_000, tzinfo=timezone.utc)
    assert end - start == timedelta(microseconds=200_000)
    assert end.tzinfo is start.tzinfo
    assert start - timedelta(days=1) == datetime(
        2024,
        2,
        28,
        23,
        59,
        59,
        900_000,
        tzinfo=timezone.utc,
    )


def test_awareness_requires_a_non_none_offset_not_only_a_tzinfo_object():
    """tzinfo 存在只是第一条件；utcoffset(dt) 返回 None 时 datetime 仍属 naive。"""

    class LabelOnlyTimezone(tzinfo):
        def utcoffset(self, value):
            return None

        def dst(self, value):
            return None

        def tzname(self, value):
            return "business-wall-time"

    labeled = datetime(2024, 1, 1, 9, tzinfo=LabelOnlyTimezone())

    assert labeled.tzinfo is not None
    assert labeled.utcoffset() is None
    assert labeled.tzname() == "business-wall-time"
    assert labeled == datetime(2024, 1, 1, 9)


def test_naive_and_aware_datetimes_neither_compare_nor_subtract_as_instants():
    """相同墙上字段不代表相同时刻；相等返回 False，排序与相减直接拒绝。"""

    naive = datetime(2024, 1, 1, 12)
    aware = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)

    assert naive != aware
    with pytest.raises(TypeError):
        naive < aware
    with pytest.raises(TypeError):
        aware - naive


def test_fixed_offset_timezone_supplies_offset_name_and_no_dst_rules():
    """timezone 只表示固定 offset；它不会因日期变化应用地区 DST 历史。"""

    india = timezone(timedelta(hours=5, minutes=30), "IST")
    instant = datetime(2024, 7, 1, 12, tzinfo=india)

    assert instant.utcoffset() == timedelta(hours=5, minutes=30)
    assert instant.tzname() == "IST"
    assert instant.dst() is None
    assert timezone.utc.utcoffset(None) == timedelta(0)
    assert str(timezone.utc) == "UTC"

    with pytest.raises(ValueError):
        timezone(timedelta(hours=24))
    with pytest.raises(ValueError):
        timezone(timedelta(hours=-24))


def test_astimezone_converts_an_instant_while_replace_only_changes_its_label():
    """astimezone 保持 UTC 时刻；replace(tzinfo=...) 不调整墙上字段。"""

    utc_noon = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    plus_eight = timezone(timedelta(hours=8))

    converted = utc_noon.astimezone(plus_eight)
    relabeled = utc_noon.replace(tzinfo=plus_eight)

    assert converted == datetime(2024, 1, 1, 20, tzinfo=plus_eight)
    assert converted.timestamp() == utc_noon.timestamp()

    assert relabeled == datetime(2024, 1, 1, 12, tzinfo=plus_eight)
    assert relabeled.astimezone(timezone.utc) == datetime(
        2024,
        1,
        1,
        4,
        tzinfo=timezone.utc,
    )
    assert relabeled.timestamp() != utc_noon.timestamp()


def test_aware_datetimes_with_different_offsets_compare_as_utc_instants():
    """两个 aware 对象 tzinfo 不同时，比较与相减会先归一到 UTC。"""

    utc_value = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
    plus_eight_value = datetime(
        2024,
        1,
        1,
        20,
        tzinfo=timezone(timedelta(hours=8)),
    )

    assert utc_value == plus_eight_value
    assert utc_value - plus_eight_value == timedelta(0)
    assert hash(utc_value) == hash(plus_eight_value)


def test_timestamp_round_trip_is_stable_when_timezone_is_explicit():
    """显式传 UTC 避免 fromtimestamp 使用主机 localtime；POSIX epoch 可稳定断言。"""

    epoch = datetime.fromtimestamp(0, tz=timezone.utc)

    assert epoch == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert epoch.timestamp() == 0.0
    assert datetime.fromtimestamp(epoch.timestamp(), timezone.utc) == epoch

    naive_utc = datetime.utcfromtimestamp(0)
    assert naive_utc == datetime(1970, 1, 1)
    assert naive_utc.tzinfo is None


def test_current_utc_constructors_differ_in_awareness_not_claimed_exact_time():
    """只验证返回形状；真实时钟可能在两次调用之间前进，不能断言字段完全相等。"""

    naive_utc = datetime.utcnow()
    aware_utc = datetime.now(timezone.utc)

    assert naive_utc.tzinfo is None
    assert aware_utc.tzinfo is timezone.utc
    assert MINYEAR <= naive_utc.year <= MAXYEAR
    assert MINYEAR <= aware_utc.year <= MAXYEAR


def test_datetime_isoformat_round_trip_preserves_fixed_offset_and_precision():
    """Python 3.10 fromisoformat 是 isoformat 的逆操作，不是任意 ISO 8601 parser。"""

    fixed_offset = timezone(timedelta(hours=5, minutes=30))
    value = datetime(
        2024,
        2,
        29,
        12,
        34,
        56,
        123_456,
        tzinfo=fixed_offset,
    )

    assert value.isoformat() == "2024-02-29T12:34:56.123456+05:30"
    assert value.isoformat(" ", timespec="milliseconds") == (
        "2024-02-29 12:34:56.123+05:30"
    )
    assert datetime.fromisoformat(value.isoformat()) == value
    assert datetime.fromisoformat("2024-02-29 12:34:56+05:30") == value.replace(
        microsecond=0,
    )

    # 结尾 Z 的支持在更新版本扩展；锁定的 3.10 格式要求显式 +00:00。
    with pytest.raises(ValueError):
        datetime.fromisoformat("2024-02-29T12:34:56Z")


def test_strftime_and_strptime_share_documented_common_directives():
    """格式串是显式协议；%f 保留微秒，%z 可重建 fixed-offset aware datetime。"""

    value = datetime(
        2024,
        2,
        29,
        12,
        34,
        56,
        123_456,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )
    format_string = "%Y-%m-%d %H:%M:%S.%f %z"
    rendered = value.strftime(format_string)

    assert rendered == "2024-02-29 12:34:56.123456 +0530"
    assert datetime.strptime(rendered, format_string) == value


def test_strptime_missing_fields_use_1900_defaults_in_python_310():
    """只解析月日时年份默认为 1900；这会让没有年份的 2 月 29 日无法解析。"""

    assert datetime.strptime("03-14", "%m-%d") == datetime(1900, 3, 14)

    with pytest.raises(ValueError):
        datetime.strptime("02-29", "%m-%d")

    assert datetime.strptime("2024-02-29", "%Y-%m-%d") == datetime(2024, 2, 29)


def test_invalid_time_fields_and_leap_seconds_fail_at_construction():
    """datetime 假定每天恰好 86400 秒，不表示 leap second，也不自动进位坏字段。"""

    with pytest.raises(ValueError):
        time(24, 0)
    with pytest.raises(ValueError):
        datetime(2024, 1, 1, 23, 60)
    with pytest.raises(ValueError):
        datetime(2024, 1, 1, 23, 59, 60)
    with pytest.raises(ValueError):
        datetime.fromisoformat("not-a-datetime")
