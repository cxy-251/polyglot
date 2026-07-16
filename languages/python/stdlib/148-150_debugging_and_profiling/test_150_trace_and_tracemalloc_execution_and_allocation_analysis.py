"""150｜trace 与 tracemalloc：语句执行计数、调用关系和内存分配快照。

``trace`` 基于 Python trace events 统计行与调用，``tracemalloc`` 在
allocator 层保存分配 traceback。前者不是分支覆盖工具，后者也不追踪
解释器之外的所有进程内存；案例展示各自能证明什么，以及全局 tracing
状态应如何收尾。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.trace python.trace.trace-class
# polyglot-covers: python.trace.run python.trace.runctx python.trace.runfunc
# polyglot-covers: python.trace.results-cumulative python.trace.line-counts
# polyglot-covers: python.trace.countfuncs python.trace.called-functions
# polyglot-covers: python.trace.countcallers python.trace.call-relationships
# polyglot-covers: python.trace.ignoremods python.trace.ignoredirs
# polyglot-covers: python.trace.coverage-results python.trace.update-results
# polyglot-covers: python.trace.write-results python.trace.show-missing
# polyglot-covers: python.trace.coverdir python.trace.summary
# polyglot-covers: python.trace.infile-outfile-count-accumulation
# polyglot-covers: python.trace.line-not-branch-coverage-boundary
# polyglot-covers: python.stdlib.tracemalloc python.tracemalloc.start-stop
# polyglot-covers: python.tracemalloc.traceback-limit python.tracemalloc.is-tracing
# polyglot-covers: python.tracemalloc.get-traced-memory
# polyglot-covers: python.tracemalloc.get-tracemalloc-memory
# polyglot-covers: python.tracemalloc.reset-peak python.tracemalloc.clear-traces
# polyglot-covers: python.tracemalloc.take-snapshot
# polyglot-covers: python.tracemalloc.snapshot-statistics
# polyglot-covers: python.tracemalloc.snapshot-compare-to
# polyglot-covers: python.tracemalloc.statistic python.tracemalloc.statistic-diff
# polyglot-covers: python.tracemalloc.filter python.tracemalloc.domain-filter
# polyglot-covers: python.tracemalloc.filter-inclusive-exclusive
# polyglot-covers: python.tracemalloc.filter-all-frames
# polyglot-covers: python.tracemalloc.snapshot-dump-load
# polyglot-covers: python.tracemalloc.snapshot-traces
# polyglot-covers: python.tracemalloc.trace-domain-size-traceback
# polyglot-covers: python.tracemalloc.get-object-traceback
# polyglot-covers: python.tracemalloc.frame python.tracemalloc.traceback-format
# polyglot-covers: python.tracemalloc.cumulative-statistics-boundary
# polyglot-covers: python.tracemalloc.process-global-ownership

from contextlib import contextmanager
from pathlib import Path
import sys
import trace
import tracemalloc

import pytest


def trace_leaf(value):
    return value * 2


def trace_branch(flag):
    if flag:
        return "taken"
    return "not taken"


def trace_workload(limit):
    values = []
    for value in range(limit):
        values.append(trace_leaf(value))
    return values


def allocation_layer(size, count):
    return [bytearray(size) for _ in range(count)]


def allocate_payload(size, count):
    return allocation_layer(size, count)


@contextmanager
def owned_tracemalloc(nframe=5):
    """只在未被外层启用时取得全局 tracemalloc 所有权。"""

    if tracemalloc.is_tracing():
        pytest.skip("outer process owns tracemalloc; do not clear its trace history")
    tracemalloc.start(nframe)
    try:
        yield
    finally:
        tracemalloc.stop()


def counts_for_current_file(results):
    return {
        (filename, lineno): count
        for (filename, lineno), count in results.counts.items()
        if filename == __file__
    }


def test_trace_runfunc_returns_value_and_accumulates_line_counts():
    tracer = trace.Trace(count=1, trace=0)

    assert tracer.runfunc(trace_workload, 3) == [0, 2, 4]
    first_results = tracer.results()
    first_counts = counts_for_current_file(first_results)
    assert first_counts
    assert sum(first_counts.values()) > 3

    tracer.runfunc(trace_workload, 3)
    second_counts = counts_for_current_file(tracer.results())
    assert second_counts.keys() == first_counts.keys()
    assert all(second_counts[key] == first_counts[key] * 2 for key in first_counts)

    # results() 是当前 Trace 的累计快照，不会把内部 counts 清零。


def test_trace_run_and_runctx_execute_source_in_selected_namespaces():
    tracer = trace.Trace(count=1, trace=0)
    namespace = {"value": 3}

    assert tracer.runctx("answer = value + 4", namespace, namespace) is None
    assert namespace["answer"] == 7

    # run 使用自己的默认命名空间；显式共享状态时优先使用 runctx。
    assert tracer.run("standalone = 5") is None
    string_counts = {
        key: count
        for key, count in tracer.results().counts.items()
        if key[0] == "<string>"
    }
    assert string_counts


def test_countfuncs_records_called_functions_without_line_counts():
    tracer = trace.Trace(count=0, trace=0, countfuncs=1)
    tracer.runfunc(trace_workload, 2)
    results = tracer.results()

    called_names = {function_key[2] for function_key in results.calledfuncs}
    assert "trace_workload" in called_names
    assert "trace_leaf" in called_names
    assert results.counts == {}


def test_countcallers_records_parent_child_relationships():
    tracer = trace.Trace(count=0, trace=0, countcallers=1)
    tracer.runfunc(trace_workload, 2)
    results = tracer.results()

    edges = {
        (parent[2], child[2])
        for parent, child in results.callers
        if len(parent) == 3 and len(child) == 3
    }
    assert ("trace_workload", "trace_leaf") in edges


def test_ignoremods_and_ignoredirs_filter_traced_modules():
    module_filtered = trace.Trace(
        count=1,
        trace=0,
        ignoremods=(__name__,),
    )
    module_filtered.runfunc(trace_workload, 2)
    assert counts_for_current_file(module_filtered.results()) == {}

    directory_filtered = trace.Trace(
        count=1,
        trace=0,
        ignoredirs=(str(Path(__file__).parent),),
    )
    directory_filtered.runfunc(trace_workload, 2)
    assert counts_for_current_file(directory_filtered.results()) == {}


def test_coverage_results_update_merges_counts_from_independent_runs():
    first_tracer = trace.Trace(count=1, trace=0)
    second_tracer = trace.Trace(count=1, trace=0)
    first_tracer.runfunc(trace_workload, 2)
    second_tracer.runfunc(trace_workload, 2)

    first = first_tracer.results()
    baseline = counts_for_current_file(first).copy()
    first.update(second_tracer.results())
    merged = counts_for_current_file(first)

    assert merged.keys() == baseline.keys()
    assert all(merged[key] == baseline[key] * 2 for key in baseline)


def test_write_results_creates_annotated_cover_file_with_missing_lines(
    tmp_path,
    capsys,
):
    tracer = trace.Trace(count=1, trace=0)
    assert tracer.runfunc(trace_branch, True) == "taken"

    tracer.results().write_results(
        show_missing=True,
        summary=True,
        coverdir=str(tmp_path),
    )
    output = capsys.readouterr().out
    cover_files = list(tmp_path.rglob("*.cover"))

    assert cover_files
    current_cover = next(
        path for path in cover_files if Path(__file__).stem in path.name
    )
    annotated = current_cover.read_text(encoding="utf-8")
    assert "trace_branch" in annotated
    assert "return \"taken\"" in annotated
    assert ">>>>>>" in annotated
    assert "return \"not taken\"" in annotated
    assert Path(__file__).stem in output

    # trace 以 executable line 为单位，不能区分同一行短路表达式的不同 branch；
    # 需要 branch coverage 时应使用专门覆盖工具。


def test_infile_and_outfile_accumulate_counts_across_trace_instances(tmp_path):
    counts_file = tmp_path / "trace-counts.dat"
    cover_dir = tmp_path / "cover"
    first = trace.Trace(count=1, trace=0, outfile=str(counts_file))
    first.runfunc(trace_workload, 2)
    first.results().write_results(show_missing=False, coverdir=str(cover_dir))
    baseline = counts_for_current_file(first.results())
    assert counts_file.exists()

    second = trace.Trace(
        count=1,
        trace=0,
        infile=str(counts_file),
        outfile=str(counts_file),
    )
    second.runfunc(trace_workload, 2)
    combined_results = second.results()
    combined = counts_for_current_file(combined_results)
    combined_results.write_results(show_missing=False, coverdir=str(cover_dir))

    assert combined.keys() == baseline.keys()
    assert all(combined[key] == baseline[key] * 2 for key in baseline)


def test_tracemalloc_start_limit_memory_counters_and_stop_lifecycle():
    with owned_tracemalloc(nframe=7):
        assert tracemalloc.is_tracing() is True
        assert tracemalloc.get_traceback_limit() == 7
        baseline_current, baseline_peak = tracemalloc.get_traced_memory()
        payload = allocate_payload(4096, 16)
        current, peak = tracemalloc.get_traced_memory()

        assert len(payload) == 16
        assert current > baseline_current + 50_000
        assert peak >= current
        assert peak >= baseline_peak
        assert tracemalloc.get_tracemalloc_memory() > 0

        tracemalloc.reset_peak()
        reset_current, reset_peak = tracemalloc.get_traced_memory()
        assert reset_peak >= reset_current

    assert tracemalloc.is_tracing() is False
    with pytest.raises(RuntimeError, match="must be tracing"):
        tracemalloc.take_snapshot()


def test_tracemalloc_rejects_non_positive_traceback_limits():
    if tracemalloc.is_tracing():
        pytest.skip("outer process owns tracemalloc")

    with pytest.raises(ValueError, match="frames must be in range"):
        tracemalloc.start(0)
    assert tracemalloc.is_tracing() is False


def test_snapshot_statistics_and_compare_to_find_positive_allocation_growth():
    with owned_tracemalloc(nframe=5):
        before = tracemalloc.take_snapshot()
        payload = allocate_payload(2048, 20)
        after = tracemalloc.take_snapshot()

        line_statistics = after.statistics("lineno")
        assert line_statistics
        assert all(
            left.size >= right.size
            for left, right in zip(line_statistics, line_statistics[1:])
        )
        assert all(statistic.count > 0 for statistic in line_statistics)

        differences = after.compare_to(before, "lineno")
        relevant = [
            difference
            for difference in differences
            if any(frame.filename == __file__ for frame in difference.traceback)
            and difference.size_diff > 0
        ]
        assert len(payload[0]) == 2048
        assert relevant
        assert sum(item.size_diff for item in relevant) > 30_000
        assert all(item.count > 0 for item in relevant)
        assert any(item.count_diff > 0 for item in relevant)


def test_snapshot_statistics_support_grouping_and_restrict_cumulative_mode():
    with owned_tracemalloc(nframe=5):
        payload = allocate_payload(512, 10)
        snapshot = tracemalloc.take_snapshot()

        by_filename = snapshot.statistics("filename")
        by_lineno = snapshot.statistics("lineno")
        by_traceback = snapshot.statistics("traceback")
        cumulative = snapshot.statistics("lineno", cumulative=True)

        assert payload
        assert by_filename and by_lineno and by_traceback and cumulative
        assert all(len(item.traceback) == 1 for item in by_filename)
        with pytest.raises(ValueError, match="cumulative mode"):
            snapshot.statistics("traceback", cumulative=True)


def test_snapshot_filters_combine_inclusions_exclusions_and_domains():
    with owned_tracemalloc(nframe=5):
        payload = allocate_payload(256, 8)
        snapshot = tracemalloc.take_snapshot()

        include_file = tracemalloc.Filter(True, __file__, all_frames=True)
        python_domain = tracemalloc.DomainFilter(True, 0)
        assert include_file.inclusive is True
        assert include_file.filename_pattern == __file__
        assert include_file.lineno is None
        assert include_file.all_frames is True
        assert python_domain.inclusive is True
        assert python_domain.domain == 0

        included = snapshot.filter_traces([include_file, python_domain])
        assert payload
        assert len(included.traces) > 0
        assert all(trace_record.domain == 0 for trace_record in included.traces)
        assert all(
            any(frame.filename == __file__ for frame in trace_record.traceback)
            for trace_record in included.traces
        )

        excluded = snapshot.filter_traces(
            [tracemalloc.Filter(False, __file__, all_frames=True)]
        )
        assert all(
            all(frame.filename != __file__ for frame in trace_record.traceback)
            for trace_record in excluded.traces
        )


def test_snapshot_dump_and_load_preserve_trace_data(tmp_path):
    with owned_tracemalloc(nframe=3):
        payload = allocate_payload(1024, 5)
        snapshot = tracemalloc.take_snapshot()
        output = tmp_path / "memory.snapshot"
        snapshot.dump(str(output))
        loaded = tracemalloc.Snapshot.load(str(output))

        assert payload
        assert loaded.traceback_limit == snapshot.traceback_limit == 3
        assert len(loaded.traces) == len(snapshot.traces)
        assert sum(item.size for item in loaded.traces) == sum(
            item.size for item in snapshot.traces
        )
        assert output.exists()

        # dump 是诊断 artifact，不是面向长期兼容的数据交换格式；
        # 消费者应使用匹配版本的 Snapshot.load，并在报告中保留解释器版本。


def test_trace_records_expose_domain_size_and_formattable_traceback():
    with owned_tracemalloc(nframe=5):
        payload = allocate_payload(128, 4)
        snapshot = tracemalloc.take_snapshot()
        record = next(
            item
            for item in snapshot.traces
            if any(frame.filename == __file__ for frame in item.traceback)
        )

        assert payload
        assert record.domain == 0
        assert record.size > 0
        assert 1 <= len(record.traceback) <= 5
        assert record.traceback.total_nframe >= len(record.traceback)
        assert all(frame.filename and frame.lineno >= 0 for frame in record.traceback)

        formatted = record.traceback.format(limit=3, most_recent_first=True)
        assert formatted
        assert any(Path(__file__).name in line for line in formatted)


def test_get_object_traceback_reports_where_a_traced_object_was_allocated():
    with owned_tracemalloc(nframe=5):
        payload = bytearray(2048)
        allocation_traceback = tracemalloc.get_object_traceback(payload)

        assert allocation_traceback is not None
        assert any(frame.filename == __file__ for frame in allocation_traceback)
        # 对象查询路径在 3.10 可能不知道截断前总帧数，以 None 表示；Snapshot trace 通常有值。
        if allocation_traceback.total_nframe is not None:
            assert allocation_traceback.total_nframe >= len(allocation_traceback)
        assert 1 <= len(allocation_traceback) <= 5

    assert tracemalloc.get_object_traceback(payload) is None


def test_clear_traces_resets_history_without_stopping_hooks():
    with owned_tracemalloc(nframe=2):
        payload = allocate_payload(1024, 8)
        before_current, before_peak = tracemalloc.get_traced_memory()
        assert payload
        assert before_current > 0
        assert before_peak >= before_current

        tracemalloc.clear_traces()
        assert tracemalloc.is_tracing() is True
        assert tracemalloc.get_traceback_limit() == 2
        assert tracemalloc.get_traced_memory() == (0, 0)

        # reset_peak 只重置峰值基线而保留 traces；clear_traces 清空历史但保留
        # allocator hooks；stop 同时卸载 hooks 并清空历史。
