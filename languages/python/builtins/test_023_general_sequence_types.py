"""023｜``list``、``tuple`` 与 ``range`` 通用序列和差异化语义示例。

三者都支持索引、切片、成员判断、index/count 等序列操作，但用途不同：list 是
可变工作集合，tuple 是固定位置的不可变序列，range 是惰性表示的整数等差数列。

订阅/切片协议、赋值目标与解包语法已在 005、017 展示；本文件聚焦内置序列类型
自身。内容基于 Python 3.10 Sequence Types、Mutable Sequence Types、Lists、
Tuples 和 Ranges；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.type.list python.type.tuple python.type.range
# polyglot-covers: python.builtin.list python.builtin.tuple python.builtin.range
# polyglot-covers: python.sequence.common-operations python.sequence.lexicographic
# polyglot-covers: python.list.slice-assignment python.list.mutating-methods
# polyglot-covers: python.list.copy python.list.sort python.list.aliasing
# polyglot-covers: python.tuple.packing python.tuple.hashability
# polyglot-covers: python.range.parameters python.range.slicing
# polyglot-covers: python.range.equality python.range.large-length

import sys

import pytest


def test_list_and_tuple_construct_from_any_iterable():
    """构造器会消费 iterable，并把当时产生的元素保存为具体序列。"""

    squares = (number * number for number in range(4))
    as_list = list(squares)

    assert as_list == [0, 1, 4, 9]
    assert list(squares) == []
    assert tuple(as_list) == (0, 1, 4, 9)
    assert list("abc") == ["a", "b", "c"]
    assert list() == []
    assert tuple() == ()

    # generator 是一次性 iterator；第一次构造 list 后已经耗尽，第二次不会重放。


def test_common_sequence_operations_share_index_slice_and_search_rules():
    """list/tuple 的通用操作返回相应序列类型，并按相等关系查找元素。"""

    items = ["a", "b", "a", "c"]
    fixed = tuple(items)

    assert items[1] == fixed[1] == "b"
    assert items[-1] == fixed[-1] == "c"
    assert items[1:3] == ["b", "a"]
    assert fixed[1:3] == ("b", "a")
    assert "b" in items and "missing" not in fixed
    assert items.index("a", 1) == 2
    assert fixed.count("a") == 2

    with pytest.raises(ValueError):
        items.index("missing")


def test_concatenation_and_repetition_create_new_sequence_values():
    """连接要求相同序列家族；重复次数小于等于零产生空序列。"""

    left = [1, 2]
    combined = left + [3]

    assert combined == [1, 2, 3]
    assert left == [1, 2]
    assert ("a",) * 3 == ("a", "a", "a")
    assert [1, 2] * 0 == []
    assert [1, 2] * -2 == []

    with pytest.raises(TypeError):
        [1, 2] + (3,)

    # 反复 `result = result + chunk` 会持续复制旧内容；大量拼接应按类型选择
    # list.extend、str.join 或 bytearray.extend。


def test_sequence_comparison_is_lexicographic_for_compatible_types():
    """逐项比较在首个不同元素处决定结果，公共前缀相同时较短者更小。"""

    assert [1, 2, 9] < [1, 3, 0]
    assert [1, 2] < [1, 2, 0]
    assert ("a", "z") > ("a", "b")
    assert [1, 2] != (1, 2)

    with pytest.raises(TypeError):
        [1, 2] < (1, 2)

    # equality 对不同序列类型通常直接为 False；大小排序则不会擅自统一 list/tuple。


def test_list_index_and_slice_assignment_can_replace_or_resize_regions():
    """单索引替换一个槽位，普通切片可以用任意长度 iterable 替换。"""

    values = [0, 1, 2, 3, 4]
    values[0] = 10
    values[1:3] = [11, 12, 13]

    assert values == [10, 11, 12, 13, 3, 4]

    values[2:5] = []
    assert values == [10, 11, 4]

    # 切片赋空 iterable 等价于删除范围；右侧会先转成适合赋值的元素序列。


def test_extended_slice_assignment_requires_exactly_matching_length():
    """步长不为 1 的切片固定了目标槽位数，不能借赋值调整列表长度。"""

    values = [0, 1, 2, 3, 4, 5]
    values[::2] = [10, 20, 30]

    assert values == [10, 1, 20, 3, 30, 5]

    with pytest.raises(ValueError, match="extended slice"):
        values[::2] = [1, 2]

    del values[1::2]
    assert values == [10, 20, 30]


def test_append_extend_and_insert_have_different_input_shapes():
    """append 添加一个对象，extend 逐项消费 iterable，insert 在位置前插入。"""

    appended = [1]
    appended.append([2, 3])
    assert appended == [1, [2, 3]]

    extended = [1]
    extended.extend([2, 3])
    extended.extend("45")
    assert extended == [1, 2, 3, "4", "5"]

    extended.insert(1, "inserted")
    assert extended == [1, "inserted", 2, 3, "4", "5"]

    # extend("45") 添加两个字符而不是字符串整体；需要整体元素时使用 append。


def test_remove_pop_and_clear_expose_distinct_removal_intents():
    """remove 按首个相等值删除，pop 按位置删除并返回元素，clear 删除全部。"""

    values = ["a", "b", "a", "c"]
    values.remove("a")
    assert values == ["b", "a", "c"]

    assert values.pop() == "c"
    assert values.pop(0) == "b"
    assert values == ["a"]

    with pytest.raises(ValueError):
        values.remove("missing")

    values.clear()
    assert values == []

    with pytest.raises(IndexError):
        values.pop()


def test_reverse_and_other_in_place_methods_return_none():
    """可变序列的原地方法用 None 防止把“结果”误认为新列表。"""

    values = [1, 2, 3]
    returned = values.reverse()

    assert returned is None
    assert values == [3, 2, 1]

    # `values = values.reverse()` 会把变量绑定为 None；sort() 也遵守同一约定。


def test_list_copy_and_slice_are_shallow_copies():
    """外层列表独立，内部可变元素仍由原列表和副本共同引用。"""

    original = [["shared"], ["other"]]
    copied = original.copy()
    sliced = original[:]

    assert copied == original == sliced
    assert copied is not original and sliced is not original
    assert copied[0] is original[0]

    copied.append(["new outer item"])
    copied[0].append("changed through nested alias")

    assert len(original) == 2
    assert original[0] == ["shared", "changed through nested alias"]

    # 需要递归隔离时使用 copy.deepcopy，并先确认对象图/资源是否适合深拷贝。


def test_list_sort_uses_key_reverse_and_stable_order_in_place():
    """key 提取排序依据；相同 key 的元素保持原相对顺序。"""

    records = [
        {"name": "first-high", "score": 90},
        {"name": "low", "score": 70},
        {"name": "second-high", "score": 90},
    ]

    returned = records.sort(key=lambda record: record["score"], reverse=True)

    assert returned is None
    assert [record["name"] for record in records] == [
        "first-high",
        "second-high",
        "low",
    ]

    # 稳定性允许先按次要字段排，再按主要字段排；相同主要 key 不会打乱旧次序。


def test_sorted_returns_a_new_list_and_accepts_non_list_iterables():
    """需要保留原序列或输入不是 list 时，sorted 返回新的 list。"""

    original = ("pear", "fig", "banana")
    ordered = sorted(original, key=len)

    assert ordered == ["fig", "pear", "banana"]
    assert original == ("pear", "fig", "banana")


def test_repeating_a_nested_mutable_value_reuses_the_same_reference():
    """序列乘法复制引用，不会为每个位置重新构造嵌套对象。"""

    aliased = [[0] * 3] * 2
    aliased[0][0] = 1

    assert aliased == [[1, 0, 0], [1, 0, 0]]
    assert aliased[0] is aliased[1]

    independent = [[0] * 3 for _ in range(2)]
    independent[0][0] = 1

    assert independent == [[1, 0, 0], [0, 0, 0]]
    assert independent[0] is not independent[1]


def test_mutating_a_list_while_iterating_can_skip_elements():
    """iterator 的位置继续前进，而删除会把后续元素向左移动。"""

    unsafe = [1, 2, 2, 3]
    for value in unsafe:
        if value == 2:
            unsafe.remove(value)

    assert unsafe == [1, 2, 3]

    safe = [value for value in [1, 2, 2, 3] if value != 2]
    assert safe == [1, 3]

    # 过滤时构造新列表最清楚；确需原地改写可最后做 `values[:] = filtered`。


def test_tuple_is_created_by_commas_and_supports_packing():
    """逗号形成 tuple；括号主要用于分组和消除语法歧义。"""

    packed = 1, 2, 3
    single = ("only",)
    grouped = ("not a tuple")

    assert packed == (1, 2, 3)
    assert single == tuple(["only"])
    assert type(single) is tuple
    assert type(grouped) is str
    assert () == tuple()

    # 单元素 tuple 必须有尾逗号；`("only")` 只是带括号的 str 表达式。


def test_tuple_slots_are_immutable_but_can_reference_mutable_objects():
    """不能重新绑定 tuple 槽位，不代表槽位引用的对象不可改变。"""

    inner = [1]
    record = ("items", inner)

    with pytest.raises(TypeError):
        record[1] = [2]

    inner.append(2)
    assert record == ("items", [1, 2])

    # 不变的是 tuple 保存的两个引用；其中 list 自己的状态仍可变化。


def test_sequence_hashability_requires_an_immutable_hashable_object_graph():
    """list 永远不可 hash；tuple 只有所有元素可 hash 时才可 hash。"""

    immutable_record = ("name", 3)
    mutable_record = ("name", [3])

    assert {immutable_record: "value"}[immutable_record] == "value"

    with pytest.raises(TypeError):
        hash(["name", 3])

    with pytest.raises(TypeError):
        hash(mutable_record)


def test_range_parameters_describe_a_half_open_arithmetic_progression():
    """stop 不包含在结果中，step 可为负但不能为零。"""

    default = range(5)
    stepped = range(2, 10, 3)
    descending = range(5, 0, -2)

    assert list(default) == [0, 1, 2, 3, 4]
    assert list(stepped) == [2, 5, 8]
    assert (stepped.start, stepped.stop, stepped.step) == (2, 10, 3)
    assert list(descending) == [5, 3, 1]
    assert list(range(2, 2)) == []

    with pytest.raises(ValueError, match="must not be zero"):
        range(0, 10, 0)


def test_range_supports_index_count_membership_and_range_slices():
    """range 实现序列接口而不先物化全部整数。"""

    values = range(0, 20, 3)

    assert values[0] == 0
    assert values[-1] == 18
    assert 9 in values
    assert 10 not in values
    assert values.index(9) == 3
    assert values.count(9) == 1
    assert values.count(10) == 0

    sliced = range(0, 20, 2)[2:5]
    assert type(sliced) is range
    assert sliced == range(4, 10, 2)
    assert range(5)[::-1] == range(4, -1, -1)


def test_range_equality_and_hash_depend_on_represented_sequence():
    """参数三元组不同，只要表示同一串整数，range 就相等。"""

    left = range(0, 3, 2)
    right = range(0, 4, 2)

    assert list(left) == list(right) == [0, 2]
    assert left == right
    assert hash(left) == hash(right)
    assert range(0) == range(2, 1, 3)

    # 若需要保存用户原始参数，应单独保存 start/stop/step，不能只依赖 range equality。


def test_range_can_represent_more_items_than_len_can_return():
    """range 参数使用任意精度整数，但 len 受 Py_ssize_t 可表示范围约束。"""

    huge = range(sys.maxsize + 2)

    assert huge[sys.maxsize + 1] == sys.maxsize + 1
    assert sys.maxsize + 1 in huge

    with pytest.raises(OverflowError):
        len(huge)

    # range 本身仍是小型惰性描述；失败的是把元素数量压入平台长度返回类型。


def test_range_does_not_support_concatenation_or_repetition():
    """连接或重复通常不再是单一等差数列，所以 range 明确拒绝。"""

    with pytest.raises(TypeError):
        range(3) + range(3, 6)

    with pytest.raises(TypeError):
        range(3) * 2

    assert list(range(3)) + list(range(3, 6)) == [0, 1, 2, 3, 4, 5]
