"""157｜gc：对象追踪、循环回收、终结和调优。

CPython 以引用计数处理大多数对象，并用分代循环垃圾回收器补上引用环。
本套只断言公开接口保证，不把临时计数或精确回收数量当成稳定业务
语义。会改变全局调试列表和永久代的案例放在子解释器；阈值、开关和
回调案例都用
``finally`` 恢复，避免一个内存管理示例改变后续测试环境。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.gc python.gc.reference-counting-and-cycles
# polyglot-covers: python.gc.enable-disable-isenabled
# polyglot-covers: python.gc.collect python.gc.generations
# polyglot-covers: python.gc.get-count python.gc.get-threshold
# polyglot-covers: python.gc.set-threshold python.gc.disable-automatic-collection
# polyglot-covers: python.gc.get-stats
# polyglot-covers: python.gc.is-tracked python.gc.atomic-vs-container
# polyglot-covers: python.gc.dynamic-untracking
# polyglot-covers: python.gc.get-objects python.gc.generation-filter
# polyglot-covers: python.gc.get-referents python.gc.get-referrers
# polyglot-covers: python.gc.debugging-introspection-caveat
# polyglot-covers: python.gc.callbacks python.gc.callback-info
# polyglot-covers: python.gc.debug-flags python.gc.debug-saveall
# polyglot-covers: python.gc.garbage
# polyglot-covers: python.gc.cyclic-finalizers python.gc.pep-442
# polyglot-covers: python.gc.is-finalized python.gc.resurrection-once
# polyglot-covers: python.gc.weakref-cycle-collection
# polyglot-covers: python.gc.freeze python.gc.unfreeze
# polyglot-covers: python.gc.get-freeze-count python.gc.copy-on-write-workflow

import gc
import json
import subprocess
import sys
import weakref

import pytest


class CycleNode:
    def __init__(self, name):
        self.name = name
        self.peer = None


def run_child(program):
    return subprocess.run(
        [sys.executable, "-c", program],
        check=True,
        capture_output=True,
        text=True,
    )


def test_gc_enable_disable_and_isenabled_form_a_restorable_process_switch():
    original = gc.isenabled()
    try:
        gc.disable()
        assert gc.isenabled() is False
        gc.enable()
        assert gc.isenabled() is True
    finally:
        if original:
            gc.enable()
        else:
            gc.disable()


def test_disabling_cyclic_gc_does_not_disable_reference_counting():
    class PlainObject:
        pass

    finalized = []
    original = gc.isenabled()
    try:
        gc.disable()
        value = PlainObject()
        reference = weakref.ref(value, lambda ref: finalized.append("released"))
        del value
        assert reference() is None
        assert finalized == ["released"]
    finally:
        if original:
            gc.enable()
        else:
            gc.disable()
    # gc.disable 只暂停循环检测；引用计数降到零的非循环对象仍会
    # 立即释放。


def test_collect_accepts_three_generations_and_rejects_an_invalid_generation():
    for generation in (0, 1, 2):
        collected = gc.collect(generation)
        assert isinstance(collected, int)
        assert collected >= 0

    with pytest.raises(ValueError, match="invalid generation"):
        gc.collect(3)


def test_collect_breaks_an_unreachable_reference_cycle():
    first = CycleNode("first")
    second = CycleNode("second")
    first.peer = second
    second.peer = first
    first_reference = weakref.ref(first)
    second_reference = weakref.ref(second)

    del first, second
    assert gc.collect() >= 2
    assert first_reference() is None
    assert second_reference() is None


def test_count_and_threshold_are_three_generation_tuples():
    count = gc.get_count()
    threshold = gc.get_threshold()
    assert len(count) == 3
    assert len(threshold) == 3
    assert all(isinstance(value, int) and value >= 0 for value in count)
    assert all(isinstance(value, int) and value >= 0 for value in threshold)


def test_set_threshold_controls_automatic_collection_and_is_restored():
    original = gc.get_threshold()
    try:
        gc.set_threshold(700, 11, 13)
        assert gc.get_threshold() == (700, 11, 13)

        gc.set_threshold(0)
        assert gc.get_threshold() == (0, 11, 13)
        # threshold0=0 关闭自动分代收集，但显式 gc.collect() 仍可运行。
        assert isinstance(gc.collect(0), int)
    finally:
        gc.set_threshold(*original)


def test_generation_stats_are_cumulative_dictionaries():
    before = gc.get_stats()
    gc.collect(0)
    after = gc.get_stats()

    assert len(after) == 3
    for generation in after:
        assert {"collections", "collected", "uncollectable"} <= generation.keys()
        assert all(isinstance(value, int) and value >= 0 for value in generation.values())
    assert after[0]["collections"] >= before[0]["collections"] + 1


def test_is_tracked_distinguishes_atomic_values_from_mutable_containers():
    assert gc.is_tracked(42) is False
    assert gc.is_tracked("immutable text") is False
    assert gc.is_tracked([]) is True
    assert gc.is_tracked({}) is False

    mapping = {"key": []}
    assert gc.is_tracked(mapping) is True
    # CPython 可把只含原子键值的 dict 动态移出追踪集合；是否优化
    # 不应被用作可移植业务语义，is_tracked 主要服务诊断。
    mapping["key"] = 1
    gc.collect()
    assert gc.is_tracked(mapping) is False


def test_get_objects_can_filter_by_generation_and_never_contains_result_list_itself():
    gc.collect()
    marker = CycleNode("young marker")
    generation_zero = gc.get_objects(generation=0)
    all_tracked = gc.get_objects()

    assert marker in generation_zero
    assert marker in all_tracked
    assert generation_zero not in generation_zero
    assert all_tracked not in all_tracked


def test_get_referents_exposes_traversal_edges_not_all_language_level_attributes():
    payload = []
    owner = CycleNode("owner")
    owner.peer = payload
    referents = gc.get_referents(owner)

    assert owner.__dict__ in referents
    assert owner.__class__ in referents
    assert payload in gc.get_referents(owner.__dict__)
    # 返回的是类型的 tp_traverse 暴露给循环 GC 的边，不承诺等同于 __dict__
    # 或 dir()；原子对象也可能不被报告。


def test_get_referrers_is_a_debug_snapshot_that_includes_live_local_containers():
    target = CycleNode("target")
    explicit_owner = [target]
    referrers = gc.get_referrers(target)

    assert any(referrer is explicit_owner for referrer in referrers)
    # 调用本身、当前栈和刚生成的结果都会改变对象图；不能依赖数量或
    # 用它证明“只有一个所有者”。诊断前 gc.collect() 也只能清除
    # 已不可达的环。


def test_gc_callbacks_receive_start_and_stop_phases_and_are_removed_afterward():
    events = []

    def callback(phase, info):
        events.append((phase, info.copy()))

    gc.callbacks.append(callback)
    try:
        gc.collect(0)
    finally:
        gc.callbacks.remove(callback)

    assert events[0][0] == "start"
    assert events[-1][0] == "stop"
    assert events[0][1]["generation"] == 0
    assert {"generation", "collected", "uncollectable"} <= events[-1][1].keys()
    assert callback not in gc.callbacks


def test_debug_saveall_and_garbage_are_isolated_in_a_child_interpreter():
    program = """
import gc
import json

class Node:
    pass

gc.set_debug(gc.DEBUG_SAVEALL)
first = Node()
second = Node()
first.peer = second
second.peer = first
del first, second
collected = gc.collect()
result = {
    "collected": collected,
    "saved_nodes": sum(type(value).__name__ == "Node" for value in gc.garbage),
    "debug": gc.get_debug(),
}
print(json.dumps(result))
gc.garbage.clear()
gc.set_debug(0)
"""
    result = json.loads(run_child(program).stdout)
    assert result["collected"] >= 2
    assert result["saved_nodes"] == 2
    assert result["debug"] & gc.DEBUG_SAVEALL
    # DEBUG_SAVEALL 有意把不可达对象留在 gc.garbage，会延长其生命期；
    # 生产诊断完成后必须清空列表并恢复 debug flags。


def test_debug_flag_constants_can_be_combined_as_a_bitmask():
    combined = gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_SAVEALL
    assert combined == gc.DEBUG_LEAK
    assert gc.DEBUG_STATS & combined == 0
    assert all(
        isinstance(flag, int)
        for flag in (
            gc.DEBUG_STATS,
            gc.DEBUG_COLLECTABLE,
            gc.DEBUG_UNCOLLECTABLE,
            gc.DEBUG_SAVEALL,
            gc.DEBUG_LEAK,
        )
    )


def test_cycles_with_del_are_collectable_under_safe_object_finalization():
    finalized = []

    class FinalizedNode:
        def __init__(self, name):
            self.name = name
            self.peer = None

        def __del__(self):
            finalized.append(self.name)

    first = FinalizedNode("first")
    second = FinalizedNode("second")
    first.peer = second
    second.peer = first
    references = (weakref.ref(first), weakref.ref(second))
    del first, second

    assert gc.collect() >= 2
    assert set(finalized) == {"first", "second"}
    assert all(reference() is None for reference in references)
    # 现代 Python 的安全终结协议能处理大多数带 __del__ 的纯 Python 环；
    # gc.garbage 通常只剩含有不安全 C 扩展终结器的特殊情况。


def test_is_finalized_marks_a_resurrected_object_and_del_only_runs_once():
    resurrected = []

    class Lazarus:
        def __del__(self):
            resurrected.append(self)

    value = Lazarus()
    value.cycle = value
    del value
    gc.collect()

    survivor = resurrected.pop()
    assert gc.is_finalized(survivor) is True
    reference = weakref.ref(survivor)
    survivor.cycle = None
    del survivor
    gc.collect()
    assert reference() is None
    assert resurrected == []
    # 一个对象即使被 __del__ 复活也已标为 finalized；再次死亡时
    # 不会重复调用。


def test_freeze_workflow_is_demonstrated_in_a_child_to_preserve_existing_permanent_state():
    program = """
import gc
import json

gc.collect()
before = gc.get_freeze_count()
marker = [[]]
gc.freeze()
frozen = gc.get_freeze_count()
gc.unfreeze()
after = gc.get_freeze_count()
print(json.dumps({"before": before, "frozen": frozen, "after": after}))
"""
    result = json.loads(run_child(program).stdout)
    assert result["frozen"] > result["before"]
    assert result["after"] == 0
    # fork 前“先 disable、再 freeze、子进程保持 disable”可减少写时复制页面；
    # freeze/unfreeze 操作整个解释器对象图，因此普通单元测试不应在
    # 主进程尝试。
