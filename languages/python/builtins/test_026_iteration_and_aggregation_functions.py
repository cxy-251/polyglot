"""026｜迭代、组合、筛选、排序与聚合类内置函数示例。

本组函数大多接收任意 iterable，其中 iter/next/enumerate/zip/map/filter/reversed
返回一次性惰性 iterator；sorted/min/max/sum/all/any 则消费输入并产生结果。

迭代器协议和生成器控制流已在 008 展示，异步 aiter/anext 已在 015 展示；本文件
聚焦同步内置函数的组合工作流。内容基于 Python 3.10 Built-in Functions；当前
文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.builtin.len python.builtin.iter python.builtin.next
# polyglot-covers: python.builtin.enumerate python.builtin.zip
# polyglot-covers: python.builtin.map python.builtin.filter
# polyglot-covers: python.builtin.reversed python.builtin.sorted
# polyglot-covers: python.builtin.all python.builtin.any
# polyglot-covers: python.builtin.min python.builtin.max python.builtin.sum
# polyglot-covers: python.zip.strict python.iter.callable-sentinel
# polyglot-covers: python.iterator.lazy-single-pass

import pytest


def test_len_requires_a_sized_object_not_merely_an_iterable():
    """len 查询对象声明的大小，不会为了计数而消费一次性 iterator。"""

    source = ["a", "b", "c"]
    iterator = iter(source)

    assert len(source) == 3
    assert len(range(10)) == 10

    with pytest.raises(TypeError):
        len(iterator)

    assert next(iterator) == "a"

    # `__len__` 的返回约束和真假值 fallback 见 001；未知长度的流需在消费时计数。


def test_iter_and_next_expose_single_pass_iteration_and_default():
    """iter 取得 iterator；next 每次推进一项，耗尽后可抛错或返回默认值。"""

    iterator = iter(["first", "second"])

    assert iter(iterator) is iterator
    assert next(iterator) == "first"
    assert next(iterator) == "second"
    assert next(iterator, "finished") == "finished"
    assert next(iterator, "still finished") == "still finished"

    with pytest.raises(StopIteration):
        next(iterator)

    # 默认值只把“耗尽”转换为普通返回；iterator 不会因此重置或重新播放。


def test_two_argument_iter_calls_until_equal_sentinel_without_yielding_it():
    """``iter(callable, sentinel)`` 反复无参数调用，遇到相等值即停止。"""

    responses = iter([b"row-1", b"row-2", b"", b"unused"])
    calls = []

    def read_chunk():
        calls.append("read")
        return next(responses)

    chunks = iter(read_chunk, b"")

    assert list(chunks) == [b"row-1", b"row-2"]
    assert calls == ["read", "read", "read"]
    assert next(responses) == b"unused"

    # sentinel 本身已从数据源读出但不会产出；常见用途是定长 read 直到返回 b""。


def test_callable_iterator_uses_equality_not_object_identity_for_sentinel():
    """每次返回的新对象只要与 sentinel 相等也会终止。"""

    values = iter([[1], [2], []])
    result = list(iter(lambda: next(values), []))

    assert result == [[1], [2]]


def test_enumerate_pairs_lazy_items_with_configurable_integer_indices():
    """enumerate 不复制 iterable，start 只影响计数而不跳过输入。"""

    produced = []

    def names():
        for name in ["alpha", "beta"]:
            produced.append(name)
            yield name

    indexed = enumerate(names(), start=1)

    assert produced == []
    assert next(indexed) == (1, "alpha")
    assert produced == ["alpha"]
    assert list(indexed) == [(2, "beta")]
    assert list(indexed) == []


def test_zip_default_mode_stops_at_shortest_input():
    """普通 zip 静默截断较长输入，这既有用也可能掩盖数据长度错误。"""

    names = ["alice", "bob", "unused"]
    scores = [90, 80]

    paired = zip(names, scores)

    assert list(paired) == [("alice", 90), ("bob", 80)]
    assert list(paired) == []
    assert list(zip()) == []
    assert list(zip([1, 2])) == [(1,), (2,)]


def test_zip_strict_reports_length_mismatch_when_iterator_is_consumed():
    """Python 3.10 strict=True 要求所有输入同时耗尽。"""

    paired = zip(["alice", "bob"], [90], strict=True)

    assert next(paired) == ("alice", 90)

    with pytest.raises(ValueError, match="shorter than argument"):
        next(paired)

    # 构造 zip 时尚未读取输入，因此错误发生在 next/list/for 等消费位置。


def test_zip_can_transpose_rows_and_unzip_pairs():
    """星号解包把每一行作为 zip 的一个输入，可用于规则矩阵转置。"""

    rows = [("alice", 90), ("bob", 80)]
    names, scores = zip(*rows, strict=True)

    assert names == ("alice", "bob")
    assert scores == (90, 80)
    assert list(zip(names, scores, strict=True)) == rows

    # 空 rows 无法直接解包成两个变量；实际流水线应单独定义空输入结果。


def test_map_is_lazy_and_multiple_inputs_stop_at_the_shortest():
    """map 逐组调用函数；默认不会验证输入长度一致。"""

    calls = []

    def multiply(left, right):
        calls.append((left, right))
        return left * right

    products = map(multiply, [2, 3, 4], [10, 20])

    assert calls == []
    assert next(products) == 20
    assert calls == [(2, 10)]
    assert list(products) == [60]
    assert calls == [(2, 10), (3, 20)]
    assert list(products) == []

    assert list(map(pow, [2, 3], [3, 2])) == [8, 9]


def test_filter_none_removes_every_false_value_not_only_none():
    """function=None 时，filter 对每项做普通真假值判断。"""

    values = [None, 0, False, "", [], "ready", 3]

    assert list(filter(None, values)) == ["ready", 3]

    only_not_none = [value for value in values if value is not None]
    assert only_not_none == [0, False, "", [], "ready", 3]

    # 数据清理若只想移除 None，必须写 `is not None`，不能使用 filter(None, ...)。


def test_filter_predicate_is_called_lazily_once_per_examined_item():
    """filter 只在推进时调用 predicate，并跳过 False 项直到找到下一项。"""

    calls = []

    def is_even(number):
        calls.append(number)
        return number % 2 == 0

    evens = filter(is_even, [1, 2, 3, 4])

    assert calls == []
    assert next(evens) == 2
    assert calls == [1, 2]
    assert list(evens) == [4]
    assert calls == [1, 2, 3, 4]


def test_reversed_returns_iterator_and_does_not_modify_source_sequence():
    """reversed 按反向索引惰性读取；它不是 list.reverse()。"""

    source = [1, 2, 3]
    backward = reversed(source)

    assert iter(backward) is backward
    assert next(backward) == 3
    assert list(backward) == [2, 1]
    assert source == [1, 2, 3]

    generator = (number for number in range(3))
    with pytest.raises(TypeError):
        reversed(generator)

    # generator 没有长度/随机索引；若确实要反转流，必须先物化并承担相应内存成本。


def test_reversed_prefers_custom_reversed_protocol():
    """对象可用 ``__reversed__`` 提供比通用索引 fallback 更合适的反向算法。"""

    class History:
        def __iter__(self):
            return iter(["oldest", "newest"])

        def __reversed__(self):
            return iter(["newest", "oldest"])

    history = History()

    assert list(history) == ["oldest", "newest"]
    assert list(reversed(history)) == ["newest", "oldest"]


def test_sorted_consumes_any_iterable_and_leaves_input_unchanged():
    """sorted 总是创建 list；key 提取比较值，reverse 决定方向。"""

    source = ("Banana", "fig", "apple")
    ordered = sorted(source, key=lambda text: (len(text), text.casefold()))

    assert ordered == ["fig", "apple", "Banana"]
    assert source == ("Banana", "fig", "apple")

    descending = sorted((3, 1, 2), reverse=True)
    assert descending == [3, 2, 1]


def test_sorted_is_stable_for_equal_keys():
    """key 相同的记录保留输入相对顺序，适合分阶段排序。"""

    records = [
        {"name": "first", "score": 90},
        {"name": "low", "score": 70},
        {"name": "second", "score": 90},
    ]

    ordered = sorted(records, key=lambda record: record["score"], reverse=True)

    assert [record["name"] for record in ordered] == ["first", "second", "low"]


def test_all_and_any_have_vacuous_empty_results():
    """all 要找第一个假值，any 要找第一个真值；空输入分别没有反例/证例。"""

    assert all([True, 1, "ready"])
    assert not all([True, 0, "ready"])
    assert any([0, "", "ready"])
    assert not any([0, "", None])

    assert all([]) is True
    assert any([]) is False
    assert type(all([1])) is bool
    assert type(any([1])) is bool

    # 与 `and`/`or` 返回操作数不同，all/any 的结果始终是 bool。


def test_all_and_any_short_circuit_without_consuming_remaining_items():
    """决定结果后不会继续请求 iterator，可避免无用工作或副作用。"""

    all_events = []

    def for_all():
        for value in [1, 0, 1]:
            all_events.append(value)
            yield value

    assert all(for_all()) is False
    assert all_events == [1, 0]

    any_events = []

    def for_any():
        for value in [0, "ready", "unused"]:
            any_events.append(value)
            yield value

    assert any(for_any()) is True
    assert any_events == [0, "ready"]


def test_min_and_max_accept_iterable_or_multiple_positional_values():
    """两种调用形式都返回输入中的原对象，而不是 key 的结果。"""

    assert min([3, 1, 2]) == 1
    assert max(3, 1, 2) == 3

    names = ["python", "go", "rust"]
    assert min(names, key=len) == "go"
    assert max(names, key=len) == "python"


def test_min_max_are_stable_and_return_first_item_with_best_key():
    """多个元素拥有相同最优 key 时，保留最先遇到的元素。"""

    first = {"name": "first", "score": 90}
    second = {"name": "second", "score": 90}
    lower = {"name": "lower", "score": 70}
    records = [first, second, lower]

    assert max(records, key=lambda record: record["score"]) is first
    assert min(records, key=lambda record: record["score"]) is lower


def test_min_max_default_only_applies_to_empty_single_iterable_form():
    """default 把空 iterable 转成正常结果，但不能与多位置参数形式混用。"""

    calls = []

    def key(value):
        calls.append(value)
        return value

    assert min([], key=key, default="missing") == "missing"
    assert calls == []

    with pytest.raises(ValueError):
        max([])

    with pytest.raises(TypeError):
        min(3, 1, default=0)

    # 空输入返回 default 时不会把 default 传给 key；它可以与元素类型不同。


def test_sum_uses_start_as_left_seed_for_numeric_aggregation():
    """sum 从 start 开始逐项相加；默认 start 是整数 0。"""

    assert sum([1, 2, 3]) == 6
    assert sum([1, 2, 3], start=10) == 16
    assert sum([], start=10) == 10
    assert sum([True, False, True]) == 2

    # bool 是 int 子类所以可以计数，但业务语义更清楚时可写显式生成表达式。
    flags = [True, False, True]
    assert sum(1 for enabled in flags if enabled) == 2


def test_sum_rejects_text_and_is_a_poor_general_concatenation_tool():
    """str/bytes 被明确拒绝；list 虽可相加，反复复制使 sum 低效。"""

    with pytest.raises(TypeError, match="sum.*strings"):
        sum(["py", "thon"], start="")

    with pytest.raises(TypeError):
        sum([b"py", b"thon"], start=b"")

    assert sum([[1], [2], [3]], start=[]) == [1, 2, 3]
    assert [item for group in [[1], [2], [3]] for item in group] == [1, 2, 3]

    # 文本用 join；一般嵌套 iterable 可用推导式或 itertools.chain，避免二次复制。
