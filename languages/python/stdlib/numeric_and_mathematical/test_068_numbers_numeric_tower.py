"""068｜``numbers`` 数值抽象基类、跨类型相等与算术双分派。

``Number -> Complex -> Real -> Rational -> Integral`` 是逐层增强的能力分类，
适合判断调用者真正需要哪组数值协议。它不是要求所有“看起来像数字”的类型强行继承
同一个具体实现。本文件也用 ``Fraction`` 和最小自定义类型展示混合算术的
``__op__`` / ``__rop__`` fallback 规则。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.numbers.Number python.numbers.numeric-tower
# polyglot-covers: python.numbers.Complex python.numbers.Real
# polyglot-covers: python.numbers.Rational python.numbers.Integral
# polyglot-covers: python.numbers.builtin-classification python.numbers.bool-is-integral
# polyglot-covers: python.numbers.abstract-operations python.numbers.virtual-subclass
# polyglot-covers: python.numbers.extensible-tower python.numbers.abc-register
# polyglot-covers: python.numbers.rational-invariants python.numbers.cross-type-hash
# polyglot-covers: python.numbers.mixed-mode-arithmetic python.numbers.builtin-fallback
# polyglot-covers: python.numeric-dispatch.NotImplemented python.numeric-dispatch.reflected-operation
# polyglot-covers: python.numeric-dispatch.subclass-priority python.numeric-dispatch.type-error

from abc import abstractmethod
from fractions import Fraction
import numbers

import pytest


def test_numeric_tower_abc_subclass_relationships_run_from_specific_to_general():
    """越靠下的 ABC 承诺越多；Integral 同时满足上方所有数值类别。"""

    assert issubclass(numbers.Integral, numbers.Rational)
    assert issubclass(numbers.Rational, numbers.Real)
    assert issubclass(numbers.Real, numbers.Complex)
    assert issubclass(numbers.Complex, numbers.Number)

    assert not issubclass(numbers.Real, numbers.Rational)
    assert not issubclass(numbers.Complex, numbers.Real)


def test_builtin_numeric_types_enter_the_tower_at_different_levels():
    """int、float、complex 分别停在 Integral、Real、Complex；不要只检查 Number 后猜能力。"""

    assert isinstance(3, numbers.Integral)
    assert isinstance(3, numbers.Rational)
    assert isinstance(3, numbers.Real)
    assert isinstance(3, numbers.Complex)
    assert isinstance(3, numbers.Number)

    assert isinstance(3.5, numbers.Real)
    assert not isinstance(3.5, numbers.Rational)

    assert isinstance(3 + 4j, numbers.Complex)
    assert not isinstance(3 + 4j, numbers.Real)


def test_bool_is_integral_because_bool_is_a_subclass_of_int():
    """``True``/``False`` 会通过 Integral 检查；若布尔值在业务上无效，必须额外排除。"""

    assert issubclass(bool, int)
    assert isinstance(True, numbers.Integral)
    assert isinstance(False, numbers.Number)

    def require_non_boolean_integer(value):
        if isinstance(value, bool) or not isinstance(value, numbers.Integral):
            raise TypeError("a non-boolean integer is required")
        return int(value)

    assert require_non_boolean_integer(7) == 7
    with pytest.raises(TypeError, match="non-boolean integer"):
        require_non_boolean_integer(True)


def test_fraction_is_rational_and_exposes_normalized_integral_components():
    """Rational 要求分子分母为 Integral、约至最简且分母为正；Fraction 落实这些不变量。"""

    value = Fraction(-6, -8)

    assert isinstance(value, numbers.Rational)
    assert isinstance(value, numbers.Real)
    assert not isinstance(value, numbers.Integral)
    assert value == Fraction(3, 4)
    assert value.numerator == 3
    assert value.denominator == 4
    assert isinstance(value.numerator, numbers.Integral)


def test_each_tower_level_corresponds_to_additional_protocols():
    """实例展示各层新增能力：complex components、real rounding、rational parts、integer bits。"""

    complex_value = 3 + 4j
    real_value = 3.75
    rational_value = Fraction(7, 3)
    integral_value = 6

    assert complex_value.real == 3
    assert complex_value.imag == 4
    assert complex_value.conjugate() == 3 - 4j
    assert abs(complex_value) == 5

    assert round(real_value) == 4
    assert real_value // 2 == 1.0
    assert divmod(real_value, 2) == (1.0, 1.75)

    assert (rational_value.numerator, rational_value.denominator) == (7, 3)
    assert integral_value << 1 == 12
    assert integral_value & 3 == 2


@pytest.mark.parametrize(
    "abstract_type",
    [numbers.Complex, numbers.Real, numbers.Rational, numbers.Integral],
)
def test_specific_numeric_abcs_cannot_be_instantiated_without_abstract_operations(abstract_type):
    """这些类描述协议而非现成数值；缺少抽象运算的直接实例化会被 ABCMeta 拒绝。"""

    assert abstract_type.__abstractmethods__
    with pytest.raises(TypeError, match="abstract class"):
        abstract_type()


def test_number_is_a_broad_classification_not_a_specific_arithmetic_contract():
    """只需要 abs 的函数可接收 Number；需要 floor/bit 操作时应选择更具体 ABC。"""

    def magnitude(value):
        if not isinstance(value, numbers.Number):
            raise TypeError("number required")
        return abs(value)

    assert magnitude(-4) == 4
    assert magnitude(3 + 4j) == 5
    with pytest.raises(TypeError, match="number required"):
        magnitude("4")


def test_virtual_registration_changes_classification_but_does_not_mix_in_methods():
    """ABC.register 只声明外部类型符合协议；它不会复制 Real 的默认属性或实现。"""

    class ExternalMeasurement:
        pass

    numbers.Real.register(ExternalMeasurement)
    value = ExternalMeasurement()

    assert isinstance(value, numbers.Real)
    assert isinstance(value, numbers.Number)
    assert not hasattr(value, "real")
    with pytest.raises(TypeError):
        float(value)


def test_a_domain_abc_can_be_inserted_between_complex_and_real():
    """自定义层继承 Complex，再把 Real 注册为虚拟子类，就能扩展而不修改标准数值塔。"""

    class Measurable(numbers.Complex):
        @abstractmethod
        def uncertainty(self):
            """返回该数值的测量误差。"""

    Measurable.register(numbers.Real)

    assert issubclass(numbers.Real, Measurable)
    assert isinstance(1.5, Measurable)
    assert isinstance(2, Measurable)
    assert not isinstance(1 + 2j, Measurable)


def test_equal_values_from_different_numeric_types_must_share_the_same_hash():
    """跨类型相等必须满足 hash 不变量，否则 dict/set 会保存逻辑重复的 key。"""

    integer = 2
    rational = Fraction(2, 1)
    real = 2.0
    complex_value = 2 + 0j

    assert integer == rational == real == complex_value
    assert hash(integer) == hash(rational) == hash(real) == hash(complex_value)
    assert len({integer, rational, real, complex_value}) == 1


def test_fraction_hashes_like_an_exactly_equal_float_when_equality_is_exact():
    """二分数可被 float 精确表示时也要共享 hash；不可精确表示时通常并不相等。"""

    exact = Fraction(1, 2)
    inexact = Fraction(1, 10)

    assert exact == 0.5
    assert hash(exact) == hash(0.5)

    assert inexact != 0.1
    assert float(inexact) == 0.1


def test_fraction_mixed_arithmetic_preserves_exactness_until_a_wider_fallback_is_needed():
    """已知 int/Fraction 时返回 Fraction；遇到 float/complex 则转换到最近共同内置类型。"""

    value = Fraction(1, 3)

    with_integer = value + 1
    with_fraction = value + Fraction(1, 6)
    with_float = value + 0.5
    with_complex = value + 1j

    assert with_integer == Fraction(4, 3)
    assert type(with_integer) is Fraction
    assert with_fraction == Fraction(1, 2)
    assert type(with_fraction) is Fraction
    assert type(with_float) is float
    assert with_float == float(value) + 0.5
    assert type(with_complex) is complex
    assert with_complex == complex(value) + 1j


def test_reverse_fraction_operation_handles_a_left_hand_integral():
    """``int + Fraction`` 先给 int.__add__，其 NotImplemented 让 Fraction.__radd__ 保留精度。"""

    result = 2 + Fraction(1, 3)

    assert result == Fraction(7, 3)
    assert type(result) is Fraction


def test_notimplemented_from_forward_operation_gives_reflected_operation_a_chance():
    """运算方法应返回 NotImplemented（不是抛异常），让右操作数处理它认识的组合。"""

    calls = []

    class LeftNumber:
        def __add__(self, other):
            calls.append("left.__add__")
            return NotImplemented

    class RightNumber:
        def __radd__(self, other):
            calls.append("right.__radd__")
            return "handled by right"

    assert LeftNumber() + RightNumber() == "handled by right"
    assert calls == ["left.__add__", "right.__radd__"]


def test_right_subclass_reflected_method_gets_priority_over_left_base_method():
    """右侧类型是左侧类型子类时，Python 先试更具体的子类 __radd__。"""

    calls = []

    class BaseNumber:
        def __add__(self, other):
            calls.append("base.__add__")
            return "base result"

    class SpecializedNumber(BaseNumber):
        def __radd__(self, other):
            calls.append("specialized.__radd__")
            return "specialized result"

    result = BaseNumber() + SpecializedNumber()

    assert result == "specialized result"
    assert calls == ["specialized.__radd__"]


def test_type_error_is_raised_only_after_both_arithmetic_sides_decline():
    """双方都返回 NotImplemented 后，解释器才产生最终的 unsupported operand TypeError。"""

    calls = []

    class LeftNumber:
        def __add__(self, other):
            calls.append("left")
            return NotImplemented

    class RightNumber:
        def __radd__(self, other):
            calls.append("right")
            return NotImplemented

    with pytest.raises(TypeError, match="unsupported operand"):
        LeftNumber() + RightNumber()

    assert calls == ["left", "right"]
