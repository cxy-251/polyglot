"""二元、反向与原地运算符的完整分派骨架。

Python 的算术符号不仅服务于数字：``+`` 也能拼接序列，``*`` 也能重复
序列，自定义类型则通过普通、反向和原地三组特殊方法接入运算。这个测试套
先完整展示运算符到特殊方法的映射，再用少量正常工作流解释分派优先级、
``NotImplemented``、增强赋值和内置类型中容易误解的行为。

内容基于 Python 3.10 Expressions 6.5--6.9、Simple Statements 7.2.1 和
Data Model 3.3.8。当前项目处于只编写、暂不执行的阶段，本文件尚未经过
pytest 验证。
"""

# polyglot-covers: python.expression.power
# polyglot-covers: python.expression.binary-arithmetic
# polyglot-covers: python.expression.shifts
# polyglot-covers: python.expression.bitwise-operations
# polyglot-covers: python.statement.augmented-assignment
# polyglot-covers: python.protocol.__add__ python.protocol.__sub__ python.protocol.__mul__
# polyglot-covers: python.protocol.__matmul__ python.protocol.__truediv__ python.protocol.__floordiv__
# polyglot-covers: python.protocol.__mod__ python.protocol.__divmod__ python.protocol.__pow__
# polyglot-covers: python.protocol.__lshift__ python.protocol.__rshift__
# polyglot-covers: python.protocol.__and__ python.protocol.__xor__ python.protocol.__or__
# polyglot-covers: python.protocol.reflected-binary-operations
# polyglot-covers: python.protocol.inplace-binary-operations

import operator

import pytest


def test_builtin_arithmetic_precedence_and_power_associativity():
    """乘法先于加法，幂从右向左结合，并且与左侧负号有特殊优先级。"""

    assert 2 + 3 * 4 == 14
    assert 2**3**2 == 2 ** (3**2) == 512

    # 常见坑：-2**2 解析为 -(2**2)，不是 (-2)**2。负指数则允许整数底数
    # 产生浮点结果。
    assert -2**2 == -4
    assert (-2) ** 2 == 4
    assert 2**-2 == 0.25


def test_true_division_floor_division_modulo_and_divmod_stay_consistent():
    """``//`` 向负无穷舍入，余数符号跟随除数。"""

    assert 5 / 2 == 2.5
    assert 5 // 2 == 2
    assert -5 // 2 == -3

    quotient, remainder = divmod(-5, 2)
    assert (quotient, remainder) == (-3, 1)
    assert -5 == quotient * 2 + remainder

    # 常见坑：整除不是简单“截掉小数”。如果向零截断，-5 / 2 会得到 -2；
    # floor division 必须向下取整，所以结果是 -3，并由余数保持恒等式成立。


def test_sequence_addition_and_multiplication_reuse_arithmetic_symbols():
    """序列用 ``+`` 拼接、用整数 ``*`` 重复，但仍有严格类型契约。"""

    assert [1, 2] + [3] == [1, 2, 3]
    assert "ha" * 3 == "hahaha"
    assert 3 * "ha" == "hahaha"
    assert "ha" * -1 == ""

    # list 与 tuple 都是序列，却不能直接拼接。+ 对序列通常要求相同类型，
    # 不会因为两边都可迭代就自动转换。
    with pytest.raises(TypeError):
        [1, 2] + (3,)


def test_shift_and_bitwise_operators_have_distinct_integer_meanings():
    """移位改变二进制位位置，按位运算逐位组合整数。"""

    assert 0b0011 << 2 == 0b1100
    assert 0b1100 >> 2 == 0b0011
    assert 0b1100 & 0b1010 == 0b1000
    assert 0b1100 ^ 0b1010 == 0b0110
    assert 0b1100 | 0b1010 == 0b1110


class BinaryMethodProbe:
    """返回方法名，完整显示普通二元运算符的协议映射。"""

    def __add__(self, other):
        return "__add__"

    def __sub__(self, other):
        return "__sub__"

    def __mul__(self, other):
        return "__mul__"

    def __matmul__(self, other):
        return "__matmul__"

    def __truediv__(self, other):
        return "__truediv__"

    def __floordiv__(self, other):
        return "__floordiv__"

    def __mod__(self, other):
        return "__mod__"

    def __divmod__(self, other):
        return "__divmod__"

    def __pow__(self, other, modulo=None):
        return "__pow__", modulo

    def __lshift__(self, other):
        return "__lshift__"

    def __rshift__(self, other):
        return "__rshift__"

    def __and__(self, other):
        return "__and__"

    def __xor__(self, other):
        return "__xor__"

    def __or__(self, other):
        return "__or__"


def test_all_binary_operators_dispatch_to_their_normal_methods():
    """普通二元协议覆盖算术、矩阵、除法、幂、移位和按位运算。"""

    left = BinaryMethodProbe()
    right = object()

    assert left + right == "__add__"
    assert left - right == "__sub__"
    assert left * right == "__mul__"
    assert left @ right == "__matmul__"
    assert left / right == "__truediv__"
    assert left // right == "__floordiv__"
    assert left % right == "__mod__"
    assert divmod(left, right) == "__divmod__"
    assert left**right == ("__pow__", None)
    assert pow(left, right, 7) == ("__pow__", 7)
    assert left << right == "__lshift__"
    assert left >> right == "__rshift__"
    assert left & right == "__and__"
    assert left ^ right == "__xor__"
    assert left | right == "__or__"

    # operator 模块提供函数形式，但仍触发同一数据模型协议。
    assert operator.add(left, right) == "__add__"


class ReflectedMethodProbe:
    """完整显示左侧不支持操作时会尝试的反向方法。"""

    def __radd__(self, other):
        return "__radd__"

    def __rsub__(self, other):
        return "__rsub__"

    def __rmul__(self, other):
        return "__rmul__"

    def __rmatmul__(self, other):
        return "__rmatmul__"

    def __rtruediv__(self, other):
        return "__rtruediv__"

    def __rfloordiv__(self, other):
        return "__rfloordiv__"

    def __rmod__(self, other):
        return "__rmod__"

    def __rdivmod__(self, other):
        return "__rdivmod__"

    def __rpow__(self, other, modulo=None):
        return "__rpow__", modulo

    def __rlshift__(self, other):
        return "__rlshift__"

    def __rrshift__(self, other):
        return "__rrshift__"

    def __rand__(self, other):
        return "__rand__"

    def __rxor__(self, other):
        return "__rxor__"

    def __ror__(self, other):
        return "__ror__"


def test_all_binary_operators_can_dispatch_to_reflected_methods():
    """反向方法属于右操作数，方法内部的 ``self`` 仍然是右侧对象。"""

    left = object()
    right = ReflectedMethodProbe()

    assert left + right == "__radd__"
    assert left - right == "__rsub__"
    assert left * right == "__rmul__"
    assert left @ right == "__rmatmul__"
    assert left / right == "__rtruediv__"
    assert left // right == "__rfloordiv__"
    assert left % right == "__rmod__"
    assert divmod(left, right) == "__rdivmod__"
    assert left**right == ("__rpow__", None)
    assert left << right == "__rlshift__"
    assert left >> right == "__rrshift__"
    assert left & right == "__rand__"
    assert left ^ right == "__rxor__"
    assert left | right == "__ror__"


def test_not_implemented_triggers_reflected_binary_dispatch():
    """普通方法不认识另一类型时，返回 ``NotImplemented`` 让右侧接手。"""

    calls = []

    class LeftOperand:
        def __add__(self, other):
            calls.append("left.__add__")
            return NotImplemented

    class RightOperand:
        def __radd__(self, other):
            calls.append("right.__radd__")
            return "combined"

    assert LeftOperand() + RightOperand() == "combined"
    assert calls == ["left.__add__", "right.__radd__"]


def test_raising_type_error_inside_normal_method_blocks_reflected_dispatch():
    """不支持类型时应返回 ``NotImplemented``，而不是过早抛出异常。"""

    calls = []

    class IncorrectLeftOperand:
        def __add__(self, other):
            calls.append("left.__add__")
            raise TypeError("left operand rejected the type too early")

    class RightOperand:
        def __radd__(self, other):
            calls.append("right.__radd__")
            return "right side could handle it"

    with pytest.raises(TypeError):
        IncorrectLeftOperand() + RightOperand()

    assert calls == ["left.__add__"]


def test_reflected_method_is_not_an_unconditional_second_call():
    """左侧已经成功返回结果时，右侧的反向方法不会执行。"""

    calls = []

    class LeftOperand:
        def __add__(self, other):
            calls.append("left.__add__")
            return "left result"

    class RightOperand:
        def __radd__(self, other):
            calls.append("right.__radd__")
            return "right result"

    assert LeftOperand() + RightOperand() == "left result"
    assert calls == ["left.__add__"]

    # 常见坑：__radd__ 不是“把两个参数调换后总会再调用一次”。它只在左侧
    # 不支持操作时参与，或者在右侧类型是左侧子类时获得优先机会。


def test_right_subclass_reflected_method_can_override_base_dispatch():
    """右侧是更具体的子类时，其反向实现优先于左侧基类实现。"""

    calls = []

    class BaseQuantity:
        def __add__(self, other):
            calls.append("base.__add__")
            return "base result"

    class SpecializedQuantity(BaseQuantity):
        def __radd__(self, other):
            calls.append("specialized.__radd__")
            return "specialized result"

    result = BaseQuantity() + SpecializedQuantity()

    assert result == "specialized result"
    assert calls == ["specialized.__radd__"]


class InPlaceMethodProbe:
    """返回方法名，显示每个增强赋值符号对应的原地方法。"""

    def __iadd__(self, other):
        return "__iadd__"

    def __isub__(self, other):
        return "__isub__"

    def __imul__(self, other):
        return "__imul__"

    def __imatmul__(self, other):
        return "__imatmul__"

    def __itruediv__(self, other):
        return "__itruediv__"

    def __ifloordiv__(self, other):
        return "__ifloordiv__"

    def __imod__(self, other):
        return "__imod__"

    def __ipow__(self, other):
        return "__ipow__"

    def __ilshift__(self, other):
        return "__ilshift__"

    def __irshift__(self, other):
        return "__irshift__"

    def __iand__(self, other):
        return "__iand__"

    def __ixor__(self, other):
        return "__ixor__"

    def __ior__(self, other):
        return "__ior__"


def test_all_augmented_assignments_dispatch_to_inplace_methods():
    """增强赋值会把原地方法的返回值重新绑定给左侧目标。"""

    other = object()

    value = InPlaceMethodProbe()
    value += other
    assert value == "__iadd__"

    value = InPlaceMethodProbe()
    value -= other
    assert value == "__isub__"

    value = InPlaceMethodProbe()
    value *= other
    assert value == "__imul__"

    value = InPlaceMethodProbe()
    value @= other
    assert value == "__imatmul__"

    value = InPlaceMethodProbe()
    value /= other
    assert value == "__itruediv__"

    value = InPlaceMethodProbe()
    value //= other
    assert value == "__ifloordiv__"

    value = InPlaceMethodProbe()
    value %= other
    assert value == "__imod__"

    value = InPlaceMethodProbe()
    value **= other
    assert value == "__ipow__"

    value = InPlaceMethodProbe()
    value <<= other
    assert value == "__ilshift__"

    value = InPlaceMethodProbe()
    value >>= other
    assert value == "__irshift__"

    value = InPlaceMethodProbe()
    value &= other
    assert value == "__iand__"

    value = InPlaceMethodProbe()
    value ^= other
    assert value == "__ixor__"

    value = InPlaceMethodProbe()
    value |= other
    assert value == "__ior__"


class MutableCounter:
    def __init__(self, total):
        self.total = total

    def __iadd__(self, amount):
        self.total += amount
        return self


def test_inplace_method_can_mutate_and_preserve_identity():
    """正确的可变 ``__iadd__`` 通常修改 ``self`` 并返回同一个对象。"""

    counter = MutableCounter(10)
    alias = counter

    counter += 5

    assert counter is alias
    assert alias.total == 15


class ImmutableCounter:
    def __init__(self, total):
        self.total = total

    def __add__(self, amount):
        return ImmutableCounter(self.total + amount)


def test_augmented_assignment_falls_back_to_normal_method_and_rebinds():
    """缺少 ``__iadd__`` 时，``+=`` 使用普通加法并绑定其新结果。"""

    counter = ImmutableCounter(10)
    original = counter

    counter += 5

    assert counter is not original
    assert counter.total == 15
    assert original.total == 10


class ForgetsToReturnSelf:
    def __init__(self, total):
        self.total = total

    def __iadd__(self, amount):
        self.total += amount
        # 故意遗漏 return self。


def test_inplace_method_return_value_is_always_rebound_to_the_target():
    """原地方法即使修改成功，也必须返回增强赋值之后应保存的对象。"""

    value = ForgetsToReturnSelf(10)
    alias = value

    value += 5

    assert alias.total == 15
    assert value is None

    # 常见坑：__iadd__ 忘记 return self 时，原对象确实已修改，但变量随后
    # 被重新绑定到隐式返回值 None，错误往往在后续使用变量时才暴露。


def test_list_plus_equals_mutates_but_tuple_plus_equals_rebinds():
    """增强赋值不保证原地修改，实际行为由对象类型决定。"""

    mutable = [1, 2]
    mutable_alias = mutable
    mutable += [3]

    assert mutable is mutable_alias
    assert mutable_alias == [1, 2, 3]

    immutable = (1, 2)
    immutable_alias = immutable
    immutable += (3,)

    assert immutable is not immutable_alias
    assert immutable == (1, 2, 3)
    assert immutable_alias == (1, 2)


def test_augmented_assignment_evaluates_a_complex_target_once():
    """``target.attribute += value`` 只解析一次左侧目标。"""

    class Holder:
        def __init__(self):
            self._value = 10
            self.events = []

        @property
        def value(self):
            self.events.append("get")
            return self._value

        @value.setter
        def value(self, new_value):
            self.events.append(("set", new_value))
            self._value = new_value

    holder = Holder()
    holder.value += 5

    assert holder._value == 15
    assert holder.events == ["get", ("set", 15)]


def test_augmented_assignment_can_mutate_before_target_assignment_fails():
    """tuple 中的可变元素可能先被修改，随后 tuple 赋值才失败。"""

    values = ([1, 2],)

    with pytest.raises(TypeError):
        values[0] += [3]

    assert values == ([1, 2, 3],)

    # 执行顺序是：取出 values[0]、对列表执行原地加法、再尝试把结果写回
    # values[0]。最后一步因为 tuple 不可赋值而报错，但列表修改无法回滚。


def test_ternary_pow_calls_left_dunder_pow_with_the_modulus():
    """三参数 ``pow`` 把模数作为 ``__pow__`` 的第三个协议参数。"""

    class ModularNumber:
        def __pow__(self, exponent, modulo=None):
            return exponent, modulo

    assert pow(ModularNumber(), 5, 7) == (5, 7)


def test_python_310_ternary_pow_does_not_try_reflected_pow():
    """Python 3.10 的三参数 ``pow`` 不使用右侧 ``__rpow__`` fallback。"""

    calls = []

    class LeftOperand:
        def __pow__(self, exponent, modulo=None):
            calls.append(("left.__pow__", modulo))
            return NotImplemented

    class RightOperand:
        def __rpow__(self, base, modulo=None):
            calls.append(("right.__rpow__", modulo))
            return "reflected result"

    with pytest.raises(TypeError):
        pow(LeftOperand(), RightOperand(), 7)

    assert calls == [("left.__pow__", 7)]

    # 这是版本相关行为，因此测试名称明确写出 Python 3.10。以后升级语言
    # 基线时必须重新核对，而不能假定所有 Python 版本都保持相同分派。
