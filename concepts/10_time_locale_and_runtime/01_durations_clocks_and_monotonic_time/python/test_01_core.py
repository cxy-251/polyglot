"""时长、时钟与单调时间。

共同问题：时长与时间点如何运算；墙上时钟和单调时钟分别回答什么；
测量经过时间是否依赖真实等待或日历时间。
"""

# polyglot-family: time_locale_and_runtime
# polyglot-concept: durations_clocks_and_monotonic_time
# polyglot-related: languages/python/stdlib/077-087_generic_operating_system_services/
# polyglot-related+: test_081_time_complete_epoch_formatting_clocks_and_timezones.py

import datetime
import time


def test_timedelta_normalizes_units_and_supports_arithmetic():
    duration = datetime.timedelta(minutes=1, seconds=30)

    assert duration.total_seconds() == 90
    assert duration * 2 == datetime.timedelta(minutes=3)


def test_monotonic_clock_cannot_move_backwards_with_system_clock_adjustments():
    info = time.get_clock_info("monotonic")
    first = time.monotonic_ns()
    second = time.monotonic_ns()

    assert info.monotonic is True
    assert info.adjustable is False
    assert second >= first


def test_wall_clock_and_monotonic_clock_have_different_epochs():
    wall_seconds = time.time()
    monotonic_seconds = time.monotonic()

    assert wall_seconds > 0
    assert monotonic_seconds >= 0
    assert time.get_clock_info("time").monotonic is False

    # 两个数值不能相减得到有意义的日历差；单调时钟的参考点未定义。


def test_process_time_measures_cpu_time_instead_of_wall_time():
    info = time.get_clock_info("process_time")
    before = time.process_time_ns()
    sum(range(100))
    after = time.process_time_ns()

    assert info.monotonic is True
    assert after >= before
