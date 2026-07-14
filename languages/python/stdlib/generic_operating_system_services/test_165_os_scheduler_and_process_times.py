"""165｜``os`` scheduler 的 read-only introspection、affinity 与 process times。

scheduler setters 会改变测试进程并可能需要 privilege，本文件只查询 policy、
priority、CPU affinity 和 timing。``sched_yield`` 是无返回值的调度提示，不保证
另一 thread/process 一定立即获得 CPU。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.os.sched-getscheduler python.os.sched-getparam
# polyglot-covers: python.os.sched-param python.os.sched-priority-range
# polyglot-covers: python.os.sched-get-priority-min python.os.sched-get-priority-max
# polyglot-covers: python.os.sched-getaffinity python.os.cpu-affinity
# polyglot-covers: python.os.sched-yield python.os.scheduler-readonly-introspection
# polyglot-covers: python.os.times python.os.times-result

import os

import pytest


@pytest.mark.skipif(
    not all(
        hasattr(os, name)
        for name in (
            "sched_getscheduler",
            "sched_getparam",
            "sched_get_priority_min",
            "sched_get_priority_max",
        )
    ),
    reason="平台不提供 scheduler introspection",
)
def test_scheduler_policy_parameter_and_priority_range_are_consistent():
    """pid=0 表示 caller；sched_param 是带 named field 的 immutable tuple-like。"""

    policy = os.sched_getscheduler(0)
    parameter = os.sched_getparam(0)
    minimum = os.sched_get_priority_min(policy)
    maximum = os.sched_get_priority_max(policy)

    assert isinstance(parameter, os.sched_param)
    assert tuple(parameter) == (parameter.sched_priority,)
    assert minimum <= parameter.sched_priority <= maximum


@pytest.mark.skipif(
    not hasattr(os, "sched_getaffinity"),
    reason="平台不提供 CPU affinity query",
)
def test_affinity_is_usable_cpu_set_not_machine_cpu_count():
    """container/cgroup 可限制 usable CPUs，所以 affinity 可能小于 cpu_count。"""

    affinity = os.sched_getaffinity(0)
    machine_count = os.cpu_count()

    assert isinstance(affinity, set)
    assert affinity
    assert all(type(cpu) is int and cpu >= 0 for cpu in affinity)
    if machine_count is not None:
        assert len(affinity) <= machine_count


@pytest.mark.skipif(not hasattr(os, "sched_yield"), reason="平台不提供 sched_yield")
def test_sched_yield_returns_none_without_promising_execution_order():
    """yield 只主动放弃当前 time slice；没有可调度 peer 时可以立即继续。"""

    assert os.sched_yield() is None


def test_times_result_has_named_fields_and_legacy_five_tuple_view():
    """CPU time 与 elapsed real time 不是同一时钟，不能彼此替代。"""

    measured = os.times()

    assert len(measured) == 5
    assert tuple(measured) == (
        measured.user,
        measured.system,
        measured.children_user,
        measured.children_system,
        measured.elapsed,
    )
    assert all(value >= 0 for value in measured)
