"""058｜``bisect`` 有序表搜索、插入边界与 record key 示例。

二分函数寻找的是插入位置而不是“是否相等”：它只调用 ``__lt__``，并用 left 或
right 规则把相同值放在切分点的一侧。搜索是 O(log n)，但 ``insort`` 最终调用
list.insert 移动元素，所以整体插入仍为 O(n)。所有 API 都要求输入范围事先有序。

Python 3.10 新增的 ``key`` 还有一处重要非对称：``bisect_*`` 只对数组元素调用
key，搜索值 ``x`` 应直接传比较键；``insort_*`` 则会用 ``key(x)`` 搜索，最终仍
把完整的 x 对象插入列表。当前文件尚未经过 pytest 验证。
"""

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

import bisect
from dataclasses import dataclass
from functools import cache
from itertools import count
from operator import attrgetter

import pytest


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
