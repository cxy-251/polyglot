"""004｜一元运算与数值转换协议的可执行示例。

一元 ``-``、``+``、``~`` 和 ``abs()`` 都会分派到对象的特殊方法；
``int()``、``float()``、``complex()`` 与“需要精确整数”的索引协议则有各自的
优先级和返回值契约。本测试套用正常工作流连接这些入口，并把 Python 3.10
特有的 fallback 单独标出，避免以后升级版本时把旧行为误当成永久保证。

内容基于 Python 3.10 Expressions 6.6、Data Model 3.3.8、Built-in
Functions、operator.index 和 math 的数论函数。
"""

# polyglot-covers: python.expression.unary-arithmetic
# polyglot-covers: python.builtin.abs python.builtin.int python.builtin.float
# polyglot-covers: python.builtin.complex python.builtin.bin python.builtin.hex
# polyglot-covers: python.builtin.oct python.builtin.round
# polyglot-covers: python.protocol.__neg__ python.protocol.__pos__
# polyglot-covers: python.protocol.__invert__ python.protocol.__abs__
# polyglot-covers: python.protocol.__int__ python.protocol.__float__
# polyglot-covers: python.protocol.__complex__ python.protocol.__index__
# polyglot-covers: python.protocol.__round__ python.protocol.__trunc__
# polyglot-covers: python.protocol.__floor__ python.protocol.__ceil__
# polyglot-covers: python.stdlib.operator.index python.stdlib.math.trunc
# polyglot-covers: python.stdlib.math.floor python.stdlib.math.ceil

import math
import operator

import pytest


def test_builtin_unary_operators_have_distinct_numeric_meanings():
    """负号、正号和按位取反不是同一种“改变符号”操作。"""

    assert -7 == -7
    assert +(-7) == -7
    assert ~7 == -8

    # 对整数，~x 等于 -(x + 1)，因为 Python 的按位运算按无限长二进制补码
    # 的效果定义。常见坑是把 ~x 误认为 -x；7 的结果实际是 -8。
    for value in (-7, 0, 7):
        assert ~value == -(value + 1)


def test_abs_handles_real_and_complex_magnitudes():
    """``abs`` 对实数取绝对值，对复数返回到原点的距离。"""

    assert abs(-12) == 12
    assert abs(3 + 4j) == 5.0


class UnaryMethodProbe:
    """用返回标记显示四个一元入口对应的特殊方法。"""

    def __neg__(self):
        return "__neg__"

    def __pos__(self):
        return "__pos__"

    def __invert__(self):
        return "__invert__"

    def __abs__(self):
        return "__abs__"


def test_unary_operators_dispatch_to_their_special_methods():
    """语法运算符和 ``abs`` 内置函数共享同一套数值数据模型。"""

    value = UnaryMethodProbe()

    assert -value == "__neg__"
    assert +value == "__pos__"
    assert ~value == "__invert__"
    assert abs(value) == "__abs__"


class Measurement:
    def __init__(self, value):
        self.value = value

    def __pos__(self):
        """返回规范化的新值，而不是机械地返回 ``self``。"""

        return Measurement(max(0, self.value))


def test_custom_unary_plus_may_create_a_new_or_normalized_object():
    """一元正号由 ``__pos__`` 定义，不承诺保留对象身份。"""

    original = Measurement(-3)
    normalized = +original

    assert normalized is not original
    assert normalized.value == 0
    assert original.value == -3

    # 常见坑：对 int 等内置不可变对象，+value 看起来像“什么也没做”，但
    # 自定义类型完全可以借此产生副本、规范化值或返回另一种表示。


class ExplicitConversions:
    def __init__(self):
        self.calls = []

    def __int__(self):
        self.calls.append("__int__")
        return 11

    def __float__(self):
        self.calls.append("__float__")
        return 2.5

    def __complex__(self):
        self.calls.append("__complex__")
        return 3 + 4j

    def __index__(self):
        self.calls.append("__index__")
        return 99


def test_explicit_numeric_conversion_methods_take_priority_over_index():
    """各转换函数优先调用自己的专用方法，而不是直接使用 ``__index__``。"""

    value = ExplicitConversions()

    assert int(value) == 11
    assert float(value) == 2.5
    assert complex(value) == 3 + 4j
    assert value.calls == ["__int__", "__float__", "__complex__"]


class IndexOnly:
    """表示可无损转换成整数、因而可安全用作索引的值。"""

    def __init__(self, value):
        self.value = value

    def __index__(self):
        return self.value


def test_index_protocol_serves_integer_only_standard_library_apis():
    """索引、切片、range 和进制格式化都要求 ``__index__``。"""

    position = IndexOnly(2)
    stop = IndexOnly(3)
    value = IndexOnly(10)
    letters = ["a", "b", "c", "d"]

    assert operator.index(position) == 2
    assert letters[position] == "c"
    assert letters[:stop] == ["a", "b", "c"]
    assert list(range(stop)) == [0, 1, 2]
    assert bin(value) == "0b1010"
    assert oct(value) == "0o12"
    assert hex(value) == "0xa"

    # 这些入口不能接受任意“近似可转整数”的对象。__index__ 的语义是值本来
    # 就能被无损看作整数，因此既适合容器位置，也适合位数和进制表示。


def test_python_310_numeric_constructors_fall_back_to_index():
    """Python 3.10 在专用转换方法缺失时允许三个构造器使用 ``__index__``。"""

    value = IndexOnly(7)

    assert int(value) == 7
    assert float(value) == 7.0
    assert complex(value) == 7 + 0j

    # 这是版本相关 fallback。测试名称明确锁定 Python 3.10；升级 sources.lock
    # 后应重新核对官方文档，而不是默认后续版本的优先级永远不变。


class IntOnly:
    def __int__(self):
        return 2


def test_int_conversion_does_not_automatically_make_an_object_an_index():
    """``__int__`` 允许显式转换，但不表示对象可无损用于索引。"""

    value = IntOnly()

    assert int(value) == 2

    with pytest.raises(TypeError):
        operator.index(value)

    with pytest.raises(TypeError):
        ["a", "b", "c"][value]

    with pytest.raises(TypeError):
        bin(value)

    # 常见坑：给类实现 __int__ 后，int(value) 成功，并不意味着 range、切片、
    # bin/hex/oct 也接受它。只有确实拥有无损整数语义的类型才应实现 __index__。


def test_conversion_fallbacks_follow_the_documented_precedence():
    """``complex`` 依次考虑 complex、float、index，而 ``float`` 再退到 index。"""

    calls = []

    class FloatAndIndex:
        def __float__(self):
            calls.append("__float__")
            return 2.5

        def __index__(self):
            calls.append("__index__")
            return 9

    value = FloatAndIndex()

    assert complex(value) == 2.5 + 0j
    assert calls == ["__float__"]

    calls.clear()
    assert float(value) == 2.5
    assert calls == ["__float__"]


def test_conversion_special_methods_have_strict_result_types():
    """数值转换方法不能只返回“看起来可以继续转换”的任意对象。"""

    class BadInt:
        def __int__(self):
            return 1.5

    class BadFloat:
        def __float__(self):
            return "1.5"

    class BadComplex:
        def __complex__(self):
            return (1, 2)

    class BadIndex:
        def __index__(self):
            return 1.0

    with pytest.raises(TypeError):
        int(BadInt())

    with pytest.raises(TypeError):
        float(BadFloat())

    with pytest.raises(TypeError):
        complex(BadComplex())

    with pytest.raises(TypeError):
        operator.index(BadIndex())

    # Python 不会把 __int__ 返回的 float 再执行一次 int，也不会把 __index__
    # 返回的 1.0 当作 1；协议方法自身必须直接履行所声明的类型契约。


def test_python_310_normalizes_legacy_index_int_subclass_results():
    """Python 3.10 会警告不精确的返回类型，并把结果规范成精确 ``int``。"""

    class LegacyBooleanIndex:
        def __index__(self):
            # bool 是 int 的子类，但不是 __index__ 契约要求的精确整数类型。
            return True

    with pytest.warns(DeprecationWarning):
        result = operator.index(LegacyBooleanIndex())

    assert result == 1
    assert type(result) is int

    # 常见坑：依赖这个兼容行为会把错误的数据模型带到新版本。正确实现应直接
    # 返回普通 int；这里保留反例，是为了记录 Python 3.10 的迁移期表现。


class RoundProbe:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def __round__(self, ndigits=None):
        self.calls.append(ndigits)
        if ndigits is None:
            return int(self.value)
        return float(f"{self.value:.{ndigits}f}")


def test_round_delegates_and_passes_ndigits_to_round_method():
    """省略和提供 ``ndigits`` 会以不同参数调用 ``__round__``。"""

    value = RoundProbe(3.14159)

    assert round(value) == 3
    assert round(value, 2) == 3.14
    assert value.calls == [None, 2]

    # 常见坑：把 __round__ 定义成不接收 ndigits 的无参方法，只会在
    # round(value) 时碰巧工作，round(value, 2) 会因为参数不匹配而失败。


def test_builtin_round_uses_ties_to_even_and_exposes_binary_float_limits():
    """内置舍入采用偶数舍入；十进制小数还受二进制浮点表示影响。"""

    assert round(2.5) == 2
    assert round(3.5) == 4
    assert round(2.675, 2) == 2.67

    # 2.675 无法被二进制浮点精确表示，所以这个结果不是 round 的随机错误。
    # 需要精确十进制规则的业务应选用标准库 decimal，而不是猜测 float 尾数。


class IntegralRounding:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def __trunc__(self):
        self.calls.append("__trunc__")
        return int(self.value)

    def __floor__(self):
        self.calls.append("__floor__")
        return int(self.value // 1)

    def __ceil__(self):
        self.calls.append("__ceil__")
        quotient = int(self.value // 1)
        return quotient if self.value == quotient else quotient + 1


def test_math_integer_rounding_functions_delegate_to_distinct_protocols():
    """截断、下取整和上取整是三种独立操作，不可互相替代。"""

    value = IntegralRounding(-2.4)

    assert math.trunc(value) == -2
    assert math.floor(value) == -3
    assert math.ceil(value) == -2
    assert value.calls == ["__trunc__", "__floor__", "__ceil__"]

    # 负数最能暴露区别：trunc 朝零得到 -2，floor 朝负无穷得到 -3，ceil
    # 朝正无穷也得到 -2。实现数值类型时不应让三个方法盲目共享同一结果。


def test_python_310_int_can_use_trunc_as_its_last_legacy_fallback():
    """Python 3.10 的 ``int`` 在 int/index 均缺失时最后尝试 ``__trunc__``。"""

    class LegacyTruncOnly:
        def __trunc__(self):
            return 8

    assert int(LegacyTruncOnly()) == 8

    # 这是为 Python 3.10 基线保留的历史行为，不是新类型的推荐设计。希望支持
    # int(value) 的类型应直接实现 __int__，拥有无损整数语义时再实现 __index__。
