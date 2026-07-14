"""082｜``itertools`` 选择、分组、切片与迭代器分流。

这些工具的关键不只是“返回哪些值”，还包括底层 iterator 已经被推进到哪里。
takewhile 会吃掉首个失败项，groupby 的组 iterator 共享同一输入，tee 用缓冲换取
独立消费进度；忽略这些状态语义，常会得到数据无声丢失或内存意外增长。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.itertools.dropwhile python.itertools.drop-prefix-only
# polyglot-covers: python.itertools.takewhile python.itertools.takewhile-consumes-failure
# polyglot-covers: python.itertools.filterfalse python.itertools.filterfalse-none
# polyglot-covers: python.itertools.groupby python.itertools.groupby-consecutive
# polyglot-covers: python.itertools.groupby-sort-workflow python.itertools.groupby-shared-source
# polyglot-covers: python.itertools.islice python.itertools.islice-no-negative
# polyglot-covers: python.itertools.islice-consumption python.itertools.islice-infinite
# polyglot-covers: python.itertools.pairwise python.itertools.python310-pairwise
# polyglot-covers: python.itertools.starmap python.itertools.argument-unpacking
# polyglot-covers: python.itertools.tee python.itertools.tee-buffering
# polyglot-covers: python.itertools.tee-original-boundary python.itertools.tee-not-threadsafe
# polyglot-covers: python.itertools.zip_longest python.itertools.zip-longest-fill
# polyglot-covers: python.itertools.zip-longest-infinite-boundary

from itertools import (
    count,
    dropwhile,
    filterfalse,
    groupby,
    islice,
    pairwise,
    starmap,
    takewhile,
    tee,
    zip_longest,
)
from operator import itemgetter

import pytest


def test_dropwhile_drops_only_the_initial_true_prefix():
    """predicate 首次为假后不再调用；后面即使再次满足条件也会原样返回。"""

    checked = []

    def below_five(value):
        checked.append(value)
        return value < 5

    result = list(dropwhile(below_five, [1, 4, 6, 4, 1]))

    assert result == [6, 4, 1]
    assert checked == [1, 4, 6]


def test_dropwhile_may_have_a_long_lazy_startup():
    """只构造对象不会扫描前缀；第一次 next 才持续消费，直到找到首个 predicate=False。"""

    checked = []
    iterator = dropwhile(lambda value: checked.append(value) is None, [1, 2, 3])

    assert checked == []
    assert next(iterator, "empty") == "empty"
    assert checked == [1, 2, 3]


def test_takewhile_stops_at_the_first_failure_even_if_later_values_match():
    """takewhile 只描述连续前缀，不等价于 filter；失败后的 4/1 不会重新参加判断。"""

    assert list(takewhile(lambda value: value < 5, [1, 4, 6, 4, 1])) == [1, 4]


def test_takewhile_consumes_and_discards_the_first_failing_item():
    """底层 iterator 已读出失败值才能判断停止；继续读源时从失败值的下一项开始。"""

    source = iter([1, 4, 6, 4, 1])

    assert list(takewhile(lambda value: value < 5, source)) == [1, 4]
    assert list(source) == [4, 1]


def test_filterfalse_returns_items_where_predicate_is_false():
    """它是 filter 的逻辑补集，仍保持源顺序且只按需取值。"""

    assert list(filterfalse(lambda value: value % 2, range(10))) == [0, 2, 4, 6, 8]


def test_filterfalse_none_selects_falsy_items_by_normal_truth_testing():
    """predicate=None 等同使用 bool，保留 0、空容器、None 等 falsy 值。"""

    values = [0, 1, "", "text", [], [1], None, False]

    assert list(filterfalse(None, values)) == [0, "", [], None, False]


def test_groupby_groups_consecutive_runs_not_all_equal_keys_globally():
    """行为类似 Unix uniq 而不是 SQL GROUP BY；同一个 key 离开后再次出现会形成新组。"""

    runs = [(key, "".join(group)) for key, group in groupby("AAAABBBCCDAABBB")]

    assert runs == [
        ("A", "AAAA"),
        ("B", "BBB"),
        ("C", "CC"),
        ("D", "D"),
        ("A", "AA"),
        ("B", "BBB"),
    ]


def test_groupby_sort_workflow_aggregates_all_records_with_the_same_key():
    """若需求是全局聚合，应先按同一个 key 排序，再立即 materialize 每个 group。"""

    records = [
        {"team": "blue", "score": 3},
        {"team": "red", "score": 5},
        {"team": "blue", "score": 7},
        {"team": "red", "score": 11},
    ]
    key = itemgetter("team")
    ordered = sorted(records, key=key)
    totals = {team: sum(row["score"] for row in rows) for team, rows in groupby(ordered, key=key)}

    assert totals == {"blue": 10, "red": 16}


def test_group_iterators_share_the_source_and_expire_when_parent_advances():
    """外层 groupby 前进会越过当前 run；未保存的旧 group 剩余元素随之不可再取。"""

    grouped = groupby("AAABB")
    first_key, first_group = next(grouped)
    assert first_key == "A"
    assert next(first_group) == "A"

    second_key, second_group = next(grouped)

    assert second_key == "B"
    assert list(first_group) == []
    assert list(second_group) == ["B", "B"]


def test_islice_supports_slice_shapes_without_materializing_the_source():
    """stop-only、start/stop 与 step 都对应普通正向 slice，但输出本身仍是 iterator。"""

    assert list(islice("ABCDEFG", 2)) == ["A", "B"]
    assert list(islice("ABCDEFG", 2, 5)) == ["C", "D", "E"]
    assert list(islice("ABCDEFG", 0, None, 2)) == ["A", "C", "E", "G"]


@pytest.mark.parametrize("arguments", [(-1, None), (0, -1), (0, 5, -1), (0, 5, 0)])
def test_islice_rejects_negative_indices_and_nonpositive_steps(arguments):
    """一般 iterator 无法从末尾定位或倒退，所以 islice 不支持序列 slice 的负数能力。"""

    with pytest.raises(ValueError):
        islice(range(10), *arguments)


def test_fully_consumed_islice_advances_source_to_stop_not_last_output():
    """step=3 最后产出索引 9，但完整消费 slice(0,10,3) 后源位置已经到索引 10。"""

    source = iter(range(20))

    assert list(islice(source, 0, 10, 3)) == [0, 3, 6, 9]
    assert next(source) == 10


def test_islice_bounds_an_infinite_iterator():
    """stop=None 可能继续到源耗尽；面对 count 等无限源应给有限 stop 或外层消费上限。"""

    assert list(islice(count(100), 2, 7, 2)) == [102, 104, 106]


def test_pairwise_returns_overlapping_pairs_and_is_empty_for_short_input():
    """3.10 新增 pairwise；相邻窗口共享中间元素，输出数量比输入少一个。"""

    assert list(pairwise("ABCDE")) == [
        ("A", "B"),
        ("B", "C"),
        ("C", "D"),
        ("D", "E"),
    ]
    assert list(pairwise([])) == []
    assert list(pairwise([1])) == []


def test_pairwise_supports_adjacent_difference_workflows():
    """相邻 pair 可直接计算增量，不需要手工维护 previous sentinel。"""

    readings = [10, 13, 12, 20]
    changes = [current - previous for previous, current in pairwise(readings)]

    assert changes == [3, -1, 8]


def test_starmap_unpacks_each_input_item_as_positional_arguments():
    """数据已预先组成参数 tuple 时，starmap(func, rows) 对应逐行调用 func(*row)。"""

    assert list(starmap(pow, [(2, 5), (3, 2), (10, 3)])) == [32, 9, 1000]


def test_starmap_surfaces_argument_shape_errors_at_consumption_time():
    """惰性构造不校验 tuple 长度；真正取到形状错误的行时才由目标函数抛 TypeError。"""

    iterator = starmap(pow, [(2, 3), (4,)])

    assert next(iterator) == 8
    with pytest.raises(TypeError):
        next(iterator)


def test_tee_copies_consumption_positions_not_source_values_eagerly():
    """快分支从源取新值并为慢分支缓存；慢分支追赶时不再次执行源的副作用。"""

    events = []

    def source():
        for value in range(3):
            events.append(value)
            yield value

    fast, slow = tee(source())

    assert events == []
    assert [next(fast), next(fast)] == [0, 1]
    assert events == [0, 1]
    assert next(slow) == 0
    assert events == [0, 1]
    assert list(slow) == [1, 2]
    assert list(fast) == [2]


def test_tee_count_controls_how_many_independent_iterators_are_returned():
    """默认两路；n=0 返回空 tuple，n=1 仍返回只含一个 iterator 的 tuple。"""

    assert tee([1, 2], 0) == ()

    (only,) = tee([1, 2], 1)
    assert list(only) == [1, 2]


def test_tee_original_iterator_should_not_be_used_after_splitting():
    """直接推进原 iterator 不会通知 tee 的分支，导致其观察到的流缺项。"""

    original = iter([1, 2, 3, 4])
    first, second = tee(original)

    assert next(original) == 1
    assert list(first) == [2, 3, 4]
    assert list(second) == [2, 3, 4]


def test_zip_longest_uses_fillvalue_until_the_longest_input_ends():
    """与 zip 的最短边界不同，较短输入耗尽后用 fillvalue 补齐。"""

    result = list(zip_longest("ABCD", "xy", fillvalue="-"))

    assert result == [("A", "x"), ("B", "y"), ("C", "-"), ("D", "-")]
    assert list(zip_longest()) == []


def test_zip_longest_with_an_infinite_input_must_be_bounded_from_outside():
    """只要任一输入无限，zip_longest 也无限；islice 可把教学和生产 pipeline 限定在有限窗口。"""

    rows = zip_longest(count(), ["A", "B"], fillvalue="missing")

    assert list(islice(rows, 4)) == [
        (0, "A"),
        (1, "B"),
        (2, "missing"),
        (3, "missing"),
    ]
