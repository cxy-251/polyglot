"""055｜``enum`` 成员身份、别名、自动值、查找与定制协议。

普通 ``Enum`` 把一组符号名绑定到预先创建的单例成员。成员可携带任意值和行为，
但普通枚举刻意不等同于底层值。本文件还覆盖 ``EnumMeta`` 提供的迭代/查找、
``auto``、``_missing_``、``_ignore_``、函数式 API 与 ``__new__`` 创建协议。

这些案例面向 Python 3.10。
"""

# polyglot-covers: python.enum.Enum python.enum.member-singleton
# polyglot-covers: python.enum.name python.enum.value python.enum.str-repr
# polyglot-covers: python.enum.iteration python.enum.hashable python.enum.membership
# polyglot-covers: python.enum.value-lookup python.enum.name-lookup python.enum.lookup-errors
# polyglot-covers: python.enum.alias python.enum.__members__ python.enum.unique
# polyglot-covers: python.enum.auto python.enum._generate_next_value_
# polyglot-covers: python.enum.identity-comparison python.enum.no-ordering python.enum.truthiness
# polyglot-covers: python.enum.methods python.enum.descriptors python.enum.custom-str
# polyglot-covers: python.enum.restricted-subclassing python.enum.behavior-mixin
# polyglot-covers: python.enum.functional-api python.enum.functional-start
# polyglot-covers: python.enum.functional-type
# polyglot-covers: python.enum._missing_ python.enum._ignore_
# polyglot-covers: python.enum.__new__ python.enum.__init__ python.enum._value_
# polyglot-covers: python.enum.member-rebinding python.enum.mutable-value
# polyglot-covers: python.enum.pickle-identity python.enum.python310-nonmember-containment




from enum import auto, Enum, unique
import pickle
import pytest
from enum import auto, Enum, Flag, IntEnum, IntFlag

class PickleStatus(Enum):
    """放在模块顶层，pickle 才能通过模块名和限定名重新找到这个 Enum。"""

    READY = "ready"
    DONE = "done"


def test_enum_members_expose_symbolic_name_value_and_diagnostic_representations():
    """成员类型就是枚举类；str 强调符号名，repr 还展示底层 value。"""

    class Color(Enum):
        RED = 1
        GREEN = 2

    member = Color.RED

    assert type(member) is Color
    assert member.name == "RED"
    assert member.value == 1
    assert str(member) == "Color.RED"
    assert repr(member) == "<Color.RED: 1>"


def test_enum_members_are_singletons_and_value_construction_is_lookup():
    """类创建时已经造好全部成员；之后 ``Color(value)`` 返回既有单例而非新实例。"""

    class Color(Enum):
        RED = 1
        BLUE = 2

    first = Color.RED
    second = Color(1)

    assert first is second
    assert Color(Color.RED) is Color.RED


def test_iteration_uses_definition_order_and_members_are_hashable_keys():
    """迭代次序稳定为定义顺序；成员 identity 稳定，因此适合作为 mapping key。"""

    class Priority(Enum):
        HIGH = 30
        LOW = 10
        MEDIUM = 20

    labels = {
        Priority.HIGH: "urgent",
        Priority.MEDIUM: "normal",
    }

    assert list(Priority) == [Priority.HIGH, Priority.LOW, Priority.MEDIUM]
    assert labels[Priority(20)] == "normal"


def test_lookup_by_value_and_name_use_different_call_and_subscription_syntax():
    """``Status(value)`` 按 value；``Status[name]`` 按符号名，二者不要混用。"""

    class Status(Enum):
        PENDING = "pending"
        RUNNING = "running"

    assert Status("running") is Status.RUNNING
    assert Status["RUNNING"] is Status.RUNNING

    with pytest.raises(ValueError, match="not a valid"):
        Status("RUNNING")
    with pytest.raises(KeyError, match="running"):
        Status["running"]


def test_duplicate_values_create_aliases_that_share_one_member_identity():
    """同值的后定义名称默认是别名；按 value 查找总是返回第一个 canonical member。"""

    class ExitCode(Enum):
        SUCCESS = 0
        OK = 0
        FAILURE = 1

    assert ExitCode.OK is ExitCode.SUCCESS
    assert ExitCode.OK.name == "SUCCESS"
    assert ExitCode(0) is ExitCode.SUCCESS
    assert ExitCode["OK"] is ExitCode.SUCCESS


def test_iteration_skips_aliases_while_members_mapping_includes_every_name():
    """常规迭代只给 canonical 成员；审计别名应读取只读的 ``__members__``。"""

    class ExitCode(Enum):
        SUCCESS = 0
        OK = 0
        FAILURE = 1

    assert list(ExitCode) == [ExitCode.SUCCESS, ExitCode.FAILURE]
    assert list(ExitCode.__members__) == ["SUCCESS", "OK", "FAILURE"]
    assert ExitCode.__members__["OK"] is ExitCode.SUCCESS

    with pytest.raises(TypeError):
        ExitCode.__members__["NEW"] = ExitCode.SUCCESS


def test_unique_decorator_rejects_value_aliases_during_class_creation():
    """业务要求一值一名时使用 ``@unique``，错误会同时指出 alias 和原名称。"""

    with pytest.raises(ValueError, match=r"OK -> SUCCESS"):

        @unique
        class ExitCode(Enum):
            SUCCESS = 0
            OK = 0


def test_reusing_the_same_member_name_is_always_an_error():
    """值可以形成别名，名称却不能在同一 enum class body 中定义两次。"""

    with pytest.raises(TypeError, match="Attempted to reuse key"):

        class Broken(Enum):
            VALUE = 1
            VALUE = 2


def test_auto_assigns_increasing_values_for_plain_enum():
    """普通 Enum 的 auto 默认从 1 开始递增；不要让业务协议依赖隐式编号。"""

    class Direction(Enum):
        NORTH = auto()
        EAST = auto()
        SOUTH = auto()

    assert [member.value for member in Direction] == [1, 2, 3]
    assert all(Direction)


def test_generate_next_value_can_derive_stable_values_from_member_names():
    """钩子在成员创建前执行，可根据 name/start/count/last_values 自定义 auto。"""

    calls = []

    class Header(Enum):
        def _generate_next_value_(name, start, count, last_values):
            calls.append((name, start, count, tuple(last_values)))
            return name.lower().replace("_", "-")

        CONTENT_TYPE = auto()
        USER_AGENT = auto()

    assert Header.CONTENT_TYPE.value == "content-type"
    assert Header.USER_AGENT.value == "user-agent"
    assert calls == [
        ("CONTENT_TYPE", 1, 0, ()),
        ("USER_AGENT", 1, 1, ("content-type",)),
    ]


def test_generate_next_value_must_be_declared_before_auto_members():
    """先出现 auto 再替换生成器会使同一 class body 的规则前后不一致，因此被拒绝。"""

    with pytest.raises(TypeError, match="_generate_next_value_"):

        class Broken(Enum):
            FIRST = auto()

            def _generate_next_value_(name, start, count, last_values):
                return name


def test_plain_enum_compares_by_identity_not_by_raw_or_other_enum_values():
    """两个无关 Enum 即使 value 相同也不相等，避免常量域之间意外串通。"""

    class HttpStatus(Enum):
        OK = 200

    class DatabaseStatus(Enum):
        OK = 200

    assert HttpStatus.OK is HttpStatus(200)
    assert HttpStatus.OK != 200
    assert HttpStatus.OK != DatabaseStatus.OK


def test_plain_enum_does_not_invent_ordering_from_underlying_values():
    """value 是数字也不代表成员可排序；若领域需要顺序，应显式定义比较语义。"""

    class Size(Enum):
        SMALL = 1
        LARGE = 2

    with pytest.raises(TypeError, match="not supported"):
        Size.SMALL < Size.LARGE


def test_plain_enum_members_are_truthy_even_when_their_value_is_zero():
    """普通 Enum 的成员都为真；函数式 API 从 1 起步也避免把首成员误作 false。"""

    class Result(Enum):
        SUCCESS = 0
        FAILURE = 1

    assert bool(Result.SUCCESS) is True
    assert bool(Result.FAILURE) is True


def test_enum_can_define_instance_methods_descriptors_classmethods_and_str():
    """方法和 descriptor 不会变成成员，可把领域行为放在符号值旁边。"""

    class Temperature(Enum):
        COLD = 5
        WARM = 25

        @property
        def fahrenheit(self):
            return self.value * 9 / 5 + 32

        def is_freezing(self):
            return self.value <= 0

        @classmethod
        def comfortable(cls):
            return cls.WARM

        def __str__(self):
            return f"{self.value}°C"

    assert Temperature.COLD.fahrenheit == 41
    assert not Temperature.COLD.is_freezing()
    assert Temperature.comfortable() is Temperature.WARM
    assert str(Temperature.WARM) == "25°C"
    assert "fahrenheit" not in Temperature.__members__


def test_enum_with_members_cannot_be_extended_with_more_members():
    """已有成员的 Enum 不可继承扩充，否则基类成员就不再是子类实例，破坏类型不变量。"""

    class Color(Enum):
        RED = 1

    with pytest.raises(TypeError, match="cannot extend enumeration"):

        class MoreColor(Color):
            BLUE = 2


def test_memberless_enum_base_can_share_behavior_across_multiple_enums():
    """没有成员的 Enum 基类可作为行为 mixin，再由各子类分别定义自己的成员域。"""

    class DescribedEnum(Enum):
        def describe(self):
            return f"{type(self).__name__}:{self.name}={self.value}"

    class Color(DescribedEnum):
        RED = 1

    class Size(DescribedEnum):
        SMALL = "s"

    assert Color.RED.describe() == "Color:RED=1"
    assert Size.SMALL.describe() == "Size:SMALL=s"
    assert Color.RED != Size.SMALL


def test_functional_api_accepts_names_and_can_choose_a_start_value():
    """只有名称时自动编号；start 适合适配已有常量，但类语法通常更易读。"""

    Animal = Enum("Animal", "ANT BEE CAT", start=10)

    assert Animal.__name__ == "Animal"
    assert [member.name for member in Animal] == ["ANT", "BEE", "CAT"]
    assert [member.value for member in Animal] == [10, 11, 12]


def test_functional_api_accepts_pairs_and_a_concrete_mixin_type():
    """name/value pairs 可锁定协议值；type=str 让所有成员同时具有字符串行为。"""

    Header = Enum(
        "Header",
        [("CONTENT_TYPE", "content-type"), ("ACCEPT", "accept")],
        type=str,
    )

    assert Header.CONTENT_TYPE.value == "content-type"
    assert isinstance(Header.CONTENT_TYPE, str)
    assert Header.CONTENT_TYPE.upper() == "CONTENT-TYPE"
    assert Header.CONTENT_TYPE == "content-type"


def test_missing_hook_can_normalize_external_values_before_lookup():
    """``_missing_`` 只在正常 value 查找失败后调用，适合受控的兼容/规范化。"""

    class Build(Enum):
        DEBUG = "debug"
        OPTIMIZED = "optimized"

        @classmethod
        def _missing_(cls, value):
            if isinstance(value, str):
                normalized = value.casefold()
                for member in cls:
                    if member.value == normalized:
                        return member
            return None

    assert Build("DEBUG") is Build.DEBUG
    assert Build("Optimized") is Build.OPTIMIZED
    with pytest.raises(ValueError):
        Build("unknown")


def test_ignore_keeps_class_body_helpers_out_of_the_final_enum():
    """``_ignore_`` 列出的临时变量不会成为成员，而且类创建后会从 namespace 删除。"""

    class HttpCode(Enum):
        _ignore_ = "label temporary"
        label = "unused helper"
        temporary = 999
        OK = 200
        NOT_FOUND = 404

    assert list(HttpCode) == [HttpCode.OK, HttpCode.NOT_FOUND]
    assert "label" not in HttpCode.__members__
    assert not hasattr(HttpCode, "label")
    assert not hasattr(HttpCode, "temporary")


def test_new_controls_actual_value_while_init_attaches_additional_metadata():
    """需要变换真正 value 时用 __new__ 并设置 _value_；其他字段优先在 __init__ 填充。"""

    class HttpStatus(Enum):
        def __new__(cls, code, phrase):
            member = object.__new__(cls)
            member._value_ = code
            return member

        def __init__(self, code, phrase):
            self.phrase = phrase

        OK = (200, "OK")
        NOT_FOUND = (404, "Not Found")

    assert HttpStatus.OK.value == 200
    assert HttpStatus.OK.phrase == "OK"
    assert HttpStatus(404) is HttpStatus.NOT_FOUND
    assert HttpStatus.NOT_FOUND.value != (404, "Not Found")


def test_custom_new_is_used_for_creation_then_enum_new_handles_later_lookups():
    """自定义 __new__ 只在 class 构建成员时运行；类完成后调用 Enum(value) 只是查表。"""

    created = []

    class Code(Enum):
        def __new__(cls, value):
            created.append(value)
            member = object.__new__(cls)
            member._value_ = value
            return member

        ONE = 1
        TWO = 2

    assert created == [1, 2]
    assert Code(1) is Code.ONE
    assert Code(2) is Code.TWO
    assert created == [1, 2]


def test_enum_member_names_cannot_be_rebound_but_mutable_values_remain_mutable():
    """符号绑定受元类保护；value 若选择可变对象，其内容并不会因此自动冻结。"""

    class Registry(Enum):
        PLUGINS = []

    with pytest.raises(AttributeError, match=r"(?i)cannot reassign members"):
        Registry.PLUGINS = ["replacement"]

    Registry.PLUGINS.value.append("loaded")
    assert Registry.PLUGINS.value == ["loaded"]


def test_pickle_round_trip_resolves_a_top_level_enum_member_to_the_same_singleton():
    """可导入的顶层 Enum 以符号类型重新定位；反序列化不会制造第二个成员对象。"""

    restored = pickle.loads(pickle.dumps(PickleStatus.DONE))

    assert restored is PickleStatus.DONE


def test_python_310_enum_containment_rejects_raw_values_instead_of_looking_them_up():
    """3.10 的 ``member in EnumClass`` 只接受成员；裸 value 会抛 TypeError（后续版本已改变）。"""

    class Color(Enum):
        RED = 1

    assert Color.RED in Color
    with pytest.warns(DeprecationWarning, match="__contains__"):
        with pytest.raises(TypeError):
            1 in Color


# ``IntEnum``、字符串 mixin、``Flag`` 与 ``IntFlag`` 的互操作语义。
#
# 普通 ``Enum`` 提供最强的类型隔离；混入 ``int``/``str`` 会换取旧常量协议兼容，
# 同时也会让无关枚举通过底层值相等。``Flag`` 用位集合表达可组合选项，
# ``IntFlag`` 再放宽为可与裸整数位运算。本文件明确这些选择的边界与陷阱。
#
# 这些案例面向 Python 3.10。

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

    with pytest.raises(ValueError, match="not a valid"):
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
    """和裸系统掩码互操作时未知 bit 不报错；value 原样保留。"""

    class Permission(IntFlag):
        READ = 4
        WRITE = 2
        EXECUTE = 1

    value = Permission.EXECUTE | 8

    assert isinstance(value, Permission)
    assert value.value == 9
    assert value.name is None
    assert "8|EXECUTE" in repr(value)
    assert Permission(9) is value
    # 3.10 的 pseudo-member 没有正式 name，repr 才合成未知 bit 与已知成员；
    # 不能把诊断文本当成可按名称查找的成员。


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
