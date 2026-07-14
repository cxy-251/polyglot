"""083｜``itertools`` 组合枚举与官方 recipe 组合工作流。

product、permutations 和 combinations 先把有限输入保存为 pool，再惰性产生 tuple；
它们按“位置”而非值判断元素是否重复。官方 recipes 展示 iterator algebra 的价值：
用少量经过优化的构件组合出 powerset、滑动窗口、分块和保留边界项的前缀拆分。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

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

import pytest


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
