"""081｜epoch seconds、UTC/local ``struct_time`` 与 reversible conversions。

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
import pytest
import threading
import os

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


# ``strftime``/``strptime`` directives、defaults、strict consumption 与 `%y` pivot。
#
# numeric directives 适合稳定案例；weekday/month names 和 `%c/%x/%X` 受 locale 影响。
# ``strptime`` 未给出的字段从 1900-01-01 defaults 补齐，并要求 input 全部消费；
# 两位年份遵循固定 69/68 pivot，不是“离当前年份最近”的猜测。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.time.strftime python.time.strftime-directives
# polyglot-covers: python.time.strptime python.time.strptime-struct-time
# polyglot-covers: python.time.strptime-default-fields python.time.strptime-full-consumption
# polyglot-covers: python.time.strptime-two-digit-year-pivot
# polyglot-covers: python.time.strptime-percent-p python.time.strptime-percent-I
# polyglot-covers: python.time.strftime-locale-dependence python.time.literal-percent




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


# wall/monotonic/performance/CPU clocks、nanosecond variants 与 clock metadata。
#
# wall clock 可被调整，elapsed duration 应选 monotonic/perf_counter；CPU clocks 不计
# waiting time。各 clock 的 reference point 都未定义，只能比较同一 clock 的差值。
# 整数 nanoseconds 避免长期运行后 float 无法保存底层全部精度。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.time.time python.time.time-ns
# polyglot-covers: python.time.monotonic python.time.monotonic-ns
# polyglot-covers: python.time.perf-counter python.time.perf-counter-ns
# polyglot-covers: python.time.process-time python.time.process-time-ns
# polyglot-covers: python.time.thread-time python.time.thread-time-ns
# polyglot-covers: python.time.get-clock-info python.time.clock-selection
# polyglot-covers: python.time.clock-gettime python.time.clock-gettime-ns
# polyglot-covers: python.time.clock-getres python.time.CLOCK_REALTIME
# polyglot-covers: python.time.CLOCK_MONOTONIC python.time.pthread-getcpuclockid




def test_standard_clock_families_expose_float_and_integer_variants():
    """不跨 clock 比绝对值，也不要求两个相邻调用一定发生可观察增长。"""

    assert type(time.time()) is float
    assert type(time.time_ns()) is int
    assert type(time.monotonic()) is float
    assert type(time.monotonic_ns()) is int
    assert type(time.perf_counter()) is float
    assert type(time.perf_counter_ns()) is int
    assert type(time.process_time()) is float
    assert type(time.process_time_ns()) is int

    if hasattr(time, "thread_time"):
        assert type(time.thread_time()) is float
        assert type(time.thread_time_ns()) is int


def test_get_clock_info_explains_semantics_instead_of_exposing_epoch():
    """resolution 是 capability，不是保证每次 read 都至少增加该值。"""

    infos = {
        name: time.get_clock_info(name)
        for name in ("time", "monotonic", "perf_counter", "process_time")
    }

    assert infos["time"].adjustable is True or infos["time"].adjustable is False
    assert infos["monotonic"].monotonic is True
    assert infos["perf_counter"].monotonic is True
    assert infos["process_time"].monotonic is True
    assert all(info.resolution > 0 for info in infos.values())
    assert all(info.implementation for info in infos.values())


@pytest.mark.skipif(
    not all(
        hasattr(time, name)
        for name in ("clock_gettime", "clock_gettime_ns", "clock_getres")
    ),
    reason="平台不提供 POSIX clock APIs",
)
def test_posix_clock_id_queries_preserve_float_vs_nanosecond_types():
    """CLOCK_REALTIME 对应 wall clock；CLOCK_MONOTONIC 只用于 duration。"""

    realtime = time.clock_gettime(time.CLOCK_REALTIME)
    realtime_ns = time.clock_gettime_ns(time.CLOCK_REALTIME)
    monotonic = time.clock_gettime(time.CLOCK_MONOTONIC)

    assert type(realtime) is float
    assert type(realtime_ns) is int
    assert type(monotonic) is float
    assert time.clock_getres(time.CLOCK_REALTIME) > 0
    assert time.clock_getres(time.CLOCK_MONOTONIC) > 0


@pytest.mark.skipif(
    not hasattr(time, "pthread_getcpuclockid"),
    reason="平台不提供 per-thread POSIX clock id",
)
def test_current_thread_cpu_clock_id_can_be_read_safely():
    """只传 current thread ident；expired/invalid id 可能是 undefined behavior。"""

    clock_id = time.pthread_getcpuclockid(threading.get_ident())

    assert type(clock_id) is int
    assert time.clock_gettime(clock_id) >= 0
    assert time.clock_getres(clock_id) > 0


# process-global timezone constants、``TZ``/``tzset`` 与 UTC normalization。
#
# localtime/mktime 依赖 process-global timezone rules；仅修改 ``TZ`` 后必须调用
# ``tzset`` 才可移植。测试暂时切到无 DST 的 ``UTC0`` 并在 finally 恢复，避免污染
# pytest process。应用处理历史时区规则时应优先使用 ``zoneinfo``。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.time.tzset python.time.TZ-environment
# polyglot-covers: python.time.timezone python.time.altzone
# polyglot-covers: python.time.daylight python.time.tzname
# polyglot-covers: python.time.timezone-process-global python.time.timezone-state-restore
# polyglot-covers: python.time.localtime-utc0 python.time.mktime-local-rules




def test_timezone_constants_have_platform_defined_structural_types():
    """timezone/altzone 是 UTC 以西秒数；不要误当作 east-positive UTC offset。"""

    assert type(time.timezone) is int
    assert type(time.altzone) is int
    assert type(time.daylight) is int
    assert len(time.tzname) == 2
    assert all(isinstance(name, str) for name in time.tzname)


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="平台不提供 TZ/tzset")
def test_tzset_applies_utc0_and_state_is_restored_after_case(monkeypatch):
    """UTC0 中 local/UTC conversion 一致；finally 同步恢复 C library timezone state。"""

    original = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "UTC0")
    try:
        time.tzset()

        assert time.timezone == 0
        assert time.daylight == 0
        assert time.localtime(0)[:8] == time.gmtime(0)[:8]
        assert time.mktime(time.localtime(1_600_000_000)) == 1_600_000_000
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()
