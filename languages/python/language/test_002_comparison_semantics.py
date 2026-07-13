"""002｜比较、身份、成员判断与 rich comparison 协议。

比较运算符表面上很简单，但 Python 在这里同时区分对象身份、对象定义的
“值”、富比较特殊方法、反向分派和容器成员协议。本测试套把这些规则放在
一起，避免只记住 ``==`` 的表面写法，却不了解 ``NotImplemented``、链式
比较和 ``in`` 的 fallback 顺序。

内容基于 Python 3.10 Expressions 6.10 和 Data Model 的 rich comparison
methods。当前项目处于只编写、暂不执行的阶段，本文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.expression.value-comparisons
# polyglot-covers: python.expression.chained-comparisons
# polyglot-covers: python.expression.identity-comparisons
# polyglot-covers: python.expression.membership-tests
# polyglot-covers: python.protocol.__eq__
# polyglot-covers: python.protocol.__ne__
# polyglot-covers: python.protocol.__lt__
# polyglot-covers: python.protocol.__le__
# polyglot-covers: python.protocol.__gt__
# polyglot-covers: python.protocol.__ge__
# polyglot-covers: python.protocol.__contains__
# polyglot-covers: python.protocol.membership-iteration-fallback
# polyglot-covers: python.protocol.membership-getitem-fallback

import pytest


def test_value_equality_and_object_identity_answer_different_questions():
    """``==`` 比较值语义，``is`` 只判断是否为同一个对象。"""

    first = ["python", "rust"]
    same_value = ["python", "rust"]
    alias = first

    assert first == same_value
    assert first is not same_value
    assert first is alias

    # 常见坑：小整数和部分字符串可能被解释器复用，因此偶尔能观察到
    # ``a is b``，但那不是值比较契约。需要比较内容时始终使用 ==。
    # None 是语言定义的单例，判断它时反而应该使用 is / is not。
    result = None
    assert result is None


def test_plain_objects_have_identity_equality_but_no_default_ordering():
    """普通对象默认只与自身相等，也没有凭空产生的大小顺序。"""

    first = object()
    second = object()

    assert first == first
    assert first != second

    # Python 3 不会像早期 Python 那样给任意不同类型或普通对象制造排序。
    # 如果业务对象需要顺序，类必须明确实现相应的 rich comparison 方法。
    with pytest.raises(TypeError):
        first < second


def test_chained_comparison_evaluates_the_middle_expression_once():
    """``low < value <= high`` 既短路，又只计算一次中间表达式。"""

    calls = []

    def current_temperature():
        calls.append("temperature")
        return 21

    assert 18 < current_temperature() <= 24
    assert calls == ["temperature"]

    # 手工改写时如果重复调用函数，就不再与链式比较等价；当函数昂贵或有
    # 副作用时，这种差异尤其重要。
    calls.clear()
    assert 18 < current_temperature() and current_temperature() <= 24
    assert calls == ["temperature", "temperature"]


def test_chained_comparison_short_circuits_later_expressions():
    """前一段比较失败后，链条右侧不会继续求值。"""

    events = []

    def upper_bound():
        events.append("upper bound evaluated")
        return 100

    assert not (10 < 5 < upper_bound())
    assert events == []


class ComparisonProbe:
    """用返回标记直观展示六个运算符分别调用哪个特殊方法。"""

    def __lt__(self, other):
        return "__lt__"

    def __le__(self, other):
        return "__le__"

    def __eq__(self, other):
        return "__eq__"

    def __ne__(self, other):
        return "__ne__"

    def __gt__(self, other):
        return "__gt__"

    def __ge__(self, other):
        return "__ge__"


def test_rich_comparison_operators_dispatch_to_the_matching_methods():
    """富比较方法允许返回非 bool；布尔上下文才会继续调用 ``bool``。"""

    left = ComparisonProbe()
    right = object()

    assert (left < right) == "__lt__"
    assert (left <= right) == "__le__"
    assert (left == right) == "__eq__"
    assert (left != right) == "__ne__"
    assert (left > right) == "__gt__"
    assert (left >= right) == "__ge__"

    # 业务比较通常应返回 bool 或 NotImplemented。这里故意返回字符串，
    # 只是为了把运算符与方法的对应关系显示出来，并展示协议确实允许其他
    # 结果对象；一旦放进 if，字符串仍会经过真假值判断。
    assert bool(left < right) is True


def test_comparison_methods_are_independent_instead_of_automatically_derived():
    """实现 ``__lt__`` 和 ``__eq__`` 不会自动得到 ``__le__``。"""

    class PartialOrder:
        def __init__(self, rank):
            self.rank = rank

        def __lt__(self, other):
            if not isinstance(other, PartialOrder):
                return NotImplemented
            return self.rank < other.rank

        def __eq__(self, other):
            if not isinstance(other, PartialOrder):
                return NotImplemented
            return self.rank == other.rank

    low = PartialOrder(1)
    high = PartialOrder(2)

    assert low < high
    assert low != high

    # 常见坑：数学上 ``a < b or a == b`` 能表达 <=，不代表解释器会替类
    # 合成 __le__。需要全部排序运算时应显式实现，或以后使用
    # functools.total_ordering 生成缺失方法。
    with pytest.raises(TypeError):
        low <= high


def test_not_implemented_gives_the_other_operand_a_chance_to_compare():
    """左侧不支持组合时返回 ``NotImplemented``，Python 再尝试反向方法。"""

    calls = []

    class LeftOperand:
        def __lt__(self, other):
            calls.append("left.__lt__")
            return NotImplemented

    class RightOperand:
        def __gt__(self, other):
            calls.append("right.__gt__")
            return True

    assert LeftOperand() < RightOperand()
    assert calls == ["left.__lt__", "right.__gt__"]

    # 富比较没有 __rlt__ 这类单独的“r 方法”。< 的反向伙伴是右侧的
    # __gt__，<= 的反向伙伴是 __ge__；== 和 != 则各自反向调用同名方法。


def test_returning_false_instead_of_not_implemented_blocks_reflection():
    """``False`` 表示“比较完成且结果为假”，不是“不支持这个类型”。"""

    calls = []

    class IncorrectLeftOperand:
        def __lt__(self, other):
            calls.append("left.__lt__")
            return False

    class RightOperandThatCouldHandleIt:
        def __gt__(self, other):
            calls.append("right.__gt__")
            return True

    assert (IncorrectLeftOperand() < RightOperandThatCouldHandleIt()) is False
    assert calls == ["left.__lt__"]

    # 这是自定义协议中很实际的坑：类型不认识 other 时返回 False，会悄悄
    # 吞掉另一侧正确处理该组合的机会。应返回单例 NotImplemented。


def test_subclass_reflected_method_has_priority_over_base_implementation():
    """右侧类型是左侧类型的子类时，子类的反向方法先执行。"""

    calls = []

    class BaseVersion:
        def __lt__(self, other):
            calls.append("base.__lt__")
            return False

    class SpecializedVersion(BaseVersion):
        def __gt__(self, other):
            calls.append("specialized.__gt__")
            return True

    assert BaseVersion() < SpecializedVersion()
    assert calls == ["specialized.__gt__"]

    # 这个优先级让子类有机会覆盖基类定义的跨版本行为；它甚至发生在基类
    # __lt__ 被调用之前，而不是必须等基类返回 NotImplemented。


def test_equality_falls_back_to_identity_when_both_sides_decline():
    """双方 ``__eq__`` 都返回 ``NotImplemented`` 后，== 最终按身份判断。"""

    class DeclinesEquality:
        def __eq__(self, other):
            return NotImplemented

    first = DeclinesEquality()
    second = DeclinesEquality()

    assert first == first
    assert first != second


def test_unrelated_types_may_support_equality_without_supporting_ordering():
    """不同类型的相等比较通常能得出假，排序则可能没有定义。"""

    assert [1, 2] != (1, 2)

    with pytest.raises(TypeError):
        [1, 2] < (1, 2)

    with pytest.raises(TypeError):
        1 < "2"


def test_nan_is_not_equal_to_itself():
    """NaN 是比较一致性规则中的重要例外。"""

    not_a_number = float("nan")

    assert not_a_number != not_a_number
    assert not (not_a_number < 0)
    assert not (not_a_number > 0)

    # 常见坑：不能用 value == float("nan") 判断 NaN；实际代码应使用
    # math.isnan。这里保留直接比较案例，是为了说明比较语义本身。


def test_builtin_membership_has_type_specific_meanings():
    """序列查元素、字典查键、字符串查子串。"""

    assert "python" in ["python", "rust"]

    versions = {"python": "3.10"}
    assert "python" in versions
    assert "3.10" not in versions

    assert "thon" in "python"
    assert "" in "python"

    # 字典成员判断只检查键，不检查值；空字符串又是任意字符串的子串。
    # 两者都很常见，也都不能仅凭日常语言直觉猜测。


class ExplicitMembership:
    def __init__(self):
        self.calls = []

    def __contains__(self, item):
        self.calls.append(("__contains__", item))
        return item == "allowed"

    def __iter__(self):
        self.calls.append(("__iter__", None))
        yield "fallback value"


def test_membership_prefers_dunder_contains_over_iteration():
    """定义 ``__contains__`` 后，``in`` 不需要扫描迭代器。"""

    values = ExplicitMembership()

    assert "allowed" in values
    assert "missing" not in values
    assert values.calls == [
        ("__contains__", "allowed"),
        ("__contains__", "missing"),
    ]


class IterableMembership:
    def __init__(self, values):
        self.values = values
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        return iter(self.values)


def test_membership_falls_back_to_iteration():
    """没有 ``__contains__`` 时，``in`` 逐个比较迭代结果。"""

    values = IterableMembership(["alpha", "beta"])

    assert "beta" in values
    assert "missing" not in values
    assert values.iterations == 2


class LegacySequenceMembership:
    """只实现旧式连续整数索引，展示成员判断最后一级 fallback。"""

    def __init__(self, values):
        self.values = values
        self.requested_indexes = []

    def __getitem__(self, index):
        self.requested_indexes.append(index)
        if index >= len(self.values):
            raise IndexError
        return self.values[index]


def test_membership_final_fallback_uses_getitem_until_index_error():
    """没有 contains 和 iter 时，``in`` 从索引 0 开始调用 ``__getitem__``。"""

    values = LegacySequenceMembership(["first", "second"])

    assert "second" in values
    assert values.requested_indexes == [0, 1]

    values.requested_indexes.clear()
    assert "missing" not in values
    assert values.requested_indexes == [0, 1, 2]

    # IndexError 是“序列结束”的协议信号。若错误地返回 None 而不抛出异常，
    # 找不到元素的成员测试可能永远继续索引，形成死循环。
