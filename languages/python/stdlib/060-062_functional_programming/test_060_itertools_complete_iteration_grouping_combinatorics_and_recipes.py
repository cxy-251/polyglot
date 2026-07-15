"""060｜``itertools`` 无限流、累计计算与惰性串联。

itertools 返回单次消费的 iterator；无限工具必须由 islice 等边界截断。cycle 会缓存
首轮输入，repeat 重复的是同一对象引用而不是副本。accumulate 保留每一步状态，
chain 则按顺序惰性进入各输入，适合构造不产生中间列表的 iterator pipeline。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.itertools.iterator-algebra python.itertools.lazy-consumption
# polyglot-covers: python.itertools.count python.itertools.count-step
# polyglot-covers: python.itertools.count-float-drift python.itertools.infinite-boundary
# polyglot-covers: python.itertools.cycle python.itertools.cycle-cache
# polyglot-covers: python.itertools.repeat python.itertools.repeat-same-object
# polyglot-covers: python.itertools.repeat-map-constant
# polyglot-covers: python.itertools.accumulate python.itertools.accumulate-initial
# polyglot-covers: python.itertools.accumulate-custom-function python.itertools.running-state
# polyglot-covers: python.itertools.chain python.itertools.chain-lazy-order
# polyglot-covers: python.itertools.chain.from_iterable python.itertools.flatten-one-level
# polyglot-covers: python.itertools.compress python.itertools.shortest-input-termination




from fractions import Fraction
from itertools import accumulate, chain, compress, count, cycle, islice, repeat
from operator import mul
import pytest
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
from collections import deque
from itertools import (
    chain,
    combinations,
    combinations_with_replacement,
    filterfalse,
    islice,
    permutations,
    product,
    zip_longest,
)
from math import comb, factorial, perm

def test_itertools_objects_are_lazy_single_pass_iterators():
    """构造 pipeline 不消费源；iterator.__iter__ 返回自身，消费过的元素不会自动重放。"""

    events = []

    def source():
        for value in [1, 2, 3]:
            events.append(value)
            yield value

    iterator = chain(source(), [4])

    assert events == []
    assert iter(iterator) is iterator
    assert next(iterator) == 1
    assert events == [1]
    assert list(iterator) == [2, 3, 4]
    assert list(iterator) == []


def test_count_generates_an_arithmetic_progression_and_must_be_bounded():
    """count 本身没有终点；用 islice 明确限定消费数量，避免 list(count()) 永不返回。"""

    values = list(islice(count(start=10, step=3), 5))

    assert values == [10, 13, 16, 19, 22]


def test_count_supports_exact_non_integer_numeric_steps():
    """start/step 不限于 int；Fraction 可避免浮点反复相加的累计误差。"""

    values = list(islice(count(Fraction(1, 3), Fraction(1, 6)), 5))

    assert values == [
        Fraction(1, 3),
        Fraction(1, 2),
        Fraction(2, 3),
        Fraction(5, 6),
        Fraction(1, 1),
    ]


def test_float_count_is_compared_approximately_and_has_a_formula_alternative():
    """浮点 count 反复执行 n += step；长序列可改用 start + step*i 降低累计漂移。"""

    additive = list(islice(count(0.0, 0.1), 11))
    multiplicative = [0.0 + 0.1 * index for index in range(11)]

    assert additive[-1] == pytest.approx(1.0)
    assert multiplicative[-1] == 1.0
    assert len(additive) == len(multiplicative) == 11


def test_cycle_streams_the_first_pass_then_reuses_its_saved_copy():
    """cycle 首轮一边读取一边缓存；源耗尽后只访问缓存，不会重新调用源生成器。"""

    events = []

    def source():
        for value in ["A", "B"]:
            events.append(value)
            yield value

    iterator = cycle(source())

    assert events == []
    assert next(iterator) == "A"
    assert events == ["A"]
    assert next(iterator) == "B"
    assert list(islice(iterator, 4)) == ["A", "B", "A", "B"]
    assert events == ["A", "B"]


def test_cycle_of_an_empty_iterable_is_empty_instead_of_infinite():
    """没有任何首轮元素就没有缓存可循环，next 的 default 会立即返回。"""

    assert next(cycle([]), "empty") == "empty"


def test_repeat_yields_the_same_object_reference_not_copies():
    """repeat(object) 复用引用；修改可变对象后，所有已经取出的“副本”都会看到变化。"""

    shared = []
    copies = list(repeat(shared, 3))
    copies[0].append("visible everywhere")

    assert all(item is shared for item in copies)
    assert copies == [["visible everywhere"]] * 3


@pytest.mark.parametrize("times", [0, -1, -100])
def test_nonpositive_repeat_count_produces_an_empty_iterator(times):
    """有限 repeat 的 times 不为正时没有输出，不会为负数抛特殊异常。"""

    assert list(repeat("value", times)) == []


def test_repeat_supplies_a_constant_argument_to_map():
    """map 按最短输入停止；repeat(2) 可在不建立常量列表的情况下提供平方指数。"""

    assert list(map(pow, range(6), repeat(2))) == [0, 1, 4, 9, 16, 25]


def test_accumulate_returns_every_running_total_not_only_the_final_reduction():
    """与 reduce 只返回最终值不同，accumulate 暴露每个中间累计状态。"""

    assert list(accumulate([1, 2, 3, 4, 5])) == [1, 3, 6, 10, 15]


def test_accumulate_initial_adds_one_output_before_the_input():
    """initial 会先原样产出，因此非空输入的输出长度多一；空输入也会产出 initial。"""

    assert list(accumulate([1, 2, 3], initial=100)) == [100, 101, 103, 106]
    assert list(accumulate([], initial=100)) == [100]
    assert list(accumulate([])) == []


def test_accumulate_accepts_a_custom_binary_transition_function():
    """func(total, element) 定义状态转移，可表示 running product、min/max 或递推式。"""

    data = [3, 4, 6, 2, 1]

    assert list(accumulate(data, mul)) == [3, 12, 72, 144, 144]
    assert list(accumulate(data, max)) == [3, 4, 6, 6, 6]


def test_accumulate_models_a_stateful_cashflow_workflow():
    """当前余额进入下一步计算；输入元素是付款额，而非要与余额直接相加的普通数字。"""

    cashflows = [1_000, -90, -90, -90]
    balances = accumulate(cashflows, lambda balance, payment: balance * 1.05 + payment)

    assert list(balances) == pytest.approx([1_000, 960.0, 918.0, 873.9])


def test_chain_concatenates_inputs_without_nesting_or_copying():
    """chain 逐个耗尽输入，只展开一层 iterable；元素本身若是 list 仍原样保留。"""

    nested_element = [3, 4]
    result = list(chain([1, 2], [nested_element], (), [5]))

    assert result == [1, 2, nested_element, 5]
    assert result[2] is nested_element


def test_chain_enters_later_iterables_only_after_earlier_ones_finish():
    """惰性顺序让后续输入的副作用延迟到真正需要其第一个元素时。"""

    events = []

    def tagged(name, values):
        events.append(f"start:{name}")
        yield from values

    iterator = chain(tagged("first", [1, 2]), tagged("second", [3]))

    assert events == []
    assert [next(iterator), next(iterator)] == [1, 2]
    assert events == ["start:first"]
    assert next(iterator) == 3
    assert events == ["start:first", "start:second"]


def test_chain_from_iterable_flattens_one_lazily_produced_level():
    """from_iterable 接受“iterable 的 iterable”，适合输入组本身也是 generator 的场景。"""

    events = []

    def groups():
        events.append("first group")
        yield [1, 2]
        events.append("second group")
        yield [3, 4]

    flattened = chain.from_iterable(groups())

    assert events == []
    assert next(flattened) == 1
    assert events == ["first group"]
    assert list(flattened) == [2, 3, 4]
    assert events == ["first group", "second group"]


def test_compress_filters_data_by_selector_truthiness():
    """selector 不必是 bool；按普通 truth testing 决定是否保留同位置的数据项。"""

    data = "ABCDEF"
    selectors = [1, 0, "yes", "", [], [1]]

    assert list(compress(data, selectors)) == ["A", "C", "F"]


def test_compress_stops_when_either_input_is_exhausted():
    """compress 与 zip 一样采用最短输入边界，多出的 data 或 selector 都不会单独产生结果。"""

    assert list(compress("ABCDE", [1, 0])) == ["A"]
    assert list(compress("AB", [1, 1, 1, 1])) == ["A", "B"]


# ``itertools`` 选择、分组、切片与迭代器分流。
#
# 这些工具的关键不只是“返回哪些值”，还包括底层 iterator 已经被推进到哪里。
# takewhile 会吃掉首个失败项，groupby 的组 iterator 共享同一输入，tee 用缓冲换取
# 独立消费进度；忽略这些状态语义，常会得到数据无声丢失或内存意外增长。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

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


# ``itertools`` 组合枚举与官方 recipe 组合工作流。
#
# product、permutations 和 combinations 先把有限输入保存为 pool，再惰性产生 tuple；
# 它们按“位置”而非值判断元素是否重复。官方 recipes 展示 iterator algebra 的价值：
# 用少量经过优化的构件组合出 powerset、滑动窗口、分块和保留边界项的前缀拆分。
#
# 这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.itertools.product python.itertools.cartesian-product
# polyglot-covers: python.itertools.product-repeat python.itertools.product-eager-pools
# polyglot-covers: python.itertools.permutations python.itertools.permutation-default-r
# polyglot-covers: python.itertools.combinations python.itertools.combination-order
# polyglot-covers: python.itertools.combinations_with_replacement
# polyglot-covers: python.itertools.position-identity python.itertools.zero-length-selection
# polyglot-covers: python.itertools.invalid-selection-length python.itertools.combinatoric-cardinality
# polyglot-covers: python.itertools.recipe-powerset python.itertools.recipe-sliding-window
# polyglot-covers: python.itertools.recipe-grouper python.itertools.shared-iterator-chunking
# polyglot-covers: python.itertools.recipe-before-and-after python.itertools.preserve-first-failure
# polyglot-covers: python.itertools.recipe-unique-everseen python.itertools.order-preserving-unique




def powerset(iterable):
    """官方 recipe：按子集长度依次返回从空集到全集的所有组合。"""

    pool = list(iterable)
    return chain.from_iterable(combinations(pool, size) for size in range(len(pool) + 1))


def sliding_window(iterable, size):
    """官方 recipe：用定长 deque 保留最近 size 个元素。"""

    iterator = iter(iterable)
    window = deque(islice(iterator, size), maxlen=size)
    if len(window) == size:
        yield tuple(window)
    for value in iterator:
        window.append(value)
        yield tuple(window)


def grouper(iterable, size, *, incomplete="fill", fillvalue=None):
    """官方 recipe：让多个 zip 参数共享同一个 iterator，形成不重叠的固定长度块。"""

    iterators = [iter(iterable)] * size
    if incomplete == "fill":
        return zip_longest(*iterators, fillvalue=fillvalue)
    if incomplete == "strict":
        return zip(*iterators, strict=True)
    if incomplete == "ignore":
        return zip(*iterators)
    raise ValueError("incomplete 必须是 fill、strict 或 ignore")


def before_and_after(predicate, iterable):
    """官方 recipe：与 takewhile 相似，但把首个失败元素保留给 remainder。"""

    iterator = iter(iterable)
    transition = []

    def true_iterator():
        for element in iterator:
            if predicate(element):
                yield element
            else:
                transition.append(element)
                return

    def remainder_iterator():
        yield from transition
        yield from iterator

    return true_iterator(), remainder_iterator()


def unique_everseen(iterable, key=None):
    """官方 recipe：保存所有已经出现过的 hashable key，同时保留首次出现顺序。"""

    seen = set()
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen.add(element)
            yield element
    else:
        for element in iterable:
            marker = key(element)
            if marker not in seen:
                seen.add(marker)
                yield element


def test_product_matches_nested_loop_order():
    """最右侧 pool 像里程表最低位一样最快变化；排序输入会产生 lexicographic tuple 顺序。"""

    result = list(product("AB", "xy"))
    nested = [(left, right) for left in "AB" for right in "xy"]

    assert result == [("A", "x"), ("A", "y"), ("B", "x"), ("B", "y")]
    assert result == nested


def test_product_repeat_reuses_the_same_input_pool_dimension():
    """repeat=n 等价于把相同输入参数写 n 次，常用于状态位或配置矩阵。"""

    assert list(product([0, 1], repeat=3)) == [
        (0, 0, 0),
        (0, 0, 1),
        (0, 1, 0),
        (0, 1, 1),
        (1, 0, 0),
        (1, 0, 1),
        (1, 1, 0),
        (1, 1, 1),
    ]


def test_product_consumes_each_input_into_a_finite_pool_at_construction():
    """product 的结果虽惰性，但输入 pool 会先完整保存；无限输入因此不适用。"""

    events = []

    def source():
        for value in range(3):
            events.append(value)
            yield value

    iterator = product(source(), ["x", "y"])

    assert events == [0, 1, 2]
    assert next(iterator) == (0, "x")


def test_product_empty_dimension_and_zero_dimensions_have_different_meanings():
    """任一 pool 为空则没有组合；完全没有维度时，数学上的空 Cartesian product 含一个空 tuple。"""

    assert list(product([1, 2], [])) == []
    assert list(product()) == [()]
    assert list(product("AB", repeat=0)) == [()]


def test_permutations_defaults_to_full_length_and_supports_shorter_r():
    """省略 r 会排列全部元素；指定 r 只产生长度 r 且不重复使用同一输入位置的排列。"""

    assert list(permutations("ABC")) == [
        ("A", "B", "C"),
        ("A", "C", "B"),
        ("B", "A", "C"),
        ("B", "C", "A"),
        ("C", "A", "B"),
        ("C", "B", "A"),
    ]
    assert list(permutations("ABC", 2))[:3] == [("A", "B"), ("A", "C"), ("B", "A")]


def test_combinations_preserve_input_position_order():
    """组合只选择位置递增的 subsequence，不生成 BA 这类同一选择的另一排列。"""

    assert list(combinations("ABCD", 2)) == [
        ("A", "B"),
        ("A", "C"),
        ("A", "D"),
        ("B", "C"),
        ("B", "D"),
        ("C", "D"),
    ]


def test_combinations_with_replacement_allows_reusing_a_position():
    """replacement 版本允许 AA/BB，同时仍保持输入位置不下降的顺序。"""

    assert list(combinations_with_replacement("ABC", 2)) == [
        ("A", "A"),
        ("A", "B"),
        ("A", "C"),
        ("B", "B"),
        ("B", "C"),
        ("C", "C"),
    ]


def test_uniqueness_is_based_on_input_position_not_equal_value():
    """两个 'A' 位于不同位置，算法视为不同选择，所以相等的输出 tuple 可能重复。"""

    assert list(permutations("AAB", 2)) == [
        ("A", "A"),
        ("A", "B"),
        ("A", "A"),
        ("A", "B"),
        ("B", "A"),
        ("B", "A"),
    ]
    assert list(combinations("AAB", 2)) == [("A", "A"), ("A", "B"), ("A", "B")]


def test_zero_length_selection_has_one_empty_tuple():
    """选择零个位置只有一种结果：空选择；这与 r 大于 pool 长度的无解情况不同。"""

    assert list(permutations("ABC", 0)) == [()]
    assert list(combinations("ABC", 0)) == [()]
    assert list(combinations_with_replacement("ABC", 0)) == [()]


@pytest.mark.parametrize("function", [permutations, combinations, combinations_with_replacement])
def test_negative_selection_length_raises_value_error(function):
    """r<0 不是空结果而是非法参数；r 超过可选位置时，replacement 与非 replacement 语义不同。"""

    with pytest.raises(ValueError):
        list(function("ABC", -1))


def test_selection_length_beyond_pool_has_documented_empty_cases():
    """permutations/combinations 不能复用位置故返回空；replacement 只要 pool 非空仍能继续选择。"""

    assert list(permutations("AB", 3)) == []
    assert list(combinations("AB", 3)) == []
    assert len(list(combinations_with_replacement("AB", 3))) == 4
    assert list(combinations_with_replacement([], 1)) == []


def test_combinatoric_output_counts_match_closed_form_formulas():
    """完整 materialize 只用于小输入教学；大规模枚举应先用公式估算爆炸性输出数量。"""

    size = 5
    chosen = 3

    assert len(list(product(range(size), repeat=chosen))) == size**chosen
    assert len(list(permutations(range(size), chosen))) == perm(size, chosen)
    assert len(list(permutations(range(size)))) == factorial(size)
    assert len(list(combinations(range(size), chosen))) == comb(size, chosen)
    assert len(list(combinations_with_replacement(range(size), chosen))) == comb(size + chosen - 1, chosen)


def test_product_builds_a_searchable_configuration_matrix():
    """Cartesian product 很适合系统性生成少量正交配置，不必手写嵌套循环。"""

    matrix = list(product(["debug", "release"], ["x86", "arm"], [False, True]))

    assert len(matrix) == 8
    assert ("release", "arm", True) in matrix


def test_powerset_recipe_chains_combinations_of_every_size():
    """输入先保存一次以支持多轮 combinations；输出按子集长度而不是二进制掩码顺序。"""

    assert list(powerset([1, 2, 3])) == [
        (),
        (1,),
        (2,),
        (3,),
        (1, 2),
        (1, 3),
        (2, 3),
        (1, 2, 3),
    ]


def test_sliding_window_recipe_returns_overlapping_fixed_size_tuples():
    """窗口满之前没有输出；之后每推进一个元素，deque 自动丢弃最旧元素。"""

    assert list(sliding_window("ABCDEFG", 4)) == [
        ("A", "B", "C", "D"),
        ("B", "C", "D", "E"),
        ("C", "D", "E", "F"),
        ("D", "E", "F", "G"),
    ]
    assert list(sliding_window([1, 2], 3)) == []


def test_grouper_recipe_supports_fill_ignore_and_strict_incomplete_policies():
    """共享 iterator 每轮被 zip 连续取 n 次；末块策略必须由调用者明确选择。"""

    assert list(grouper("ABCDEFG", 3, fillvalue="x")) == [
        ("A", "B", "C"),
        ("D", "E", "F"),
        ("G", "x", "x"),
    ]
    assert list(grouper("ABCDEFG", 3, incomplete="ignore")) == [
        ("A", "B", "C"),
        ("D", "E", "F"),
    ]
    with pytest.raises(ValueError):
        list(grouper("ABCDEFG", 3, incomplete="strict"))


def test_grouper_rejects_an_unknown_incomplete_policy():
    """策略拼写错误应在构造时立即失败，不能悄悄退回某种数据丢失行为。"""

    with pytest.raises(ValueError, match="fill、strict 或 ignore"):
        grouper([1, 2, 3], 2, incomplete="drop")


def test_before_and_after_recipe_preserves_takewhile_boundary_value():
    """首个 iterator 必须先耗尽，transition 才会保存失败元素供 remainder 从它开始。"""

    before, after = before_and_after(str.isupper, iter("ABCdEf"))

    assert "".join(before) == "ABC"
    assert "".join(after) == "dEf"


def test_unique_everseen_recipe_preserves_first_occurrence_order():
    """set 只负责 membership，不负责输出顺序；生成器按输入流首次出现的位置 yield。"""

    assert list(unique_everseen("AAAABBBCCDAABBB")) == ["A", "B", "C", "D"]
    assert list(unique_everseen("ABBCcAD", key=str.lower)) == ["A", "B", "C", "D"]


def test_unique_everseen_requires_hashable_values_or_hashable_keys():
    """元素本身不可 hash 时会失败；提供 key 可把 list 映射为 hashable tuple 并保留原对象。"""

    values = [[1], [1], [2]]

    with pytest.raises(TypeError):
        list(unique_everseen(values))
    assert list(unique_everseen(values, key=tuple)) == [[1], [2]]
