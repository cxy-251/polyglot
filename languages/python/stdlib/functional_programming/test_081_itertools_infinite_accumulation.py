"""081｜``itertools`` 无限流、累计计算与惰性串联。

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
