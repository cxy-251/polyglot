"""413｜RFC 2822 日期解析、格式化、时区偏移与本地时区转换。

parsedate 返回兼容 time.mktime 的 9 元组，但末三项不可靠；parsedate_tz 另加相对 UTC 的秒数，
mktime_tz 将其规范化成 UTC timestamp。-0000 表示“UTC 时间但来源时区未知”，因此解析成
naive datetime；+0000/GMT 才保留 aware UTC。测试只用固定时间，不读取当前时钟。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.email.utils.parsedate
# polyglot-covers: python.email.utils.parsedate-invalid-none
# polyglot-covers: python.email.utils.parsedate_tz
# polyglot-covers: python.email.utils.parsedate-tz-offset-seconds
# polyglot-covers: python.email.utils.parsedate_to_datetime
# polyglot-covers: python.email.utils.parsedate-minus-zero-naive
# polyglot-covers: python.email.utils.parsedate-invalid-valueerror
# polyglot-covers: python.email.utils.mktime_tz
# polyglot-covers: python.email.utils.formatdate
# polyglot-covers: python.email.utils.formatdate-usegmt
# polyglot-covers: python.email.utils.format_datetime
# polyglot-covers: python.email.utils.format-datetime-naive-minus-zero
# polyglot-covers: python.email.utils.format-datetime-aware-offset
# polyglot-covers: python.email.utils.localtime
# polyglot-covers: python.email.utils.localtime-preserves-instant

from datetime import datetime, timedelta, timezone
from email.utils import (
    format_datetime,
    formatdate,
    localtime,
    mktime_tz,
    parsedate,
    parsedate_to_datetime,
    parsedate_tz,
)

import pytest


def test_parse_date_variants_expose_calendar_fields_and_timezone_seconds():
    text = "Mon, 20 Nov 1995 19:12:08 -0500"
    basic = parsedate(text)
    with_zone = parsedate_tz(text)

    assert basic[:6] == (1995, 11, 20, 19, 12, 8)
    assert with_zone[:6] == basic[:6]
    assert with_zone[9] == -5 * 60 * 60
    expected = datetime(1995, 11, 21, 0, 12, 8, tzinfo=timezone.utc).timestamp()
    assert mktime_tz(with_zone) == expected
    assert parsedate("not a date") is None


def test_datetime_parser_distinguishes_unknown_from_explicit_utc_zone():
    unknown_zone = parsedate_to_datetime("Tue, 02 Jan 2024 03:04:05 -0000")
    explicit_utc = parsedate_to_datetime("Tue, 02 Jan 2024 03:04:05 +0000")

    assert unknown_zone.tzinfo is None
    assert explicit_utc.tzinfo == timezone.utc
    with pytest.raises(ValueError):
        parsedate_to_datetime("Tue, 02 Jan 2024 25:04:05 +0000")


def test_fixed_timestamps_and_datetimes_format_without_reading_current_time():
    assert formatdate(1_000_000_000, usegmt=True) == (
        "Sun, 09 Sep 2001 01:46:40 GMT"
    )
    assert formatdate(1_000_000_000).endswith("-0000")

    naive = datetime(2024, 1, 2, 3, 4, 5)
    east_eight = naive.replace(tzinfo=timezone(timedelta(hours=8)))
    utc = naive.replace(tzinfo=timezone.utc)
    assert format_datetime(naive).endswith("-0000")
    assert format_datetime(east_eight).endswith("+0800")
    assert format_datetime(utc, usegmt=True).endswith("GMT")


def test_localtime_converts_zone_but_preserves_the_instant():
    instant = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    converted = localtime(instant)

    assert converted.tzinfo is not None
    assert converted.timestamp() == instant.timestamp()
