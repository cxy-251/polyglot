"""067｜``graphlib.TopologicalSorter`` 的依赖方向、批次调度与环检测。

构造参数采用 ``node -> predecessors``，也就是 value 是必须先完成的节点，而不是
successor。一次性顺序使用 ``static_order``；并行/分批工作流则显式经历
``prepare -> get_ready -> done`` 状态机。``CycleError`` 后仍可处理未被环阻塞的部分。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.graphlib.TopologicalSorter python.graphlib.predecessor-graph
# polyglot-covers: python.graphlib.add python.graphlib.add-union python.graphlib.implicit-nodes
# polyglot-covers: python.graphlib.hashable-nodes python.graphlib.duplicate-predecessors
# polyglot-covers: python.graphlib.prepare python.graphlib.python310-prepare-once
# polyglot-covers: python.graphlib.get_ready python.graphlib.done python.graphlib.ready-batches
# polyglot-covers: python.graphlib.is_active python.graphlib.bool
# polyglot-covers: python.graphlib.outstanding-nodes python.graphlib.done-validation
# polyglot-covers: python.graphlib.static_order python.graphlib.insertion-order
# polyglot-covers: python.graphlib.CycleError python.graphlib.cycle-path
# polyglot-covers: python.graphlib.partial-progress-after-cycle python.graphlib.self-cycle

from graphlib import CycleError, TopologicalSorter

import pytest


def assert_precedes(order, predecessor, successor):
    """只验证拓扑约束，不把同一 ready 层中本来无关的节点顺序写死。"""

    assert order.index(predecessor) < order.index(successor)


def test_constructor_mapping_values_are_predecessors_not_successors():
    """``target: requirements`` 表示 requirements 必须在 target 之前完成。"""

    graph = {
        "deploy": {"test"},
        "test": {"build"},
        "build": set(),
    }

    order = tuple(TopologicalSorter(graph).static_order())

    assert order == ("build", "test", "deploy")


def test_static_order_satisfies_every_dependency_without_promising_one_total_order():
    """多个合法拓扑序可能同时存在；可靠断言应检查边约束，而非无关 sibling 次序。"""

    graph = {
        "package": {"unit-tests", "integration-tests"},
        "unit-tests": {"build"},
        "integration-tests": {"build", "database"},
        "build": {"generate"},
        "database": set(),
        "generate": set(),
    }

    order = list(TopologicalSorter(graph).static_order())

    assert set(order) == set(graph)
    for node, predecessors in graph.items():
        for predecessor in predecessors:
            assert_precedes(order, predecessor, node)


def test_predecessor_named_only_in_add_is_automatically_added_as_a_node():
    """不必先声明叶子依赖；首次作为 predecessor 出现时，它会以零依赖节点加入。"""

    sorter = TopologicalSorter()
    sorter.add("compile", "generate")

    assert tuple(sorter.static_order()) == ("generate", "compile")


def test_repeated_add_calls_union_a_nodes_dependencies():
    """同一 node 多次 add 不是覆盖；所有 predecessor 会求并集。"""

    sorter = TopologicalSorter()
    sorter.add("deploy", "tests")
    sorter.add("deploy", "security-scan")
    sorter.prepare()

    first_batch = set(sorter.get_ready())
    assert first_batch == {"tests", "security-scan"}

    sorter.done(*first_batch)
    assert sorter.get_ready() == ("deploy",)


def test_duplicate_predecessors_are_collapsed_and_zero_dependency_add_is_valid():
    """依赖关系按集合处理；重复 edge 不会要求 done 两次，也可显式添加独立节点。"""

    sorter = TopologicalSorter()
    sorter.add("build", "source", "source")
    sorter.add("standalone")
    sorter.prepare()

    ready = set(sorter.get_ready())
    assert ready == {"source", "standalone"}

    sorter.done("source")
    assert sorter.get_ready() == ("build",)


def test_nodes_may_be_any_hashable_objects_but_not_mutable_lists():
    """算法以 node 为 dict key；tuple、None 等可用，list 等不可哈希对象立即失败。"""

    root = ("source", 1)
    target = ("artifact", 2)
    sorter = TopologicalSorter()
    sorter.add(target, root, None)

    order = list(sorter.static_order())
    assert set(order) == {root, target, None}
    assert_precedes(order, root, target)
    assert_precedes(order, None, target)

    with pytest.raises(TypeError, match="unhashable type"):
        TopologicalSorter().add([])


@pytest.mark.parametrize("operation", ["get_ready", "is_active", "done"])
def test_stateful_operations_require_prepare_first(operation):
    """显式调度 API 不能跳过 prepare；该步骤会冻结图并建立 ready 状态。"""

    sorter = TopologicalSorter({"task": set()})

    with pytest.raises(ValueError):
        if operation == "done":
            sorter.done("task")
        else:
            getattr(sorter, operation)()


def test_prepare_freezes_the_graph_and_add_afterwards_is_rejected():
    """一旦准备调度，依赖计数必须稳定，因此后续 add 会抛 ValueError。"""

    sorter = TopologicalSorter({"task": set()})
    sorter.prepare()

    with pytest.raises(ValueError, match="cannot be added after"):
        sorter.add("late-task")


def test_python_310_prepare_cannot_be_called_twice():
    """Python 3.10 即使尚未 get_ready 也只允许一次 prepare；较新版本已放宽部分场景。"""

    sorter = TopologicalSorter({"task": set()})
    sorter.prepare()

    with pytest.raises(ValueError, match=r"prepare\(\) more than once"):
        sorter.prepare()


def test_get_ready_and_done_form_dependency_levels_for_batch_processing():
    """每批包含当前全部零未完成依赖节点；整批 done 后才释放下一层。"""

    graph = {
        "fetch": set(),
        "lint": set(),
        "build": {"fetch"},
        "test": {"build", "lint"},
        "package": {"test"},
    }
    sorter = TopologicalSorter(graph)
    sorter.prepare()
    batches = []

    while sorter:
        ready = sorter.get_ready()
        batches.append(set(ready))
        sorter.done(*ready)

    assert batches == [
        {"fetch", "lint"},
        {"build"},
        {"test"},
        {"package"},
    ]


def test_get_ready_returns_each_node_once_and_waits_for_done():
    """节点一旦交给 worker 就成为 outstanding；未 done 前不会再次返回，也不释放后继。"""

    sorter = TopologicalSorter({"child": {"root"}, "root": set()})
    sorter.prepare()

    assert sorter.get_ready() == ("root",)
    assert sorter.get_ready() == ()
    assert sorter.is_active()

    sorter.done("root")
    assert sorter.get_ready() == ("child",)


def test_successor_waits_until_every_predecessor_is_done():
    """多个 ready task 可独立完成；只完成其中一个时，共同 successor 仍不可调度。"""

    sorter = TopologicalSorter({"merge": {"left", "right"}})
    sorter.prepare()
    ready = set(sorter.get_ready())
    assert ready == {"left", "right"}

    sorter.done("left")
    assert sorter.get_ready() == ()
    assert sorter.is_active()

    sorter.done("right")
    assert sorter.get_ready() == ("merge",)


def test_bool_delegates_to_is_active_and_turns_false_after_all_done():
    """``while sorter`` 是官方状态循环的简写；完成最后一个已返回节点后变为 False。"""

    sorter = TopologicalSorter({"task": set()})
    sorter.prepare()

    assert bool(sorter) is True
    ready = sorter.get_ready()
    assert bool(sorter) is True

    sorter.done(*ready)
    assert sorter.is_active() is False
    assert bool(sorter) is False


def test_done_rejects_nodes_that_were_not_returned_as_ready():
    """done 是 worker 完成确认，不是强制跳过依赖的接口；只能确认 get_ready 交付过的节点。"""

    sorter = TopologicalSorter({"child": {"root"}})
    sorter.prepare()

    with pytest.raises(ValueError, match="not passed out"):
        sorter.done("root")

    assert sorter.get_ready() == ("root",)
    with pytest.raises(ValueError, match="not passed out"):
        sorter.done("child")


def test_done_rejects_unknown_and_already_completed_nodes():
    """拼错 node 或重复完成都会抛错，避免依赖计数被静默破坏。"""

    sorter = TopologicalSorter({"task": set()})
    sorter.prepare()
    assert sorter.get_ready() == ("task",)

    with pytest.raises(ValueError, match="not added"):
        sorter.done("unknown")

    sorter.done("task")
    with pytest.raises(ValueError, match="already been marked done"):
        sorter.done("task")


def test_static_order_is_the_convenience_path_without_manual_state_calls():
    """只需单线程线性顺序时直接消费 iterator；它内部负责 prepare/get_ready/done。"""

    sorter = TopologicalSorter({"publish": {"build"}, "build": {"source"}})

    iterator = sorter.static_order()

    assert iter(iterator) is iterator
    assert list(iterator) == ["source", "build", "publish"]


def test_insertion_order_only_breaks_ties_between_nodes_on_the_same_level():
    """同一 ready level 没有依赖顺序，结果用图的插入顺序打破平局。"""

    first = TopologicalSorter()
    first.add(3, 2, 1)
    first.add(1, 0)

    second = TopologicalSorter()
    second.add(1, 0)
    second.add(3, 2, 1)

    assert list(first.static_order()) == [2, 0, 1, 3]
    assert list(second.static_order()) == [0, 2, 1, 3]


def test_cycle_error_exposes_one_closed_cycle_path_in_args():
    """异常 args[1] 是首尾重复的一个实际环；有多个环时不要依赖报告哪一个。"""

    graph = {
        "parse": {"validate"},
        "validate": {"store"},
        "store": {"parse"},
    }
    sorter = TopologicalSorter(graph)

    with pytest.raises(CycleError) as caught:
        sorter.prepare()

    cycle = caught.value.args[1]
    assert cycle[0] == cycle[-1]
    assert set(cycle[:-1]) == {"parse", "validate", "store"}

    for predecessor, successor in zip(cycle, cycle[1:]):
        assert predecessor in graph[successor]


def test_acyclic_nodes_can_still_progress_after_prepare_reports_a_cycle():
    """prepare 发现环后状态仍可用；可完成不受环阻塞的分支，直到只剩死锁部分。"""

    graph = {
        "generate": set(),
        "compile": {"generate"},
        "package": {"compile"},
        "cycle-a": {"cycle-b"},
        "cycle-b": {"cycle-a"},
    }
    sorter = TopologicalSorter(graph)

    with pytest.raises(CycleError):
        sorter.prepare()

    processed = []
    while sorter:
        ready = sorter.get_ready()
        processed.extend(ready)
        sorter.done(*ready)

    assert processed == ["generate", "compile", "package"]
    assert sorter.get_ready() == ()


def test_self_dependency_is_a_cycle_and_static_order_raises_when_consumed():
    """node 依赖自身也是环；static_order 是惰性 iterator，异常发生在开始迭代时。"""

    sorter = TopologicalSorter({"recursive": {"recursive"}})
    iterator = sorter.static_order()

    with pytest.raises(CycleError) as caught:
        tuple(iterator)

    assert caught.value.args[1] == ["recursive", "recursive"]
