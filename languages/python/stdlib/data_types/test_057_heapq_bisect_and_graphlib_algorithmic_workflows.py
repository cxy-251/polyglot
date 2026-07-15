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
import bisect
from functools import cache
from operator import attrgetter
from graphlib import CycleError, TopologicalSorter

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


# 058｜``bisect`` 有序表搜索、插入边界与 record key 示例。
#
# 二分函数寻找的是插入位置而不是“是否相等”：它只调用 ``__lt__``，并用 left 或
# right 规则把相同值放在切分点的一侧。搜索是 O(log n)，但 ``insort`` 最终调用
# list.insert 移动元素，所以整体插入仍为 O(n)。所有 API 都要求输入范围事先有序。
#
# Python 3.10 新增的 ``key`` 还有一处重要非对称：``bisect_*`` 只对数组元素调用
# key，搜索值 ``x`` 应直接传比较键；``insort_*`` 则会用 ``key(x)`` 搜索，最终仍
# 把完整的 x 对象插入列表。当前文件尚未经过 pytest 验证。

# polyglot-covers: python.bisect.bisect-left python.bisect.bisect-right
# polyglot-covers: python.bisect.bisect-alias python.bisect.partition-invariant
# polyglot-covers: python.bisect.less-than-only python.bisect.no-equality-search
# polyglot-covers: python.bisect.sorted-precondition python.bisect.lo-hi
# polyglot-covers: python.bisect.insort-left python.bisect.insort-right
# polyglot-covers: python.bisect.insort-alias python.bisect.in-place
# polyglot-covers: python.bisect.equal-record-placement python.bisect.key-python310
# polyglot-covers: python.bisect.search-key-not-x python.bisect.insort-key-x
# polyglot-covers: python.bisect.stateless-key python.bisect.cached-key
# polyglot-covers: python.bisect.precomputed-keys python.bisect.parallel-table
# polyglot-covers: python.bisect.range-lookup python.bisect.boundary-recipes
# polyglot-covers: python.bisect.event-schedule python.bisect.insertion-complexity




@dataclass(frozen=True)
class Movie:
    title: str
    released: int


def find_leftmost_equal(values, target):
    """把 insertion point 转成精确查找；相等判断由 recipe 自己完成。"""

    index = bisect.bisect_left(values, target)
    if index != len(values) and values[index] == target:
        return index
    raise ValueError(target)


def find_lt(values, target):
    """寻找严格小于 target 的最右元素。"""

    index = bisect.bisect_left(values, target)
    if index:
        return values[index - 1]
    raise ValueError(target)


def find_le(values, target):
    """寻找小于或等于 target 的最右元素。"""

    index = bisect.bisect_right(values, target)
    if index:
        return values[index - 1]
    raise ValueError(target)


def find_gt(values, target):
    """寻找严格大于 target 的最左元素。"""

    index = bisect.bisect_right(values, target)
    if index != len(values):
        return values[index]
    raise ValueError(target)


def find_ge(values, target):
    """寻找大于或等于 target 的最左元素。"""

    index = bisect.bisect_left(values, target)
    if index != len(values):
        return values[index]
    raise ValueError(target)


def test_left_and_right_choose_opposite_sides_of_equal_values():
    """left 停在第一项相等值之前，right 停在最后一项相等值之后。"""

    values = [1, 2, 2, 2, 4]

    left = bisect.bisect_left(values, 2)
    right = bisect.bisect_right(values, 2)

    assert left == 1
    assert right == 4
    assert all(value < 2 for value in values[:left])
    assert all(value >= 2 for value in values[left:])
    assert all(value <= 2 for value in values[:right])
    assert all(value > 2 for value in values[right:])


def test_bisect_alias_uses_the_right_hand_rule():
    """简写 bisect 等价于 bisect_right，不是 left；重复值场景最容易看出差别。"""

    values = [1, 2, 2, 3]

    assert bisect.bisect(values, 2) == 3
    assert bisect.bisect(values, 2) == bisect.bisect_right(values, 2)


def test_bisection_uses_less_than_without_calling_equality():
    """算法只划分范围，不确认命中；即使 __eq__ 不可用也能返回插入点。"""

    comparisons = []

    class OrderedProbe:
        def __init__(self, value):
            self.value = value

        def __lt__(self, other):
            comparisons.append((self.value, other.value))
            return self.value < other.value

        def __eq__(self, other):
            raise AssertionError("bisect must not test equality")

    values = [OrderedProbe(1), OrderedProbe(3), OrderedProbe(5)]

    assert bisect.bisect_left(values, OrderedProbe(3)) == 1
    assert comparisons


def test_empty_and_outside_values_map_to_valid_insertion_boundaries():
    """插入点范围包含 len(a)：空表和两端都无需特殊 sentinel。"""

    values = [10, 20, 30]

    assert bisect.bisect_left([], 5) == 0
    assert bisect.bisect_left(values, 5) == 0
    assert bisect.bisect_right(values, 30) == len(values)
    assert bisect.bisect_left(values, 99) == len(values)


def test_lo_and_hi_limit_the_considered_sorted_slice():
    """lo/hi 使用半开区间且返回原列表坐标；区间外元素不参与比较。"""

    values = [1, 3, 5, 7, 9]

    assert bisect.bisect_left(values, 6, lo=1, hi=4) == 3
    assert bisect.bisect_right(values, 3, lo=2) == 2

    with pytest.raises(ValueError, match="lo must be non-negative"):
        bisect.bisect_left(values, 3, lo=-1)


def test_bisect_does_not_validate_or_repair_an_unsorted_input():
    """二分只探查少数位置；对失序输入返回的 index 没有全局排序含义。"""

    values = [1, 5, 3, 7]

    index = bisect.bisect_right(values, 4)
    values.insert(index, 4)

    assert values == [1, 5, 3, 4, 7]
    assert values != sorted(values)


def test_manual_insert_and_insort_both_mutate_the_existing_list():
    """bisect 只返回位置；insort 组合搜索和 list.insert，原地修改且返回 None。"""

    manual = [1, 4, 7]
    automatic = [1, 4, 7]

    manual.insert(bisect.bisect_left(manual, 5), 5)
    result = bisect.insort_left(automatic, 5)

    assert manual == [1, 4, 5, 7]
    assert automatic == manual
    assert result is None


def test_insort_left_and_right_place_new_equal_records_on_different_sides():
    """对相等键，left 把新对象放在旧对象前，right 放在旧对象后。"""

    existing = [
        Movie("older-a", 2000),
        Movie("older-b", 2000),
    ]
    left = list(existing)
    right = list(existing)
    newcomer = Movie("new", 2000)
    by_year = attrgetter("released")

    bisect.insort_left(left, newcomer, key=by_year)
    bisect.insort_right(right, newcomer, key=by_year)

    assert [movie.title for movie in left] == ["new", "older-a", "older-b"]
    assert [movie.title for movie in right] == ["older-a", "older-b", "new"]


def test_insort_alias_uses_the_right_hand_insertion_rule():
    """简写 insort 等价于 insort_right，因此新重复项位于现有重复区间之后。"""

    values = [1, 2, 2, 3]

    bisect.insort(values, 2)

    assert values == [1, 2, 2, 2, 3]
    assert bisect.bisect_right(values, 2) == 4


def test_search_key_applies_to_records_but_not_to_search_value():
    """bisect_* 的 x 必须已经是可与 key(record) 比较的键，而不是完整 record。"""

    movies = [
        Movie("The Birds", 1963),
        Movie("Jaws", 1975),
        Movie("Aliens", 1986),
    ]
    by_year = attrgetter("released")

    assert bisect.bisect_left(movies, 1970, key=by_year) == 1
    assert movies[bisect.bisect_right(movies, 1975, key=by_year)].title == "Aliens"

    with pytest.raises(TypeError):
        bisect.bisect_left(movies, Movie("Wrong search shape", 1970), key=by_year)


def test_insort_key_searches_with_key_of_x_but_inserts_the_original_record():
    """insort 内部搜索 key(x)，但 list 中保存的仍是 Movie，而不是 released 整数。"""

    movies = [
        Movie("The Birds", 1963),
        Movie("Jaws", 1975),
        Movie("Aliens", 1986),
    ]
    romance = Movie("Love Story", 1970)

    bisect.insort(movies, romance, key=attrgetter("released"))

    assert movies == [
        Movie("The Birds", 1963),
        Movie("Love Story", 1970),
        Movie("Jaws", 1975),
        Movie("Aliens", 1986),
    ]
    assert all(isinstance(movie, Movie) for movie in movies)


def test_repeated_searches_recompute_stateless_key_results():
    """bisect 不缓存 key(element)；相同搜索再次执行相同二分路径时会重新计算。"""

    movies = [
        Movie("A", 1960),
        Movie("B", 1970),
        Movie("C", 1980),
        Movie("D", 1990),
    ]
    calls = []

    def recorded_year(movie):
        calls.append(movie.title)
        return movie.released

    assert bisect.bisect_left(movies, 1975, key=recorded_year) == 2
    first_call_count = len(calls)
    assert bisect.bisect_left(movies, 1975, key=recorded_year) == 2

    assert first_call_count > 0
    assert len(calls) == first_call_count * 2


def test_cached_key_avoids_recomputing_unchanged_record_keys():
    """不可变且可哈希的 record 可配合 functools.cache 复用昂贵 key 结果。"""

    movies = [Movie("A", 1960), Movie("B", 1970), Movie("C", 1980)]
    calls = []

    @cache
    def cached_year(movie):
        calls.append(movie.title)
        return movie.released

    assert bisect.bisect_left(movies, 1975, key=cached_year) == 2
    calls_after_first_search = list(calls)
    assert bisect.bisect_left(movies, 1975, key=cached_year) == 2

    assert calls_after_first_search
    assert calls == calls_after_first_search


def test_parallel_precomputed_keys_support_search_and_synchronized_insertion():
    """预计算 key 可让搜索只比较标量；插入时必须同步维护 records 和 keys。"""

    movies = [Movie("A", 1960), Movie("C", 1980)]
    years = [movie.released for movie in movies]
    newcomer = Movie("B", 1970)

    index = bisect.bisect_left(years, newcomer.released)
    years.insert(index, newcomer.released)
    movies.insert(index, newcomer)

    assert years == [1960, 1970, 1980]
    assert [movie.title for movie in movies] == ["A", "B", "C"]
    assert years == [movie.released for movie in movies]


def test_bisect_right_implements_numeric_bucket_lookup_at_exact_boundaries():
    """right 规则让等于 breakpoint 的分数进入右侧新等级，例如 90 正好为 A。"""

    def grade(score):
        breakpoints = [60, 70, 80, 90]
        grades = "FDCBA"
        return grades[bisect.bisect(breakpoints, score)]

    assert [grade(score) for score in [59, 60, 69, 70, 89, 90, 100]] == [
        "F",
        "D",
        "D",
        "C",
        "B",
        "A",
        "A",
    ]


def test_boundary_search_recipes_convert_insertion_points_to_neighbor_values():
    """left/right 分别构造严格和非严格边界，无需线性扫描有序表。"""

    values = [10, 20, 20, 30]

    assert find_leftmost_equal(values, 20) == 1
    assert find_lt(values, 20) == 10
    assert find_le(values, 20) == 20
    assert find_gt(values, 20) == 30
    assert find_ge(values, 20) == 20
    assert find_ge(values, 21) == 30


@pytest.mark.parametrize(
    ("finder", "target"),
    [
        (find_leftmost_equal, 25),
        (find_lt, 10),
        (find_le, 9),
        (find_gt, 30),
        (find_ge, 31),
    ],
)
def test_boundary_search_recipes_raise_when_no_answer_exists(finder, target):
    """插入点位于端点时先检查边界，避免把 -1 或 len(a) 当作有效结果。"""

    with pytest.raises(ValueError) as error:
        finder([10, 20, 30], target)

    assert error.value.args == (target,)


def test_insort_with_sequence_tie_breaker_maintains_a_stable_event_schedule():
    """时间相同的事件附加唯一序号，既避免比较 payload，也保留提交先后顺序。"""

    schedule = []
    sequence = count()

    def schedule_event(timestamp, payload):
        bisect.insort(schedule, (timestamp, next(sequence), payload))

    schedule_event(20, {"name": "later"})
    schedule_event(10, {"name": "first at ten"})
    schedule_event(10, {"name": "second at ten"})

    assert [entry[2]["name"] for entry in schedule] == [
        "first at ten",
        "second at ten",
        "later",
    ]


def test_insort_search_is_logarithmic_but_list_insertion_still_moves_a_suffix():
    """bisect 降低比较次数，不改变连续 list 中间插入需要移动后缀的 O(n) 成本。"""

    values = list(range(0, 20, 2))
    before = list(values)

    index = bisect.bisect_left(values, 7)
    bisect.insort_left(values, 7)

    assert index == 4
    assert values[:index] == before[:index]
    assert values[index] == 7
    assert values[index + 1 :] == before[index:]


# 067｜``graphlib.TopologicalSorter`` 的依赖方向、批次调度与环检测。
#
# 构造参数采用 ``node -> predecessors``，也就是 value 是必须先完成的节点，而不是
# successor。一次性顺序使用 ``static_order``；并行/分批工作流则显式经历
# ``prepare -> get_ready -> done`` 状态机。``CycleError`` 后仍可处理未被环阻塞的部分。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

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
