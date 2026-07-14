"""057｜``heapq`` 最小堆、流式选择与可更新优先队列示例。

``heapq`` 不提供容器类，而是在普通 list 上维护零基索引的最小堆不变量：父节点
不大于两个子节点，因此只能保证 ``heap[0]`` 是最小值，不能把内部 list 当成完整
排序结果。组合操作、惰性归并和稳定优先队列还各有不同的返回值与状态语义。

当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.heapq.heap-invariant python.heapq.zero-based-children
# polyglot-covers: python.heapq.heapify python.heapq.in-place
# polyglot-covers: python.heapq.heappush python.heapq.heappop python.heapq.peek
# polyglot-covers: python.heapq.less-than-comparison python.heapq.no-key-primitive
# polyglot-covers: python.heapq.heappushpop python.heapq.heapreplace
# polyglot-covers: python.heapq.empty-behavior python.heapq.fixed-size-top-k
# polyglot-covers: python.heapq.max-heap-negation python.heapq.tuple-priority
# polyglot-covers: python.heapq.equal-priority python.heapq.noncomparable-payload
# polyglot-covers: python.heapq.dataclass-wrapper python.heapq.stable-tie-breaker
# polyglot-covers: python.heapq.mutable-priority python.heapq.lazy-deletion
# polyglot-covers: python.heapq.priority-update python.heapq.task-removal
# polyglot-covers: python.heapq.merge python.heapq.merge-lazy
# polyglot-covers: python.heapq.merge-key python.heapq.merge-reverse
# polyglot-covers: python.heapq.merge-sorted-precondition python.heapq.merge-unbounded
# polyglot-covers: python.heapq.nlargest python.heapq.nsmallest
# polyglot-covers: python.heapq.selection-key python.heapq.selection-boundaries

from dataclasses import dataclass
from dataclasses import field
import heapq
from itertools import count
from itertools import islice

import pytest


def assert_min_heap_invariant(heap):
    """逐项检查公开文档给出的 ``parent <= child`` 数组表示。"""

    for parent_index, parent in enumerate(heap):
        left_index = 2 * parent_index + 1
        right_index = left_index + 1
        if left_index < len(heap):
            assert parent <= heap[left_index]
        if right_index < len(heap):
            assert parent <= heap[right_index]


@dataclass(order=True)
class PrioritizedItem:
    """只比较 priority；任意类型的 payload 都不参与堆排序。"""

    priority: int
    item: object = field(compare=False)


_REMOVED = object()


class UpdatablePriorityQueue:
    """采用官方 recipe 的 entry finder、唯一序号和惰性删除策略。"""

    def __init__(self):
        self.heap = []
        self.entries = {}
        self.counter = count()

    def add(self, task, priority=0):
        if task in self.entries:
            self.remove(task)

        entry = [priority, next(self.counter), task]
        self.entries[task] = entry
        heapq.heappush(self.heap, entry)

    def remove(self, task):
        entry = self.entries.pop(task)
        entry[-1] = _REMOVED

    def pop(self):
        while self.heap:
            priority, _sequence, task = heapq.heappop(self.heap)
            if task is not _REMOVED:
                del self.entries[task]
                return priority, task
        raise KeyError("pop from an empty priority queue")


def test_heapify_mutates_the_existing_list_and_establishes_min_heap_invariant():
    """heapify 线性地原地重排 list 并返回 None；调用方持有的仍是同一对象。"""

    values = [9, 1, 8, 2, 7, 3, 6]
    original_id = id(values)

    result = heapq.heapify(values)

    assert result is None
    assert id(values) == original_id
    assert values[0] == 1
    assert sorted(values) == [1, 2, 3, 6, 7, 8, 9]
    assert_min_heap_invariant(values)


def test_heap_internal_list_is_not_a_sorted_sequence_beyond_the_root():
    """堆只承诺父子关系；需要有序输出时应反复 heappop，而不是直接遍历 list。"""

    heap = [9, 1, 8, 2, 7, 3, 6]
    heapq.heapify(heap)

    internal_layout = list(heap)
    popped = [heapq.heappop(heap) for _ in range(len(heap))]

    assert internal_layout[0] == min(internal_layout)
    assert internal_layout != sorted(internal_layout)
    assert popped == sorted(internal_layout)
    assert heap == []


def test_heappush_and_heappop_maintain_the_invariant_and_return_none_or_minimum():
    """push 原地修改且返回 None；pop 删除并返回当前最小值，peek 则只读 heap[0]。"""

    heap = []

    for value in [5, 1, 4, 1, 3]:
        assert heapq.heappush(heap, value) is None
        assert_min_heap_invariant(heap)

    snapshot = list(heap)
    assert heap[0] == 1
    assert heap == snapshot
    assert [heapq.heappop(heap) for _ in range(5)] == [1, 1, 3, 4, 5]

    with pytest.raises(IndexError):
        heapq.heappop(heap)


def test_heap_operations_only_need_less_than_comparison_not_full_ordering():
    """内部筛选使用 ``<``；自定义元素不必实现 <=、> 或完整 total ordering。"""

    class OnlyLessThan:
        def __init__(self, value):
            self.value = value

        def __lt__(self, other):
            return self.value < other.value

    heap = [OnlyLessThan(4), OnlyLessThan(1), OnlyLessThan(3)]
    heapq.heapify(heap)

    assert [heapq.heappop(heap).value for _ in range(3)] == [1, 3, 4]


def test_heap_primitives_have_no_key_parameter_so_entries_must_be_decorated():
    """heappush/heappop 没有 key=；常用替代是把比较键放在 tuple 第一项。"""

    jobs = []

    with pytest.raises(TypeError):
        heapq.heappush(jobs, {"priority": 2}, key=lambda row: row["priority"])

    heapq.heappush(jobs, (2, "compile"))
    heapq.heappush(jobs, (1, "lint"))

    assert heapq.heappop(jobs) == (1, "lint")


def test_heappushpop_returns_the_smaller_value_and_keeps_the_larger_one():
    """新值小于 root 时会直接返回且堆不变；较大时才替换 root 并重新筛选。"""

    heap = [3, 5, 7]
    heapq.heapify(heap)
    snapshot = list(heap)

    assert heapq.heappushpop(heap, 2) == 2
    assert heap == snapshot

    assert heapq.heappushpop(heap, 6) == 3
    assert sorted(heap) == [5, 6, 7]
    assert len(heap) == 3
    assert_min_heap_invariant(heap)


def test_heapreplace_always_returns_old_root_even_when_new_item_is_smaller():
    """replace 先移除旧 root 再放新值，因此返回值可能比插入值大，且长度不变。"""

    heap = [3, 5, 7]
    heapq.heapify(heap)

    assert heapq.heapreplace(heap, 2) == 3
    assert sorted(heap) == [2, 5, 7]
    assert len(heap) == 3
    assert_min_heap_invariant(heap)


def test_empty_heap_distinguishes_heappushpop_from_heapreplace():
    """空堆 pushpop 直接退回 item 且仍为空；replace 没有旧 root，所以抛 IndexError。"""

    heap = []

    assert heapq.heappushpop(heap, 10) == 10
    assert heap == []

    with pytest.raises(IndexError):
        heapq.heapreplace(heap, 10)


def test_heappushpop_maintains_largest_n_values_from_a_stream():
    """固定大小的最小堆把候选下界放在 root，适合单遍保留最大的少量元素。"""

    def largest_n(iterable, size):
        heap = []
        for value in iterable:
            if len(heap) < size:
                heapq.heappush(heap, value)
            else:
                heapq.heappushpop(heap, value)
        return sorted(heap, reverse=True)

    stream = (value for value in [8, 1, 5, 12, 3, 10, 2])

    assert largest_n(stream, 3) == [12, 10, 8]


def test_negative_priorities_adapt_min_heap_into_numeric_max_priority_queue():
    """3.10 的公开 API 是最小堆；数值取负可让最高原始 priority 最先弹出。"""

    heap = []
    sequence = count()

    for priority, task in [(2, "normal"), (9, "urgent"), (9, "incident")]:
        heapq.heappush(heap, (-priority, next(sequence), task))

    assert heapq.heappop(heap)[2] == "urgent"
    assert heapq.heappop(heap)[2] == "incident"
    assert heapq.heappop(heap)[2] == "normal"


def test_equal_tuple_priorities_try_to_compare_payloads_and_can_fail():
    """(priority, task) 的 priority 相同时会继续比较 task；dict 等不可排序对象会报错。"""

    heap = []
    heapq.heappush(heap, (1, {"name": "first"}))

    with pytest.raises(TypeError, match="not supported"):
        heapq.heappush(heap, (1, {"name": "second"}))

    # heappush 不是事务操作；比较失败后不要假设 heap 自动回到调用前状态。


def test_dataclass_wrapper_excludes_noncomparable_payload_from_ordering():
    """order=True 配合 compare=False 可封装任意 payload，但相同 priority 不保证稳定顺序。"""

    heap = [
        PrioritizedItem(3, {"name": "mapping payload"}),
        PrioritizedItem(1, object()),
    ]
    heapq.heapify(heap)

    assert heapq.heappop(heap).priority == 1
    assert heapq.heappop(heap).priority == 3


def test_unique_sequence_tie_breaker_preserves_fifo_for_equal_priorities():
    """(priority, sequence, task) 的唯一序号同时避免比较 task，并提供同优先级 FIFO。"""

    heap = []
    sequence = count()

    for task in ["first", "second", "third"]:
        heapq.heappush(heap, (5, next(sequence), task))

    assert [heapq.heappop(heap)[2] for _ in range(3)] == [
        "first",
        "second",
        "third",
    ]


def test_mutating_an_enqueued_priority_silently_breaks_heap_invariant():
    """heapq 不监控元素字段变化；原地改 priority 后要重建堆或采用惰性替换。"""

    urgent = PrioritizedItem(1, "urgent")
    normal = PrioritizedItem(5, "normal")
    heap = [urgent, normal]
    heapq.heapify(heap)

    urgent.priority = 10

    assert heap[0] is urgent
    assert min(item.priority for item in heap) == 5

    heapq.heapify(heap)
    assert heap[0] is normal


def test_updatable_priority_queue_marks_old_entries_and_skips_them_lazily():
    """改变优先级时标记旧 entry、压入新 entry；pop 才清理堆中的失效记录。"""

    queue = UpdatablePriorityQueue()
    queue.add("build", priority=5)
    queue.add("docs", priority=3)
    queue.add("build", priority=1)
    queue.add("release", priority=1)
    queue.remove("docs")

    assert queue.pop() == (1, "build")
    assert queue.pop() == (1, "release")

    with pytest.raises(KeyError, match="empty priority queue"):
        queue.pop()
    assert queue.heap == []
    assert queue.entries == {}


def test_priority_queue_remove_reports_unknown_tasks_without_touching_heap():
    """entry finder 提供 O(1) 查找；删除不存在的 task 保留 dict 的 KeyError 语义。"""

    queue = UpdatablePriorityQueue()
    queue.add("known", priority=2)
    snapshot = list(queue.heap)

    with pytest.raises(KeyError) as error:
        queue.remove("missing")

    assert error.value.args == ("missing",)
    assert queue.heap == snapshot
    assert queue.pop() == (2, "known")


def test_merge_lazily_combines_already_sorted_inputs_without_materializing_all():
    """创建 merge iterator 不拉取输入；首次 next 为比较而各读取一个首元素。"""

    events = []

    def source(name, values):
        for value in values:
            events.append((name, value))
            yield value

    merged = heapq.merge(
        source("left", [1, 4]),
        source("right", [2, 3]),
    )

    assert events == []
    assert next(merged) == 1
    assert events == [("left", 1), ("right", 2)]
    assert list(merged) == [2, 3, 4]
    assert events == [
        ("left", 1),
        ("right", 2),
        ("left", 4),
        ("right", 3),
    ]


def test_merge_key_combines_sorted_record_streams_by_extracted_field():
    """key 只提取比较值，输出仍是原记录；每个输入必须已按同一 key 升序排列。"""

    service_a = [
        {"timestamp": 1, "message": "a-start"},
        {"timestamp": 4, "message": "a-end"},
    ]
    service_b = [
        {"timestamp": 2, "message": "b-start"},
        {"timestamp": 3, "message": "b-end"},
    ]

    merged = heapq.merge(
        service_a,
        service_b,
        key=lambda record: record["timestamp"],
    )

    assert [record["timestamp"] for record in merged] == [1, 2, 3, 4]


def test_merge_reverse_requires_every_input_to_be_descending_too():
    """reverse=True 反转比较方向，不会替调用方逆序各输入；输入必须预先降序。"""

    left = [(9, "left-high"), (5, "left-low")]
    right = [(8, "right-high"), (4, "right-low")]

    merged = heapq.merge(left, right, key=lambda row: row[0], reverse=True)

    assert [score for score, _name in merged] == [9, 8, 5, 4]


def test_merge_does_not_sort_an_individually_unsorted_input():
    """merge 只在各流头部间选择最小值；任何输入失序都会使整体结果也可能失序。"""

    result = list(heapq.merge([3, 1], [2, 4]))

    assert result == [2, 3, 1, 4]
    assert result != sorted(result)


def test_merge_can_lazily_prefix_unbounded_sorted_iterables():
    """merge 不预先装载全部数据，因此可配合 islice 消费无限有序流的有限前缀。"""

    even_numbers = count(0, 2)
    odd_numbers = count(1, 2)

    assert list(islice(heapq.merge(even_numbers, odd_numbers), 8)) == list(range(8))


def test_nlargest_and_nsmallest_select_records_with_a_key_and_keep_tie_order():
    """选择函数返回已排序 list；等 key 结果与稳定 sorted 切片保持相对输入顺序。"""

    records = [
        {"name": "alpha", "score": 10},
        {"name": "beta", "score": 4},
        {"name": "gamma", "score": 10},
        {"name": "delta", "score": 2},
    ]
    by_score = lambda record: record["score"]

    largest = heapq.nlargest(2, records, key=by_score)
    smallest = heapq.nsmallest(2, records, key=by_score)

    assert [record["name"] for record in largest] == ["alpha", "gamma"]
    assert [record["name"] for record in smallest] == ["delta", "beta"]


@pytest.mark.parametrize("selector", [heapq.nlargest, heapq.nsmallest])
def test_selection_size_boundaries_return_new_lists_without_padding(selector):
    """n<=0 返回空 list；n 超过输入长度时只返回全部现有元素，不补 sentinel。"""

    values = [3, 1, 2]

    assert selector(0, values) == []
    assert selector(-1, values) == []
    assert sorted(selector(10, values)) == [1, 2, 3]
    assert selector(1, []) == []
