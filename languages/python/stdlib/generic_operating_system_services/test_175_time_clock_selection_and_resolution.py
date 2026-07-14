"""175｜wall/monotonic/performance/CPU clocks、nanosecond variants 与 clock metadata。

wall clock 可被调整，elapsed duration 应选 monotonic/perf_counter；CPU clocks 不计
waiting time。各 clock 的 reference point 都未定义，只能比较同一 clock 的差值。
整数 nanoseconds 避免长期运行后 float 无法保存底层全部精度。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.time.time python.time.time-ns
# polyglot-covers: python.time.monotonic python.time.monotonic-ns
# polyglot-covers: python.time.perf-counter python.time.perf-counter-ns
# polyglot-covers: python.time.process-time python.time.process-time-ns
# polyglot-covers: python.time.thread-time python.time.thread-time-ns
# polyglot-covers: python.time.get-clock-info python.time.clock-selection
# polyglot-covers: python.time.clock-gettime python.time.clock-gettime-ns
# polyglot-covers: python.time.clock-getres python.time.CLOCK_REALTIME
# polyglot-covers: python.time.CLOCK_MONOTONIC python.time.pthread-getcpuclockid

import threading
import time

import pytest


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
