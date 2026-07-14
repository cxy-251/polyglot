"""066｜``IntEnum``、字符串 mixin、``Flag`` 与 ``IntFlag`` 的互操作语义。

普通 ``Enum`` 提供最强的类型隔离；混入 ``int``/``str`` 会换取旧常量协议兼容，
同时也会让无关枚举通过底层值相等。``Flag`` 用位集合表达可组合选项，
``IntFlag`` 再放宽为可与裸整数位运算。本文件明确这些选择的边界与陷阱。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.enum.IntEnum python.int-enum.integer-subclass
# polyglot-covers: python.int-enum.cross-type-equality python.int-enum.arithmetic-type-loss
# polyglot-covers: python.int-enum.python310-str-format python.int-enum.integer-workflows
# polyglot-covers: python.enum.typed-mixin python.enum.mixin-base-order
# polyglot-covers: python.enum.string-mixin python.enum.mixin-value-identity
# polyglot-covers: python.enum.Flag python.flag.auto-powers python.flag.combinations
# polyglot-covers: python.flag.named-composite python.flag.bitwise-operators
# polyglot-covers: python.flag.membership python.flag.zero-false
# polyglot-covers: python.flag.raw-value-lookup python.flag.invalid-bits
# polyglot-covers: python.flag.no-int-interoperability python.flag.class-isolation
# polyglot-covers: python.enum.IntFlag python.int-flag.integer-interoperability
# polyglot-covers: python.int-flag.unknown-bits python.int-flag.arithmetic-type-loss
# polyglot-covers: python.int-flag.python310-complement python.int-flag.zero-false

from enum import auto, Enum, Flag, IntEnum, IntFlag

import pytest


def test_int_enum_is_an_integer_subclass_for_legacy_integer_workflows():
    """IntEnum member 同时是 int，可用于索引、range 等只接受整数协议的位置。"""

    class Position(IntEnum):
        FIRST = 0
        SECOND = 1

    values = ["zero", "one", "two"]

    assert isinstance(Position.SECOND, int)
    assert int(Position.SECOND) == 1
    assert values[Position.SECOND] == "one"
    assert list(range(Position.SECOND + 2)) == [0, 1, 2]


def test_int_enum_equality_crosses_raw_ints_and_unrelated_int_enums():
    """整数相等关系具有传递性，导致两个无关 IntEnum 的同值成员也相等。"""

    class Shape(IntEnum):
        CIRCLE = 1

    class Request(IntEnum):
        POST = 1

    class PlainShape(Enum):
        CIRCLE = 1

    assert Shape.CIRCLE == 1
    assert Request.POST == 1
    assert Shape.CIRCLE == Request.POST
    assert Shape.CIRCLE != PlainShape.CIRCLE
    assert len({Shape.CIRCLE, Request.POST, 1}) == 1


def test_int_enum_supports_integer_ordering_but_loses_type_after_arithmetic():
    """比较沿用 int；普通算术结果也是裸 int，不再携带枚举域信息。"""

    class Level(IntEnum):
        LOW = 1
        HIGH = 3

    assert Level.LOW < Level.HIGH
    assert Level.HIGH > 2

    result = Level.LOW + Level.HIGH
    assert result == 4
    assert type(result) is int
    assert not isinstance(result, Level)


def test_python_310_int_enum_str_and_format_follow_different_paths():
    """3.10 的 str 保留 ``Class.MEMBER``，空 format/f-string 则按混入的 int 展示 value。"""

    class ExitCode(IntEnum):
        SUCCESS = 0

    assert str(ExitCode.SUCCESS) == "ExitCode.SUCCESS"
    assert format(ExitCode.SUCCESS, "") == "0"
    assert f"{ExitCode.SUCCESS}" == "0"
    assert f"{ExitCode.SUCCESS:04d}" == "0000"
    assert "%s" % ExitCode.SUCCESS == "ExitCode.SUCCESS"
    assert "%d" % ExitCode.SUCCESS == "0"


def test_typed_string_enum_interoperates_with_str_but_keeps_enum_identity():
    """把 str 放在 Enum 前会创建字符串子类成员；value 等值但不是成员对象本身。"""

    class HttpMethod(str, Enum):
        GET = "GET"
        POST = "POST"

    assert isinstance(HttpMethod.GET, str)
    assert HttpMethod.GET == "GET"
    assert HttpMethod.GET.lower() == "get"
    assert HttpMethod.GET.value == "GET"
    assert HttpMethod.GET.value is not HttpMethod.GET
    assert type(HttpMethod.GET.value) is str


def test_python_310_string_mixin_str_and_format_also_take_different_paths():
    """Enum.__str__ 展示符号身份；格式化默认委托混入的 str，适合旧字符串 API。"""

    class HttpMethod(str, Enum):
        GET = "GET"

    assert str(HttpMethod.GET) == "HttpMethod.GET"
    assert format(HttpMethod.GET, "") == "GET"
    assert f"method={HttpMethod.GET}" == "method=GET"
    assert f"{HttpMethod.GET:>5}" == "  GET"


def test_concrete_mixin_must_precede_enum_in_the_base_list():
    """合法基类顺序是 mixin、具体数据类型、Enum；把 Enum 放前面会在建类时失败。"""

    with pytest.raises(TypeError, match="new enumerations should be created as"):

        class Broken(Enum, str):
            VALUE = "value"


def test_flag_auto_assigns_powers_of_two_for_independent_bits():
    """Flag 的 auto 生成 1、2、4……，保证每个基础成员占一个独立 bit。"""

    class Permission(Flag):
        READ = auto()
        WRITE = auto()
        EXECUTE = auto()

    assert [member.value for member in Permission] == [1, 2, 4]
    assert Permission.READ.value & Permission.WRITE.value == 0


def test_flag_or_builds_a_same_class_combination_and_and_tests_overlap():
    """``|`` 表示集合并集，``&`` 表示交集；结果继续是同一个 Flag 类型。"""

    class Permission(Flag):
        READ = auto()
        WRITE = auto()
        EXECUTE = auto()

    read_write = Permission.READ | Permission.WRITE

    assert type(read_write) is Permission
    assert read_write.value == 3
    assert read_write & Permission.READ is Permission.READ
    assert read_write & Permission.EXECUTE == Permission(0)


def test_named_flag_combination_reuses_the_declared_member():
    """常用组合可以命名；同一 bit pattern 的后续运算会解析为那个单例成员。"""

    class Permission(Flag):
        READ = auto()
        WRITE = auto()
        EXECUTE = auto()
        READ_WRITE = READ | WRITE

    combined = Permission.READ | Permission.WRITE

    assert combined is Permission.READ_WRITE
    assert Permission(3) is Permission.READ_WRITE
    assert Permission.READ_WRITE.name == "READ_WRITE"


def test_flag_xor_toggles_bits_and_complement_is_limited_to_known_flags():
    """异或切换 bit；普通 Flag 的取反只返回已声明 bit 中当前未设置的部分。"""

    class Feature(Flag):
        SEARCH = auto()
        EXPORT = auto()
        AUDIT = auto()

    selected = Feature.SEARCH | Feature.EXPORT

    assert selected ^ Feature.EXPORT is Feature.SEARCH
    assert selected ^ Feature.AUDIT == Feature.SEARCH | Feature.EXPORT | Feature.AUDIT
    assert ~Feature.SEARCH == Feature.EXPORT | Feature.AUDIT


def test_flag_contains_checks_whether_all_bits_of_a_member_are_present():
    """``part in whole`` 是 bit 子集判断，不是类成员迭代；组合也可作为 part。"""

    class Permission(Flag):
        READ = auto()
        WRITE = auto()
        EXECUTE = auto()

    selected = Permission.READ | Permission.WRITE

    assert Permission.READ in selected
    assert Permission.WRITE in selected
    assert Permission.EXECUTE not in selected
    assert selected in selected
    assert Permission(0) in selected


def test_zero_flag_is_false_even_when_the_zero_state_has_a_name():
    """无 bit 状态的布尔值固定为 False；给它 BLACK/NONE 等名称不会改变这一点。"""

    class Feature(Flag):
        NONE = 0
        SEARCH = auto()
        EXPORT = auto()

    assert Feature(0) is Feature.NONE
    assert not Feature.NONE
    assert not (Feature.SEARCH & Feature.EXPORT)
    assert bool(Feature.SEARCH)


def test_flag_value_lookup_accepts_known_combinations_but_rejects_unknown_bits():
    """普通 Flag 可从已声明 bit 的任意组合构造；出现未知 bit 时抛 ValueError。"""

    class Permission(Flag):
        READ = 1
        WRITE = 2

    assert Permission(3) == Permission.READ | Permission.WRITE

    with pytest.raises(ValueError, match="not a valid Permission"):
        Permission(4)


def test_plain_flag_refuses_raw_integer_bitwise_operations():
    """Flag 保持枚举域隔离，不能直接和 int 组合；需要先显式转换并接受校验。"""

    class Permission(Flag):
        READ = 1
        WRITE = 2

    with pytest.raises(TypeError, match="unsupported operand"):
        Permission.READ | 2


def test_flags_from_different_classes_cannot_be_combined_or_compared_equal():
    """bit 数值相同也不代表语义域相同；普通 Flag 阻止跨类按位运算。"""

    class Permission(Flag):
        READ = 1

    class Feature(Flag):
        READ = 1

    assert Permission.READ != Feature.READ
    with pytest.raises(TypeError, match="unsupported operand"):
        Permission.READ | Feature.READ


def test_int_flag_bitwise_operations_preserve_type_and_accept_raw_ints():
    """IntFlag 为系统掩码互操作而放宽边界；按位结果仍携带 IntFlag 类型。"""

    class Permission(IntFlag):
        READ = 4
        WRITE = 2
        EXECUTE = 1

    combined = Permission.READ | 2

    assert type(combined) is Permission
    assert combined == Permission.READ | Permission.WRITE
    assert combined & 4 is Permission.READ
    assert combined.value == 6


def test_int_flag_accepts_unknown_bits_and_preserves_them_in_pseudo_members():
    """和裸系统掩码互操作时未知 bit 不报错；value 原样保留，名称是合成诊断信息。"""

    class Permission(IntFlag):
        READ = 4
        WRITE = 2
        EXECUTE = 1

    value = Permission.EXECUTE | 8

    assert isinstance(value, Permission)
    assert value.value == 9
    assert value.name == "8|EXECUTE"
    assert Permission(9) is value


def test_int_flag_arithmetic_loses_membership_while_bitwise_operations_keep_it():
    """只有 &, |, ^, ~ 走 flag 组合协议；加减乘除沿用 int 并返回裸数值。"""

    class Permission(IntFlag):
        READ = 4
        WRITE = 2

    bitwise = Permission.READ | Permission.WRITE
    arithmetic = Permission.READ + Permission.WRITE

    assert isinstance(bitwise, Permission)
    assert arithmetic == 6
    assert type(arithmetic) is int


def test_python_310_int_flag_complement_can_produce_a_negative_value():
    """3.10 的 IntFlag 取反沿用整数补码，可得到负 pseudo-member；后续 Python 已改变展示语义。"""

    class Permission(IntFlag):
        READ = 4
        WRITE = 2
        EXECUTE = 1
        ALL = READ | WRITE | EXECUTE

    complement = ~Permission.ALL

    assert isinstance(complement, Permission)
    assert complement.value == -8
    assert int(complement) == -8


def test_int_flag_zero_is_false_and_containment_uses_bit_subsets():
    """IntFlag 的 0 同样为假；``part in whole`` 仍要求 part 的全部 bit 已设置。"""

    class Permission(IntFlag):
        NONE = 0
        READ = 4
        WRITE = 2

    selected = Permission.READ | Permission.WRITE

    assert not Permission.NONE
    assert Permission.READ in selected
    assert Permission.NONE in selected
    assert Permission(1) not in selected
