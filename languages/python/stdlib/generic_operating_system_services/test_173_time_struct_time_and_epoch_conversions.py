"""173｜epoch seconds、UTC/local ``struct_time`` 与 reversible conversions。

``gmtime``/``localtime`` 把 timestamp 转成九字段 tuple-like；UTC 的逆变换是
``calendar.timegm``，local time 的逆变换才是 ``mktime``。混用两对 API 会把 timezone
offset 错算一次，是跨时区程序中很常见的陷阱。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.time.gmtime python.time.localtime
# polyglot-covers: python.time.struct-time python.time.struct-time-named-fields
# polyglot-covers: python.time.struct-time-zone python.time.struct-time-gmtoff
# polyglot-covers: python.time.mktime python.calendar.timegm
# polyglot-covers: python.time.utc-local-inverse-pairs python.time.fraction-discard
# polyglot-covers: python.time.asctime python.time.ctime
# polyglot-covers: python.time.asctime-no-newline python.time.ctime-equivalence

import calendar
import time


def test_struct_time_has_nine_sequence_fields_plus_timezone_attributes():
    """month 是 1..12、weekday Monday=0；tm_zone/tm_gmtoff 不属于九项 tuple。"""

    value = time.gmtime(0)

    assert isinstance(value, time.struct_time)
    assert len(value) == 9
    assert tuple(value[:6]) == (1970, 1, 1, 0, 0, 0)
    assert value.tm_year == value[0]
    assert value.tm_mon == value[1]
    assert value.tm_wday == 3
    assert value.tm_yday == 1
    assert value.tm_isdst == 0
    assert isinstance(value.tm_zone, str)
    assert type(value.tm_gmtoff) is int


def test_utc_and_local_conversion_pairs_round_trip_whole_seconds():
    """gmtime↔timegm、localtime↔mktime；fractional seconds 在 struct_time 中丢弃。"""

    timestamp = 1_600_000_000

    assert calendar.timegm(time.gmtime(timestamp)) == timestamp
    assert time.mktime(time.localtime(timestamp)) == timestamp
    assert time.gmtime(timestamp + 0.9).tm_sec == time.gmtime(timestamp).tm_sec


def test_asctime_has_no_trailing_newline_and_ctime_is_localtime_composition():
    """asctime/ctime 是 fixed English-like layout，不应当用作可排序交换格式。"""

    timestamp = 1_600_000_000
    local = time.localtime(timestamp)

    rendered = time.asctime(local)
    assert not rendered.endswith("\n")
    assert time.ctime(timestamp) == rendered
    assert time.ctime(timestamp) == time.asctime(time.localtime(timestamp))
