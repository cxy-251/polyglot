"""017｜赋值目标、容器 display、comprehension 与 ``:=`` 的可执行示例。

赋值语句先完整求值右侧，再从左到右写入 target；链式赋值不会复制对象，starred
target 总是收集成 list。list/tuple/set/dict display 可用 ``*`` / ``**`` 展开，
comprehension 则按嵌套 for/if 的书写顺序惰性地遍历源（结果容器本身立即构建）。
assignment expression ``:=`` 同时返回并绑定一个名称，但不是任意赋值 target 的
替代品。

内容基于 Python 3.10 Assignment / Annotated assignment statements、Assignment
expressions 和 Container displays/comprehensions。
"""

# polyglot-covers: python.statement.assignment python.assignment.chained
# polyglot-covers: python.assignment.unpacking python.assignment.starred-target
# polyglot-covers: python.statement.annotated-assignment
# polyglot-covers: python.expression.list-display python.expression.tuple-display
# polyglot-covers: python.expression.set-display python.expression.dict-display
# polyglot-covers: python.expression.comprehension
# polyglot-covers: python.expression.assignment-expression

import pytest


def test_chained_assignment_evaluates_rhs_once_and_shares_one_object():
    """``first = second = expression`` 只构造一次值，再绑定到多个名称。"""

    events = []

    def build():
        events.append("built")
        return []

    first = second = build()

    assert events == ["built"]
    assert first is second

    first.append("shared")
    assert second == ["shared"]

    # 常见坑：链式赋值不复制可变对象。想要两个独立 list 应分别构造，或显式
    # 根据业务语义 copy；只把 `[]` 写在右侧一次就只有一个对象。


def test_nested_unpacking_and_starred_target_bind_structure():
    """解包 target 可嵌套；一个 starred target 吸收中间剩余项。"""

    name, (major, minor) = ("Python", (3, 10))
    first, *middle, last = range(5)

    assert (name, major, minor) == ("Python", 3, 10)
    assert first == 0
    assert middle == [1, 2, 3]
    assert last == 4


def test_starred_assignment_target_always_collects_a_list():
    """无论右侧是 tuple、range 还是其他 iterable，starred 结果都是 list。"""

    head, *tail = (1, 2, 3)
    *prefix, final = range(3)

    assert head == 1
    assert tail == [2, 3]
    assert type(tail) is list
    assert prefix == [0, 1]
    assert final == 2


def test_unpacking_supports_swap_and_reports_length_mismatches():
    """右侧先打包完成，所以交换不需要临时变量；数量不符则明确失败。"""

    left, right = "left", "right"
    left, right = right, left

    assert (left, right) == ("right", "left")

    def too_few():
        first, second = [1]
        return first, second

    def too_many():
        first, second = [1, 2, 3]
        return first, second

    with pytest.raises(ValueError, match="not enough values to unpack"):
        too_few()

    with pytest.raises(ValueError, match="too many values to unpack"):
        too_many()


def test_overlapping_assignment_targets_are_written_left_to_right():
    """右侧值先固定，随后 target 的写入顺序可能影响后续 target 寻址。"""

    values = [0, 1]
    index = 0

    index, values[index] = 1, 99

    assert index == 1
    assert values == [0, 99]

    # 第二个 target 使用的 index 已被第一个 target 改为 1，所以写入 values[1]，
    # 不是旧位置 values[0]。重叠 target 虽合法，但通常应拆开以减少误读。


def test_assignment_evaluates_rhs_before_target_object_and_subscript():
    """普通赋值先求右侧，再求左侧容器与索引表达式。"""

    events = []
    storage = {}

    def rhs():
        events.append("rhs")
        return "value"

    def target():
        events.append("target")
        return storage

    def key():
        events.append("key")
        return "name"

    target()[key()] = rhs()

    assert events == ["rhs", "target", "key"]
    assert storage == {"name": "value"}


def test_annotated_class_assignment_records_metadata_and_optional_value():
    """类级 annotation 写入 ``__annotations__``；没有右侧时不创建属性值。"""

    class Settings:
        timeout: float
        retries: int = 3
        label: str = "default"

    assert Settings.__annotations__ == {
        "timeout": float,
        "retries": int,
        "label": str,
    }
    assert "timeout" not in Settings.__dict__
    assert Settings.retries == 3
    assert Settings.label == "default"

    with pytest.raises(AttributeError):
        _ = Settings.timeout

    # annotation 是元数据，不会自动构造默认值或执行运行时类型校验。


def test_sequence_and_set_displays_expand_iterables():
    """display 中 ``*iterable`` 把各元素放入新容器。"""

    middle = (2, 3)

    assert [1, *middle, 4] == [1, 2, 3, 4]
    assert (1, *middle, 4) == (1, 2, 3, 4)
    assert {1, *middle, 3} == {1, 2, 3}

    assert type({}) is dict
    assert set() == set()

    # `{}` 永远是空 dict；空 set 没有独立的 display 写法，必须调用 set()。


def test_dict_display_merges_mappings_and_later_values_win():
    """dict display 的重复键采用最后一次写入，不像函数调用那样报重复参数。"""

    defaults = {"mode": "safe", "timeout": 10}
    overrides = {"timeout": 3, "retries": 2}

    combined = {
        **defaults,
        "mode": "explicit",
        **overrides,
        1: "non-string keys are valid here",
    }

    assert combined == {
        "mode": "explicit",
        "timeout": 3,
        "retries": 2,
        1: "non-string keys are valid here",
    }

    # dict 的 **mapping 接受任意可哈希键；调用表达式的 **mapping 则要求所有
    # 键都是 str。两个语法外观相同，契约不同。


def test_dict_display_evaluates_each_key_before_its_value():
    """每个 ``key: value`` 项先求 key，再求对应 value，并按书写顺序处理。"""

    events = []

    def key(number):
        events.append(("key", number))
        return f"k{number}"

    def value(number):
        events.append(("value", number))
        return number * 10

    mapping = {key(1): value(1), key(2): value(2)}

    assert mapping == {"k1": 10, "k2": 20}
    assert events == [
        ("key", 1),
        ("value", 1),
        ("key", 2),
        ("value", 2),
    ]


def test_comprehension_filters_before_evaluating_result_expression():
    """每项先执行 for 绑定和 if filter，只有通过者才计算最左侧结果。"""

    events = []

    def source():
        events.append("source")
        return [1, 2, 3]

    def keep(number):
        events.append(("filter", number))
        return number % 2 == 1

    def transform(number):
        events.append(("result", number))
        return number * 10

    values = [transform(number) for number in source() if keep(number)]

    assert values == [10, 30]
    assert events == [
        "source",
        ("filter", 1),
        ("result", 1),
        ("filter", 2),
        ("filter", 3),
        ("result", 3),
    ]


def test_nested_comprehension_for_clauses_follow_left_to_right_nesting():
    """后一个 for 位于前一个 for 的内部，可使用前面已经绑定的名称。"""

    pairs = [
        (left, right)
        for left in [1, 2]
        for right in range(left, 4)
        if (left + right) % 2 == 0
    ]

    assert pairs == [(1, 1), (1, 3), (2, 2)]

    # 等价于两层普通 for，再在最内层执行 if。条款过多时展开成语句通常更易读。


def test_set_and_dict_comprehensions_build_their_respective_container_types():
    """相同迭代骨架可生成去重 set 或 key/value dict。"""

    residues = {number % 3 for number in range(7)}
    squares = {number: number**2 for number in range(4)}

    assert residues == {0, 1, 2}
    assert squares == {0: 0, 1: 1, 2: 4, 3: 9}
    assert type(residues) is set
    assert type(squares) is dict


def test_dict_comprehension_evaluates_key_before_value_for_each_item():
    """Python 3.10 的 dict comprehension 与 dict display 都先求 key。"""

    events = []

    def make_key(number):
        events.append(("key", number))
        return f"k{number}"

    def make_value(number):
        events.append(("value", number))
        return number * 10

    mapping = {make_key(number): make_value(number) for number in [1, 2]}

    assert mapping == {"k1": 10, "k2": 20}
    assert events == [
        ("key", 1),
        ("value", 1),
        ("key", 2),
        ("value", 2),
    ]


def test_assignment_expression_returns_value_and_binds_a_name():
    """``:=`` 让同一个计算结果既参与当前表达式，也保存供后续使用。"""

    values = [1, 2, 3]

    if (length := len(values)) > 2:
        message = f"long:{length}"
    else:
        message = f"short:{length}"

    assert length == 3
    assert message == "long:3"

    # 适合避免在条件和 suite 中重复昂贵计算；若绑定名称在很远处才使用，普通
    # 赋值语句通常更清楚。


def test_assignment_expression_precedence_can_capture_comparison_or_operand():
    """``:=`` 优先级低于比较；括号位置可决定保存完整布尔结果还是某个操作数。"""

    result = (comparison := 1 < 2)
    fallback_result = (captured_empty := "") or "fallback"
    captured_result = (captured_whole := ("" or "fallback"))

    assert result is True
    assert comparison is True
    assert fallback_result == "fallback"
    assert captured_empty == ""
    assert captured_result == "fallback"
    assert captured_whole == "fallback"


def test_top_level_assignment_expression_requires_parentheses():
    """作为独立 expression statement 时，海象运算符必须用括号消除歧义。"""

    with pytest.raises(SyntaxError):
        compile("value := 1", "<walrus-statement>", "exec")

    namespace = {}
    exec(compile("(value := 1)", "<walrus-parenthesized>", "exec"), namespace)
    assert namespace["value"] == 1


def test_assignment_expression_target_must_be_one_plain_name():
    """``:=`` 不能直接写属性、下标或解包 target。"""

    invalid_sources = [
        "(obj.value := 1)",
        "(items[0] := 1)",
        "((left, right) := (1, 2))",
    ]

    for source in invalid_sources:
        with pytest.raises(SyntaxError):
            compile(source, "<invalid-walrus-target>", "exec")

    # 需要这些 target 时应使用普通 assignment statement；walrus 的限制让表达式
    # 内副作用保持在一个可见名称上。


def test_walrus_inside_comprehension_binds_in_surrounding_scope():
    """comprehension 自有循环作用域，但 ``:=`` target 特意绑定到外围作用域。"""

    square = None
    selected = [square for number in range(4) if (square := number**2) > 2]

    assert selected == [4, 9]
    assert square == 9

    # 常见坑：循环变量 number 不泄漏，但 square 会保留最后一次 filter 求值 9。
    # 若不希望外围状态改变，应改用普通 comprehension 表达式或独立循环。


def test_walrus_cannot_rebind_a_comprehension_iteration_variable():
    """同一 comprehension 中不能让 ``:=`` 与 for target 争夺同一名称。"""

    source = "[number := number + 1 for number in range(3)]"

    with pytest.raises(SyntaxError, match="cannot rebind comprehension iteration variable"):
        compile(source, "<walrus-rebind>", "eval")


def test_walrus_is_forbidden_in_comprehension_iterable_expression():
    """comprehension 的 ``in iterable`` 部分禁止 assignment expression。"""

    source = "[number for number in (values := range(3))]"

    with pytest.raises(SyntaxError, match="comprehension iterable expression"):
        compile(source, "<walrus-iterable>", "eval")
