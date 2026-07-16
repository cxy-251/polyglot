"""062｜``operator`` 运算符函数与协议分派。

operator.add(x, y) 与 x + y 走同一数据模型协议，包括 NotImplemented、反射方法和
非 bool 的 rich comparison 返回值。函数形态适合 map/reduce/sorted 等高阶 API；
没有双下划线的名字更清晰，保留双下划线别名主要用于向后兼容。

这些案例面向 Python 3.10。
"""

# polyglot-covers: python.operator.rich-comparison python.operator.comparison-non-bool
# polyglot-covers: python.operator.comparison-reflected-fallback
# polyglot-covers: python.operator.truth python.operator.not_
# polyglot-covers: python.operator.is_ python.operator.is_not
# polyglot-covers: python.operator.abs python.operator.unary-arithmetic
# polyglot-covers: python.operator.add python.operator.binary-arithmetic
# polyglot-covers: python.operator.bitwise-functions python.operator.shift-functions
# polyglot-covers: python.operator.matmul python.operator.matmul-protocol
# polyglot-covers: python.operator.index python.operator.python310-exact-int-index
# polyglot-covers: python.operator.invert python.operator.inv-alias
# polyglot-covers: python.operator.concat python.operator.sequence-concat
# polyglot-covers: python.operator.contains python.operator.contains-operand-order
# polyglot-covers: python.operator.countOf python.operator.indexOf
# polyglot-covers: python.operator.dunder-aliases python.operator.higher-order-usage




from functools import reduce
import operator
import pytest
from types import SimpleNamespace

class ComparisonToken:
    """故意不定义 truth protocol，作为 rich comparison 的非 bool 结果。"""


class RichValue:
    def __init__(self, token):
        self.token = token

    def __lt__(self, other):
        return self.token


def test_rich_comparison_functions_return_the_protocol_result_unchanged():
    """lt/le/eq 等不强制 bool；数组库等类型可以返回逐元素 comparison object。"""

    token = ComparisonToken()
    result = operator.lt(RichValue(token), object())

    assert result is token


def test_rich_comparison_function_mapping_matches_syntax_for_plain_values():
    """六个函数可作为参数传递，同时保持各自 <、<=、==、!=、>=、> 的语义。"""

    comparisons = [
        (operator.lt, 1, 2, True),
        (operator.le, 2, 2, True),
        (operator.eq, 2, 2, True),
        (operator.ne, 2, 3, True),
        (operator.ge, 3, 2, True),
        (operator.gt, 3, 2, True),
    ]

    for function, left, right, expected in comparisons:
        assert function(left, right) is expected


def test_comparison_functions_follow_reflected_notimplemented_fallback():
    """a < b 在 a.__lt__ 返回 NotImplemented 后尝试 b.__gt__(a)，operator.lt 也一样。"""

    events = []

    class Left:
        def __lt__(self, other):
            events.append("left.__lt__")
            return NotImplemented

    class Right:
        def __gt__(self, other):
            events.append("right.__gt__")
            return "reflected result"

    assert operator.lt(Left(), Right()) == "reflected result"
    assert events == ["left.__lt__", "right.__gt__"]


def test_truth_and_not_delegate_to_bool_and_its_protocols():
    """Python 没有 __not__ special method；not_ 由解释器基于 __bool__/__len__ 取反。"""

    calls = []

    class Flag:
        def __bool__(self):
            calls.append("__bool__")
            return False

    flag = Flag()

    assert operator.truth(flag) is False
    assert operator.not_(flag) is True
    assert calls == ["__bool__", "__bool__"]


def test_identity_functions_do_not_call_equality():
    """is_/is_not 比较对象 identity；两个内容相等的独立容器仍不是同一对象。"""

    first = [1, 2]
    equal_but_distinct = [1, 2]

    assert operator.eq(first, equal_but_distinct) is True
    assert operator.is_(first, equal_but_distinct) is False
    assert operator.is_not(first, equal_but_distinct) is True
    assert operator.is_(first, first) is True


@pytest.mark.parametrize(
    ("function", "arguments", "expected"),
    [
        (operator.abs, (-7,), 7),
        (operator.neg, (7,), -7),
        (operator.pos, (-7,), -7),
        (operator.add, (7, 3), 10),
        (operator.sub, (7, 3), 4),
        (operator.mul, (7, 3), 21),
        (operator.truediv, (7, 2), 3.5),
        (operator.floordiv, (7, 2), 3),
        (operator.mod, (7, 3), 1),
        (operator.pow, (2, 5), 32),
    ],
)
def test_arithmetic_function_family_matches_intrinsic_operators(function, arguments, expected):
    """函数对象可放进参数表或高阶 pipeline，而数值结果与对应语法一致。"""

    assert function(*arguments) == expected


@pytest.mark.parametrize(
    ("function", "arguments", "expected"),
    [
        (operator.and_, (0b1100, 0b1010), 0b1000),
        (operator.or_, (0b1100, 0b1010), 0b1110),
        (operator.xor, (0b1100, 0b1010), 0b0110),
        (operator.invert, (0b0011,), ~0b0011),
        (operator.lshift, (0b0011, 2), 0b1100),
        (operator.rshift, (0b1100, 2), 0b0011),
    ],
)
def test_bitwise_and_shift_function_family(function, arguments, expected):
    """and_/or_ 是 bitwise 运算，不是短路逻辑 and/or；两个参数都会在调用前求值。"""

    assert function(*arguments) == expected


def test_operator_pow_has_no_three_argument_modular_form():
    """operator.pow 对应二元 **；需要模幂时使用 builtins.pow(base, exponent, modulus)。"""

    assert operator.pow(2, 10) == 1024
    with pytest.raises(TypeError):
        operator.pow(2, 10, 17)


def test_matmul_delegates_to_matrix_multiplication_protocol():
    """operator.matmul 触发 __matmul__，不要求第三方数组库即可展示 @ 的协议入口。"""

    class Matrix:
        def __init__(self, label):
            self.label = label

        def __matmul__(self, other):
            return f"{self.label}@{other.label}"

    assert operator.matmul(Matrix("A"), Matrix("B")) == "A@B"


def test_python_310_index_normalizes_an_int_subclass_result_to_exact_int():
    """3.10 保证 operator.index 的结果 type 恰为 int；__index__ 返回 subclass 还会发弃用警告。"""

    class IntSubclass(int):
        pass

    class Indexable:
        def __index__(self):
            return IntSubclass(7)

    with pytest.warns(DeprecationWarning):
        result = operator.index(Indexable())

    assert result == 7
    assert type(result) is int


def test_invert_and_legacy_inv_names_have_the_same_operation():
    """inv 是向后兼容别名；新代码优先使用能直接对应 ~ 语法的 invert。"""

    assert operator.invert(10) == ~10
    assert operator.inv(10) == operator.invert(10)
    assert operator.__invert__(10) == operator.invert(10)


def test_concat_is_sequence_specific_while_add_is_a_general_protocol():
    """concat 明确要求 sequence concatenation；数值虽然支持 +，却不能被当作序列拼接。"""

    assert operator.concat([1, 2], [3]) == [1, 2, 3]
    assert operator.concat("ab", "cd") == "abcd"
    assert operator.add(1, 2) == 3

    with pytest.raises(TypeError):
        operator.concat(1, 2)


def test_contains_argument_order_is_container_then_candidate():
    """语法写 candidate in container，函数却写 contains(container, candidate)，顺序容易反。"""

    assert operator.contains([1, 2, 3], 2) is True
    assert operator.contains([1, 2, 3], 9) is False

    with pytest.raises(TypeError):
        operator.contains(2, [1, 2, 3])


def test_contains_delegates_to_the_container_protocol():
    """与 in 相同，它优先调用 container.__contains__，返回值再转换为 bool 结果。"""

    events = []

    class Container:
        def __contains__(self, candidate):
            events.append(candidate)
            return candidate == "known"

    assert operator.contains(Container(), "known") is True
    assert events == ["known"]


def test_countof_and_indexof_use_equality_and_first_match_semantics():
    """countOf 统计全部相等项；indexOf 返回第一个位置，找不到时抛 ValueError。"""

    values = ["A", "B", "A", "C"]

    assert operator.countOf(values, "A") == 2
    assert operator.indexOf(values, "A") == 0

    with pytest.raises(ValueError):
        operator.indexOf(values, "missing")


def test_dunder_aliases_dispatch_like_the_preferred_clear_names():
    """双下划线版本不是直接调用 left.__add__ 的捷径；它仍表示完整的语言运算。"""

    assert operator.__add__(2, 3) == operator.add(2, 3) == 5
    assert operator.__lt__(2, 3) == operator.lt(2, 3) is True
    assert operator.__not__([]) == operator.not_([]) is True


def test_operator_functions_compose_with_map_and_reduce():
    """函数化运算符避免临时 lambda，适合 dot product 等小型 iterator workflow。"""

    left = [1, 2, 3]
    right = [4, 5, 6]

    products = map(operator.mul, left, right)
    assert reduce(operator.add, products, 0) == 32


# ``operator`` getter、序列变更、长度提示与原地运算。
#
# attrgetter/itemgetter/methodcaller 把 lookup/call 变成可复用 callable，并在每次调用时
# 重新执行协议。length_hint 只是预分配建议，不是正确性边界。iadd 等函数只执行
# in-place 运算步骤，不会替调用者完成“把返回值重新赋给变量”的第二步。
#
# 这些案例面向 Python 3.10。

# polyglot-covers: python.operator.getitem python.operator.setitem python.operator.delitem
# polyglot-covers: python.operator.slice-operations python.operator.mapping-operations
# polyglot-covers: python.operator.length_hint python.operator.length-hint-fallback
# polyglot-covers: python.operator.__length_hint__ python.operator.length-hint-estimate
# polyglot-covers: python.operator.attrgetter python.operator.attrgetter-dotted
# polyglot-covers: python.operator.attrgetter-multiple python.operator.dynamic-attribute-lookup
# polyglot-covers: python.operator.itemgetter python.operator.itemgetter-multiple
# polyglot-covers: python.operator.itemgetter-slice python.operator.itemgetter-workflow
# polyglot-covers: python.operator.methodcaller python.operator.methodcaller-arguments
# polyglot-covers: python.operator.methodcaller-positional-name
# polyglot-covers: python.operator.dynamic-method-lookup
# polyglot-covers: python.operator.iadd python.operator.inplace-assignment-boundary
# polyglot-covers: python.operator.iconcat python.operator.inplace-mutable
# polyglot-covers: python.operator.inplace-functions python.operator.imatmul




def test_getitem_supports_indices_mapping_keys_and_slices():
    """getitem 直接触发 operand.__getitem__，item 类型由 operand 自己解释。"""

    assert operator.getitem("ABCDEFG", 2) == "C"
    assert operator.getitem({"name": "Ada"}, "name") == "Ada"
    assert operator.getitem("ABCDEFG", slice(2, None, 2)) == "CEG"


def test_setitem_and_delitem_mutate_the_target_and_return_none():
    """赋值/删除表达式本身没有结果；函数形态返回 None，同时保留目标对象 identity。"""

    values = ["A", "B", "C"]
    identity = id(values)

    assert operator.setitem(values, 1, "changed") is None
    assert values == ["A", "changed", "C"]
    assert operator.delitem(values, 0) is None
    assert values == ["changed", "C"]
    assert id(values) == identity


def test_setitem_and_delitem_accept_slice_objects():
    """slice assignment 可改变长度，slice deletion 一次删除一个区间；协议与语法完全相同。"""

    values = [0, 1, 2, 3, 4]

    operator.setitem(values, slice(1, 3), [10, 20, 30])
    assert values == [0, 10, 20, 30, 3, 4]

    operator.delitem(values, slice(2, 5))
    assert values == [0, 10, 4]


def test_mapping_assignment_and_deletion_use_the_same_functions():
    """item protocol 同时覆盖 sequence index 与 mapping key，不需要两套高阶接口。"""

    record = {"name": "Ada"}

    operator.setitem(record, "language", "Python")
    assert record == {"name": "Ada", "language": "Python"}
    operator.delitem(record, "name")
    assert record == {"language": "Python"}


def test_length_hint_prefers_actual_len_when_available():
    """优先尝试 __len__，只有没有实际长度才调用 __length_hint__。"""

    calls = []

    class Both:
        def __len__(self):
            calls.append("__len__")
            return 3

        def __length_hint__(self):
            calls.append("__length_hint__")
            return 99

    assert operator.length_hint(Both()) == 3
    assert calls == ["__len__"]


def test_iterator_length_hint_can_decrease_as_items_are_consumed():
    """list iterator 能估计剩余数量；该数值用于预分配，不应用作循环停止条件。"""

    iterator = iter([1, 2, 3])

    assert operator.length_hint(iterator) == 3
    assert next(iterator) == 1
    assert operator.length_hint(iterator) == 2


def test_length_hint_uses_default_when_no_protocol_is_available():
    """普通 object 没有 len/hint；调用者可提供 fallback，默认 fallback 是 0。"""

    value = object()

    assert operator.length_hint(value) == 0
    assert operator.length_hint(value, 17) == 17


def test_length_hint_notimplemented_falls_back_but_invalid_results_raise():
    """__length_hint__ 可返回 NotImplemented；负数或非 int 则违反协议，不能当普通 fallback。"""

    class Unknown:
        def __length_hint__(self):
            return NotImplemented

    class Negative:
        def __length_hint__(self):
            return -1

    class WrongType:
        def __length_hint__(self):
            return 1.5

    assert operator.length_hint(Unknown(), 8) == 8
    with pytest.raises(ValueError):
        operator.length_hint(Negative())
    with pytest.raises(TypeError):
        operator.length_hint(WrongType())


def test_length_hint_is_an_estimate_not_a_correctness_guarantee():
    """对象可以高估或低估；消费者仍必须以 StopIteration 决定真实结束。"""

    class Optimistic:
        def __iter__(self):
            yield 1
            yield 2

        def __length_hint__(self):
            return 100

    source = Optimistic()

    assert operator.length_hint(source) == 100
    assert list(source) == [1, 2]


def test_attrgetter_reads_one_or_multiple_attributes():
    """一个名称直接返回值，多个名称按请求顺序返回 tuple，适合作 sorted/map 的 key。"""

    record = SimpleNamespace(name="Ada", score=99)

    assert operator.attrgetter("name")(record) == "Ada"
    assert operator.attrgetter("score", "name")(record) == (99, "Ada")


def test_attrgetter_resolves_dotted_paths_one_attribute_at_a_time():
    """点号不是一次 getattr 的字面名称，而是依次执行 obj.profile.name lookup。"""

    user = SimpleNamespace(profile=SimpleNamespace(name="Ada", city="London"))
    getter = operator.attrgetter("profile.name", "profile.city")

    assert getter(user) == ("Ada", "London")


def test_attrgetter_performs_dynamic_lookup_on_every_call():
    """getter 保存 attribute 名而非首次值；对象变化后同一 callable 读取最新状态。"""

    record = SimpleNamespace(status="pending")
    get_status = operator.attrgetter("status")

    assert get_status(record) == "pending"
    record.status = "done"
    assert get_status(record) == "done"


def test_attrgetter_requires_string_attribute_names():
    """attribute path 必须在构造时给字符串；不存在的属性则延迟到调用时抛 AttributeError。"""

    with pytest.raises(TypeError):
        operator.attrgetter(1)

    getter = operator.attrgetter("missing")
    with pytest.raises(AttributeError):
        getter(SimpleNamespace())


def test_itemgetter_supports_single_multiple_and_slice_items():
    """单 item 返回裸值，多 item 返回 tuple；slice 本身也是合法 __getitem__ 参数。"""

    assert operator.itemgetter(1)("ABCDEFG") == "B"
    assert operator.itemgetter(1, 3, 5)("ABCDEFG") == ("B", "D", "F")
    assert operator.itemgetter(slice(2, None))("ABCDEFG") == "CDEFG"
    assert operator.itemgetter("rank")({"rank": "captain"}) == "captain"


def test_itemgetter_composes_with_map_and_sorted():
    """一个预构造 getter 可同时提取字段和作为排序 key，避免重复 lambda。"""

    inventory = [("apple", 3), ("banana", 2), ("pear", 5), ("orange", 1)]
    get_count = operator.itemgetter(1)

    assert list(map(get_count, inventory)) == [3, 2, 5, 1]
    assert sorted(inventory, key=get_count) == [
        ("orange", 1),
        ("banana", 2),
        ("apple", 3),
        ("pear", 5),
    ]


def test_getter_factories_require_at_least_one_target():
    """空 attr/item 列表没有可定义的返回 shape，因此构造阶段立即报 TypeError。"""

    with pytest.raises(TypeError):
        operator.attrgetter()
    with pytest.raises(TypeError):
        operator.itemgetter()


def test_methodcaller_invokes_named_method_with_frozen_arguments():
    """methodcaller(name,*args,**kwargs)(obj) 等价于 getattr(obj,name)(*args,**kwargs)。"""

    normalize = operator.methodcaller("replace", "-", " ")
    center = operator.methodcaller("center", 7, ".")

    assert normalize("one-two") == "one two"
    assert center("A") == "...A..."
    # methodcaller 会原样保存调用参数；str.center 的 fillchar 在 3.10
    # 是 positional-only，不能因为 factory 支持 kwargs 就改用关键字。


def test_methodcaller_looks_up_the_method_each_time():
    """callable 保存 method 名；实例后来用同名 callable 覆盖时，新调用会命中覆盖值。"""

    class Worker:
        def run(self, value):
            return f"class:{value}"

    worker = Worker()
    caller = operator.methodcaller("run", 3)

    assert caller(worker) == "class:3"
    worker.run = lambda value: f"instance:{value}"
    assert caller(worker) == "instance:3"


def test_methodcaller_name_is_positional_only_in_python_310():
    """签名中的 / 表明 name 不能写成 keyword，后续 keyword 都会传给目标 method。"""

    with pytest.raises(TypeError):
        operator.methodcaller(name="upper")


def test_iadd_mutates_mutable_targets_but_only_returns_new_immutable_values():
    """函数只做 in-place method 调用；immutable 结果若不手工赋回，原变量保持不变。"""

    text = "hello"
    text_result = operator.iadd(text, " world")

    assert text_result == "hello world"
    assert text == "hello"
    assert text_result is not text

    values = [1, 2]
    values_result = operator.iadd(values, [3])

    assert values_result is values
    assert values == [1, 2, 3]


def test_inplace_function_does_not_assign_a_replacement_back_to_the_caller():
    """__iadd__ 可以返回不同对象；operator.iadd 返回它，但无法重绑定调用者的 target 名称。"""

    class Replacing:
        def __init__(self, value):
            self.value = value

        def __iadd__(self, other):
            return Replacing(self.value + other)

    original = Replacing(10)
    result = operator.iadd(original, 5)

    assert result is not original
    assert original.value == 10
    assert result.value == 15


@pytest.mark.parametrize(
    ("function", "arguments", "expected"),
    [
        (operator.iand, (0b1100, 0b1010), 0b1000),
        (operator.ifloordiv, (7, 2), 3),
        (operator.ilshift, (3, 2), 12),
        (operator.imod, (7, 3), 1),
        (operator.imul, (7, 3), 21),
        (operator.ior, (0b1100, 0b1010), 0b1110),
        (operator.ipow, (2, 5), 32),
        (operator.irshift, (12, 2), 3),
        (operator.isub, (7, 3), 4),
        (operator.itruediv, (7, 2), 3.5),
        (operator.ixor, (0b1100, 0b1010), 0b0110),
    ],
)
def test_inplace_numeric_and_bitwise_function_family(function, arguments, expected):
    """对 immutable int，in-place 通常产生新值；调用者仍需执行 target = function(target, operand)。"""

    assert function(*arguments) == expected


def test_iconcat_uses_sequence_inplace_concatenation():
    """list.__iadd__ 原地扩展并返回 self；tuple 则只能返回一个新 tuple。"""

    mutable = [1, 2]
    mutable_result = operator.iconcat(mutable, [3])
    immutable = (1, 2)
    immutable_result = operator.iconcat(immutable, (3,))

    assert mutable_result is mutable
    assert mutable == [1, 2, 3]
    assert immutable_result == (1, 2, 3)
    assert immutable_result is not immutable


def test_imatmul_delegates_to_the_inplace_matrix_protocol():
    """自定义类型可在 __imatmul__ 中选择原地修改或 replacement；operator 直接返回协议结果。"""

    class Matrix:
        def __init__(self, labels):
            self.labels = labels

        def __imatmul__(self, other):
            self.labels.append(other)
            return self

    matrix = Matrix(["A"])
    result = operator.imatmul(matrix, "B")

    assert result is matrix
    assert matrix.labels == ["A", "B"]
