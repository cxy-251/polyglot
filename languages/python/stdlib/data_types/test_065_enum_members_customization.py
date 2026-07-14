"""065｜``enum`` 成员身份、别名、自动值、查找与定制协议。

普通 ``Enum`` 把一组符号名绑定到预先创建的单例成员。成员可携带任意值和行为，
但普通枚举刻意不等同于底层值。本文件还覆盖 ``EnumMeta`` 提供的迭代/查找、
``auto``、``_missing_``、``_ignore_``、函数式 API 与 ``__new__`` 创建协议。

这些案例面向 Python 3.10；当前文件尚未经过 pytest 验证。
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
# polyglot-covers: python.enum.functional-api python.enum.functional-start python.enum.functional-type
# polyglot-covers: python.enum._missing_ python.enum._ignore_
# polyglot-covers: python.enum.__new__ python.enum.__init__ python.enum._value_
# polyglot-covers: python.enum.member-rebinding python.enum.mutable-value
# polyglot-covers: python.enum.pickle-identity python.enum.python310-nonmember-containment

from enum import auto, Enum, unique
import pickle

import pytest


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

    with pytest.raises(ValueError, match="not a valid Status"):
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

    with pytest.raises(AttributeError, match="cannot reassign member"):
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
    with pytest.raises(TypeError):
        1 in Color
