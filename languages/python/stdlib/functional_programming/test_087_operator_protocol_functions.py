"""087｜``operator`` 运算符函数与协议分派。

operator.add(x, y) 与 x + y 走同一数据模型协议，包括 NotImplemented、反射方法和
非 bool 的 rich comparison 返回值。函数形态适合 map/reduce/sorted 等高阶 API；
没有双下划线的名字更清晰，保留双下划线别名主要用于向后兼容。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
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
