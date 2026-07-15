"""149｜profile、cProfile、pstats 与 timeit：诊断调用成本和微基准。

确定性 profiler 用于回答“时间花在哪些调用上”，``timeit`` 用于尽量
隔离地重复测量小片段。案例验证统计结构、排序/合并和计时器协议，
不把当前机器上的绝对秒数或某次最快结果写成脆弱断言。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.profile python.stdlib.cprofile
# polyglot-covers: python.profile.deterministic-profiling-overhead-boundary
# polyglot-covers: python.cprofile.profile python.cprofile.runcall
# polyglot-covers: python.cprofile.enable-disable python.cprofile.getstats
# polyglot-covers: python.cprofile.runctx python.cprofile.dump-stats
# polyglot-covers: python.profile.profile-pure-python
# polyglot-covers: python.profile.recursive-total-and-primitive-calls
# polyglot-covers: python.stdlib.pstats python.pstats.stats
# polyglot-covers: python.pstats.stats-tuple python.pstats.sort-key
# polyglot-covers: python.pstats.strip-dirs python.pstats.print-stats
# polyglot-covers: python.pstats.print-callers python.pstats.print-callees
# polyglot-covers: python.pstats.stats-profile python.pstats.function-profile
# polyglot-covers: python.pstats.dump-load-add python.pstats.format-compatibility
# polyglot-covers: python.stdlib.timeit python.timeit.timer
# polyglot-covers: python.timeit.string-statement-globals
# polyglot-covers: python.timeit.callable-statement-and-setup
# polyglot-covers: python.timeit.setup-excluded python.timeit.custom-timer
# polyglot-covers: python.timeit.timeit python.timeit.repeat
# polyglot-covers: python.timeit.autorange python.timeit.autorange-callback
# polyglot-covers: python.timeit.gc-temporarily-disabled
# polyglot-covers: python.timeit.default-timer python.timeit.perf-counter
# polyglot-covers: python.timeit.minimum-not-average-guidance
# polyglot-covers: python.timeit.invalid-statement-boundary

import cProfile
import gc
from io import StringIO
from pathlib import Path
import profile
import pstats
import time
import timeit

import pytest


def profile_leaf(limit):
    return sum(value * value for value in range(limit))


def profile_recursive(depth):
    if depth <= 0:
        return 1
    return depth * profile_recursive(depth - 1)


def profile_workload(limit):
    return profile_leaf(limit) + profile_recursive(limit)


def function_statistic(stats, function):
    matches = [
        (key, values)
        for key, values in stats.stats.items()
        if key[0] == function.__code__.co_filename
        and key[1] == function.__code__.co_firstlineno
        and key[2] == function.__name__
    ]
    assert len(matches) == 1
    return matches[0]


def timer_for_durations(*durations):
    """生成每次前后读数差固定的 timer，避免测试依赖真实 wall clock。"""

    readings = []
    baseline = 0.0
    for duration in durations:
        readings.extend([baseline, baseline + duration])
        baseline += duration + 1.0
    iterator = iter(readings)
    return lambda: next(iterator)


def test_cprofile_runcall_returns_value_and_records_stats_tuple_semantics():
    profiler = cProfile.Profile()
    result = profiler.runcall(profile_workload, 4)
    statistics = pstats.Stats(profiler)

    assert result == profile_leaf(4) + 24
    key, values = function_statistic(statistics, profile_workload)
    primitive_calls, total_calls, total_time, cumulative_time, callers = values

    assert key[2] == "profile_workload"
    assert primitive_calls == 1
    assert total_calls == 1
    assert total_time >= 0
    assert cumulative_time >= total_time
    assert isinstance(callers, dict)

    # profiler 自身会增加开销，尤其 Python call 事件比 C-level 调用更明显；
    # 统计用于定位瓶颈，不应拿来做 Python 与 C 实现之间的公平 benchmark。


def test_recursive_stats_distinguish_total_calls_from_primitive_calls():
    profiler = cProfile.Profile()
    assert profiler.runcall(profile_recursive, 4) == 24
    statistics = pstats.Stats(profiler)

    _, values = function_statistic(statistics, profile_recursive)
    primitive_calls, total_calls = values[:2]
    assert primitive_calls == 1
    assert total_calls == 5
    assert total_calls > primitive_calls


def test_cprofile_enable_disable_and_getstats_expose_raw_entries():
    profiler = cProfile.Profile()

    profiler.enable()
    try:
        value = profile_leaf(5)
    finally:
        profiler.disable()

    assert value == 30
    entries = profiler.getstats()
    leaf = next(entry for entry in entries if entry.code is profile_leaf.__code__)
    assert leaf.callcount == 1
    assert leaf.reccallcount == 0
    assert leaf.inlinetime >= 0
    assert leaf.totaltime >= leaf.inlinetime
    assert isinstance(leaf.calls, (list, type(None)))


def test_cprofile_runctx_writes_reloadable_stats_and_updates_locals(tmp_path):
    output = tmp_path / "workload.prof"
    local_namespace = {"limit": 3}

    cProfile.runctx(
        "answer = profile_workload(limit)",
        globals(),
        local_namespace,
        str(output),
    )

    assert local_namespace["answer"] == profile_workload(3)
    assert output.exists()
    loaded = pstats.Stats(str(output))
    _, values = function_statistic(loaded, profile_workload)
    assert values[1] == 1


def test_pure_python_profile_implements_the_same_analysis_contract():
    profiler = profile.Profile()
    result = profiler.runcall(profile_workload, 3)
    statistics = pstats.Stats(profiler)

    assert result == profile_workload(3)
    _, values = function_statistic(statistics, profile_workload)
    assert values[0:2] == (1, 1)

    # profile.Profile 更容易扩展和校准，cProfile 通常开销更低；
    # 两者都能交给 pstats.Stats，但不要把不同 profiler/平台/未来版本的
    # dump 当稳定交换格式。


def test_pstats_sorts_filters_and_prints_a_readable_report():
    profiler = cProfile.Profile()
    profiler.runcall(profile_workload, 5)
    output = StringIO()
    statistics = pstats.Stats(profiler, stream=output)

    returned = (
        statistics.strip_dirs()
        .sort_stats(pstats.SortKey.CUMULATIVE, pstats.SortKey.NAME)
        .print_stats("profile_")
    )
    report = output.getvalue()

    assert returned is statistics
    assert statistics.total_calls >= statistics.prim_calls >= 1
    assert "Ordered by: cumulative time, function name" in report
    assert "profile_workload" in report
    assert "profile_leaf" in report
    assert "profile_recursive" in report
    assert "ncalls" in report
    assert "tottime" in report
    assert "cumtime" in report


def test_pstats_print_callers_and_callees_show_call_graph_edges():
    profiler = cProfile.Profile()
    profiler.runcall(profile_workload, 2)
    output = StringIO()
    statistics = pstats.Stats(profiler, stream=output).strip_dirs()

    statistics.sort_stats("name").print_callers("profile_leaf")
    callers_report = output.getvalue()
    assert "profile_leaf" in callers_report
    assert "profile_workload" in callers_report

    output.seek(0)
    output.truncate(0)
    statistics.print_callees("profile_workload")
    callees_report = output.getvalue()
    assert "profile_workload" in callees_report
    assert "profile_leaf" in callees_report
    assert "profile_recursive" in callees_report


def test_get_stats_profile_returns_named_dataclasses_for_programmatic_use():
    profiler = cProfile.Profile()
    profiler.runcall(profile_workload, 3)
    statistics = pstats.Stats(profiler).strip_dirs()

    stats_profile = statistics.get_stats_profile()
    function_profile = stats_profile.func_profiles["profile_workload"]

    assert stats_profile.total_tt >= 0
    assert function_profile.ncalls == "1"
    assert function_profile.tottime >= 0
    assert function_profile.cumtime >= function_profile.tottime
    assert function_profile.file_name == Path(__file__).name
    assert function_profile.line_number == profile_workload.__code__.co_firstlineno


def test_dump_load_and_add_accumulate_identically_named_function_stats(tmp_path):
    first_path = tmp_path / "first.prof"
    second_path = tmp_path / "second.prof"

    first = cProfile.Profile()
    second = cProfile.Profile()
    first.runcall(profile_workload, 2)
    second.runcall(profile_workload, 3)
    first.dump_stats(str(first_path))
    second.dump_stats(str(second_path))

    combined = pstats.Stats(str(first_path)).add(str(second_path))
    _, values = function_statistic(combined, profile_workload)
    assert values[0] == 2
    assert values[1] == 2

    roundtrip = tmp_path / "combined.prof"
    combined.dump_stats(str(roundtrip))
    reloaded = pstats.Stats(str(roundtrip))
    _, reloaded_values = function_statistic(reloaded, profile_workload)
    assert reloaded_values[:2] == (2, 2)


def test_timeit_string_statement_uses_the_supplied_globals_mapping():
    namespace = {"values": []}
    elapsed = timeit.timeit(
        "values.append(len(values))",
        number=3,
        globals=namespace,
    )

    assert namespace["values"] == [0, 1, 2]
    assert elapsed >= 0
    assert timeit.default_timer is time.perf_counter


def test_timer_callable_setup_is_excluded_and_statement_runs_number_times():
    events = []

    def setup():
        events.append("setup")

    def statement():
        events.append("statement")

    timer = timeit.Timer(
        stmt=statement,
        setup=setup,
        timer=timer_for_durations(4.5),
    )
    elapsed = timer.timeit(number=3)

    assert elapsed == 4.5
    assert events == ["setup", "statement", "statement", "statement"]


def test_repeat_returns_one_duration_per_fresh_timing_run():
    calls = []
    timer = timeit.Timer(
        stmt=lambda: calls.append("statement"),
        setup=lambda: calls.append("setup"),
        timer=timer_for_durations(0.4, 0.2, 0.3),
    )

    durations = timer.repeat(repeat=3, number=1)
    assert durations == pytest.approx([0.4, 0.2, 0.3])
    assert calls == [
        "setup",
        "statement",
        "setup",
        "statement",
        "setup",
        "statement",
    ]
    assert min(durations) == pytest.approx(0.2)

    # 文档建议关注 minimum：其他进程只能让某轮变慢，
    # 通常不会凭空让代码更快；mean/stdev 仍可用于观察噪声，
    # 但不能代替理解 benchmark 环境。


def test_autorange_tries_1_2_5_sequence_until_duration_is_large_enough():
    statement_calls = []
    callbacks = []
    timer = timeit.Timer(
        stmt=lambda: statement_calls.append(1),
        timer=timer_for_durations(0.01, 0.05, 0.25),
    )

    number, elapsed = timer.autorange(
        callback=lambda current_number, current_time: callbacks.append(
            (current_number, current_time)
        )
    )

    assert number == 5
    assert elapsed == pytest.approx(0.25)
    assert [item[0] for item in callbacks] == [1, 2, 5]
    assert [item[1] for item in callbacks] == pytest.approx([0.01, 0.05, 0.25])
    assert len(statement_calls) == 1 + 2 + 5


def test_timeit_temporarily_disables_gc_and_restores_previous_state():
    originally_enabled = gc.isenabled()
    if not originally_enabled:
        gc.enable()

    observed = []
    try:
        timer = timeit.Timer(lambda: observed.append(gc.isenabled()))
        timer.timeit(number=2)
        assert observed == [False, False]
        assert gc.isenabled() is True
    finally:
        if not originally_enabled:
            gc.disable()

    # 若被测 workload 依赖 cyclic collection，应在 setup 中显式 gc.enable()；
    # timeit 的默认选择减少跨轮 GC 噪声，但也可能掩盖真实工作负载成本。


def test_timer_rejects_values_that_are_neither_source_nor_callable():
    with pytest.raises(ValueError, match="stmt is neither a string nor callable"):
        timeit.Timer(stmt=object())

    with pytest.raises(ValueError, match="setup is neither a string nor callable"):
        timeit.Timer(setup=object())
