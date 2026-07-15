"""155｜dataclasses：生成方法、字段策略、继承和复制。

``@dataclass`` 不是普通“数据容器”标签，而是读取类注解后生成数据模型
特殊方法的代码生成器。本套从 ``__init__``、``__repr__``、比较和哈希
一路追到字段元数据、``InitVar``、冻结、关键字专用参数、模式匹配、
slots、继承与描述符字段，并用
``fields/asdict/replace/make_dataclass`` 展示常见工作流。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.dataclasses python.dataclasses.dataclass
# polyglot-covers: python.dataclasses.generated-init python.dataclasses.generated-repr
# polyglot-covers: python.dataclasses.generated-eq python.dataclasses.identical-type-eq
# polyglot-covers: python.dataclasses.order python.dataclasses.order-requires-eq
# polyglot-covers: python.dataclasses.existing-methods
# polyglot-covers: python.dataclasses.field-order python.dataclasses.default-order-error
# polyglot-covers: python.dataclasses.field python.dataclasses.field-options
# polyglot-covers: python.dataclasses.default-factory python.dataclasses.mutable-default
# polyglot-covers: python.dataclasses.missing-sentinel
# polyglot-covers: python.dataclasses.fields python.dataclasses.field-metadata
# polyglot-covers: python.dataclasses.class-var python.dataclasses.init-var
# polyglot-covers: python.dataclasses.post-init python.dataclasses.base-init
# polyglot-covers: python.dataclasses.frozen python.dataclasses.frozen-instance-error
# polyglot-covers: python.dataclasses.object-setattr-frozen
# polyglot-covers: python.dataclasses.hash-matrix python.dataclasses.unsafe-hash
# polyglot-covers: python.dataclasses.field-compare-hash
# polyglot-covers: python.dataclasses.inheritance python.dataclasses.reverse-mro-fields
# polyglot-covers: python.dataclasses.field-override
# polyglot-covers: python.dataclasses.kw-only python.dataclasses.kw-only-sentinel
# polyglot-covers: python.dataclasses.keyword-parameter-reordering
# polyglot-covers: python.dataclasses.match-args python.dataclasses.structural-patterns
# polyglot-covers: python.dataclasses.slots python.dataclasses.slots-new-class
# polyglot-covers: python.dataclasses.descriptor-typed-field
# polyglot-covers: python.dataclasses.asdict python.dataclasses.astuple
# polyglot-covers: python.dataclasses.deep-copy python.dataclasses.custom-factories
# polyglot-covers: python.dataclasses.shallow-copy-recipe
# polyglot-covers: python.dataclasses.replace python.dataclasses.replace-post-init
# polyglot-covers: python.dataclasses.replace-init-var python.dataclasses.replace-init-false
# polyglot-covers: python.dataclasses.is-dataclass python.dataclasses.make-dataclass

from dataclasses import asdict
from dataclasses import astuple
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import FrozenInstanceError
from dataclasses import InitVar
from dataclasses import is_dataclass
from dataclasses import KW_ONLY
from dataclasses import make_dataclass
from dataclasses import MISSING
from dataclasses import replace
import inspect
from typing import Any
from typing import ClassVar

import pytest


@dataclass
class InventoryItem:
    name: str
    unit_price: float
    quantity: int = 0

    def total(self):
        return self.unit_price * self.quantity


def test_default_decorator_generates_init_repr_and_identical_type_equality():
    item = InventoryItem("notebook", 3.5, quantity=4)

    assert (item.name, item.unit_price, item.quantity) == ("notebook", 3.5, 4)
    assert item.total() == 14.0
    assert repr(item) == "InventoryItem(name='notebook', unit_price=3.5, quantity=4)"
    assert item == InventoryItem("notebook", 3.5, 4)

    @dataclass
    class SpecializedItem(InventoryItem):
        pass

    # 生成的 __eq__ 要求两边类型完全相同，而不是 isinstance 关系。
    assert item != SpecializedItem("notebook", 3.5, 4)


def test_field_definition_order_controls_generated_signatures_and_repr():
    signature = inspect.signature(InventoryItem)
    assert list(signature.parameters) == ["name", "unit_price", "quantity"]
    assert signature.parameters["quantity"].default == 0

    with pytest.raises(TypeError, match="non-default argument"):

        @dataclass
        class InvalidOrder:
            optional: int = 1
            required: int


def test_existing_init_and_repr_are_respected_instead_of_overwritten():
    @dataclass
    class CustomMethods:
        value: int

        def __init__(self, raw):
            self.value = int(raw) * 2

        def __repr__(self):
            return f"custom:{self.value}"

    instance = CustomMethods("4")
    assert instance.value == 8
    assert repr(instance) == "custom:8"


def test_order_generates_tuple_like_relations_and_requires_equality():
    @dataclass(order=True)
    class Version:
        major: int
        minor: int

    assert Version(3, 9) < Version(3, 10)
    assert Version(3, 10) >= Version(3, 10)
    with pytest.raises(TypeError):
        Version(3, 10) < (3, 10)

    with pytest.raises(ValueError, match="eq must be true"):

        @dataclass(order=True, eq=False)
        class InvalidOrdering:
            value: int


def test_order_rejects_a_user_defined_comparison_it_would_replace():
    with pytest.raises(TypeError, match="Cannot overwrite attribute __lt__"):

        @dataclass(order=True)
        class ConflictingOrder:
            value: int

            def __lt__(self, other):
                return self.value > other.value


def test_field_options_control_init_repr_and_comparison_independently():
    @dataclass(order=True)
    class Account:
        identifier: int
        display_name: str = field(compare=False)
        password_hash: str = field(repr=False, compare=False, default="hidden")
        normalized: str = field(init=False, compare=True)

        def __post_init__(self):
            self.normalized = self.display_name.casefold()

    account = Account(7, "Alice", password_hash="secret")
    same_sort_key = Account(7, "ALICE", password_hash="different")

    assert "secret" not in repr(account)
    assert "password_hash" not in repr(account)
    assert account == same_sort_key
    assert "normalized" not in inspect.signature(Account).parameters


def test_default_factory_creates_fresh_mutable_state_per_instance():
    calls = []

    def make_tags():
        calls.append("factory called")
        return []

    @dataclass
    class Document:
        title: str
        tags: list = field(default_factory=make_tags)

    first = Document("first")
    second = Document("second")
    first.tags.append("python")

    assert first.tags == ["python"]
    assert second.tags == []
    assert first.tags is not second.tags
    assert calls == ["factory called", "factory called"]


def test_python_310_rejects_builtin_mutable_defaults_at_class_creation():
    for mutable_default in ([], {}, set()):
        with pytest.raises(ValueError, match="mutable default"):
            dataclass(
                type(
                    "InvalidMutableDefault",
                    (),
                    {
                        "__annotations__": {"value": type(mutable_default)},
                        "value": mutable_default,
                    },
                )
            )
    # Python 3.10 专门检测 list/dict/set；这不是深层不可变性证明。
    # 正确表达“每个实例一个容器”的方式仍是 default_factory。


def test_field_default_and_default_factory_are_mutually_exclusive():
    with pytest.raises(ValueError, match="cannot specify both"):
        field(default=[], default_factory=list)


def test_fields_exposes_documented_metadata_and_missing_sentinels():
    @dataclass
    class Record:
        identifier: int = field(metadata={"database": {"column": "record_id"}})
        label: str = "untitled"
        tags: list = field(default_factory=list, repr=False)

    identifier, label, tags = fields(Record)
    assert identifier.name == "identifier"
    assert identifier.type is int
    assert identifier.default is MISSING
    assert identifier.default_factory is MISSING
    assert identifier.metadata["database"]["column"] == "record_id"
    with pytest.raises(TypeError):
        identifier.metadata["new"] = "read only"

    assert label.default == "untitled"
    assert tags.default_factory is list
    assert tags.repr is False
    with pytest.raises(TypeError):
        fields(object)


def test_classvar_and_initvar_are_pseudo_fields_with_different_roles():
    @dataclass
    class Connection:
        protocol: ClassVar[str] = "https"
        host: str
        token: InitVar[str]
        authenticated: bool = field(init=False)

        def __post_init__(self, token):
            self.authenticated = token == "valid"

    connection = Connection("example.invalid", token="valid")
    assert connection.protocol == "https"
    assert connection.authenticated is True
    assert [item.name for item in fields(connection)] == ["host", "authenticated"]
    assert "protocol" not in inspect.signature(Connection).parameters
    assert "token" in inspect.signature(Connection).parameters
    assert "token" not in connection.__dict__


def test_post_init_derives_fields_and_calls_a_non_dataclass_base_init():
    class AuditBase:
        def __init__(self):
            self.audit_events = ["base initialized"]

    @dataclass
    class Rectangle(AuditBase):
        width: float
        height: float
        area: float = field(init=False)

        def __post_init__(self):
            super().__init__()
            self.area = self.width * self.height

    rectangle = Rectangle(3, 4)
    assert rectangle.area == 12
    assert rectangle.audit_events == ["base initialized"]
    # 生成的 __init__ 不会自动调用普通基类 __init__；若基类也为 dataclass，
    # 其字段会由派生类的生成初始化器统一处理。


def test_custom_init_disables_automatic_post_init_call():
    @dataclass(init=False)
    class ManualInitialization:
        value: int
        post_initialized: bool = False

        def __init__(self, value):
            self.value = value

        def __post_init__(self):
            self.post_initialized = True

    instance = ManualInitialization(3)
    assert instance.value == 3
    assert instance.post_initialized is False


def test_frozen_instances_raise_a_specific_attribute_error_subclass():
    @dataclass(frozen=True)
    class Coordinate:
        x: int
        y: int

    point = Coordinate(1, 2)
    with pytest.raises(FrozenInstanceError):
        point.x = 10
    with pytest.raises(FrozenInstanceError):
        del point.y
    assert issubclass(FrozenInstanceError, AttributeError)


def test_frozen_post_init_can_use_object_setattr_for_derived_state():
    @dataclass(frozen=True)
    class NormalizedName:
        raw: str
        normalized: str = field(init=False)

        def __post_init__(self):
            object.__setattr__(self, "normalized", self.raw.strip().casefold())

    name = NormalizedName("  Alice  ")
    assert name.normalized == "alice"
    # frozen 只能拦截生成的属性写入协议，不会把内部可变对象递归冻结。


def test_hash_generation_follows_eq_and_frozen_flags():
    @dataclass
    class MutableValue:
        value: int

    @dataclass(frozen=True)
    class FrozenValue:
        value: int

    @dataclass(eq=False)
    class IdentityValue:
        value: int

    assert MutableValue.__hash__ is None
    with pytest.raises(TypeError):
        hash(MutableValue(1))
    assert hash(FrozenValue(1)) == hash(FrozenValue(1))
    assert IdentityValue.__hash__ is object.__hash__
    assert IdentityValue(1) != IdentityValue(1)


def test_unsafe_hash_is_only_safe_when_hash_participating_state_stays_stable():
    @dataclass(unsafe_hash=True)
    class CacheKey:
        key: str
        cache: dict = field(default_factory=dict, compare=False, hash=False)

    value = CacheKey("users")
    original_hash = hash(value)
    value.cache["result"] = [1, 2, 3]
    assert hash(value) == original_hash

    value.key = "orders"
    assert value.key == "orders"
    # 把可变对象放入 set/dict 后再修改参与哈希的字段会破坏查找；
    # unsafe_hash 是程序员对逻辑稳定性的承诺，并不会使对象真的不可变。


def test_field_can_compare_expensive_value_but_exclude_it_from_hash():
    @dataclass(frozen=True)
    class DigestKey:
        namespace: str
        payload: bytes = field(compare=True, hash=False)

    first = DigestKey("events", b"a")
    second = DigestKey("events", b"b")
    assert first != second
    assert hash(first) == hash(second)
    # 相等对象必须同哈希，反过来不要求；排除字段可能增加碰撞但
    # 保持契约。


def test_dataclass_inheritance_collects_fields_in_reverse_mro_and_overrides_them():
    @dataclass
    class Base:
        x: Any = 15.0
        y: int = 0

    @dataclass
    class Derived(Base):
        z: int = 10
        x: int = 15

    assert [item.name for item in fields(Derived)] == ["x", "y", "z"]
    assert fields(Derived)[0].type is int
    assert str(inspect.signature(Derived)) == "(x: int = 15, y: int = 0, z: int = 10) -> None"
    assert Derived() == Derived(15, 0, 10)


def test_default_order_error_can_cross_an_inheritance_boundary():
    @dataclass
    class BaseWithDefault:
        optional: int = 1

    with pytest.raises(TypeError, match="non-default argument"):

        @dataclass
        class InvalidDerived(BaseWithDefault):
            required: int


def test_kw_only_sentinel_marks_all_following_fields_keyword_only():
    @dataclass
    class Point:
        x: float
        _: KW_ONLY
        y: float
        label: str = "point"

    point = Point(1.0, y=2.0)
    assert point == Point(x=1.0, y=2.0, label="point")
    with pytest.raises(TypeError):
        Point(1.0, 2.0)
    assert [item.name for item in fields(Point)] == ["x", "y", "label"]
    assert fields(Point)[1].kw_only is True


def test_kw_only_decorator_and_per_field_override_shape_the_signature():
    @dataclass(kw_only=True)
    class Request:
        method: str
        path: str

    @dataclass
    class Mixed:
        positional: int
        named: int = field(kw_only=True, default=2)

    assert str(inspect.signature(Request)) == "(*, method: str, path: str) -> None"
    assert str(inspect.signature(Mixed)) == "(positional: int, *, named: int = 2) -> None"
    with pytest.raises(TypeError):
        Request("GET", "/")


def test_inherited_keyword_only_fields_are_reordered_after_regular_parameters():
    @dataclass
    class Base:
        x: int = 1
        _: KW_ONLY
        label: str = "base"

    @dataclass
    class Derived(Base):
        y: int = 2
        flag: bool = field(default=False, kw_only=True)

    assert str(inspect.signature(Derived)) == (
        "(x: int = 1, y: int = 2, *, label: str = 'base', "
        "flag: bool = False) -> None"
    )


def test_match_args_contains_positional_init_fields_but_not_keyword_only_fields():
    @dataclass
    class Event:
        kind: str
        payload: object
        _: KW_ONLY
        source: str = "local"

    assert Event.__match_args__ == ("kind", "payload")
    event = Event("message", {"id": 7}, source="queue")
    match event:
        case Event("message", {"id": identifier}):
            matched = identifier
        case _:
            matched = None
    assert matched == 7


def test_match_args_can_be_disabled_or_supplied_explicitly():
    @dataclass(match_args=False)
    class KeywordPatternOnly:
        value: int

    assert "__match_args__" not in KeywordPatternOnly.__dict__
    with pytest.raises(TypeError):
        match KeywordPatternOnly(1):
            case KeywordPatternOnly(1):
                pass

    @dataclass
    class ExplicitPattern:
        __match_args__ = ("right",)
        left: int
        right: int

    assert ExplicitPattern.__match_args__ == ("right",)


def test_slots_returns_a_new_class_without_an_instance_dictionary():
    class RawCoordinate:
        x: int
        y: int

    SlottedCoordinate = dataclass(slots=True)(RawCoordinate)
    point = SlottedCoordinate(1, 2)

    assert SlottedCoordinate is not RawCoordinate
    assert SlottedCoordinate.__slots__ == ("x", "y")
    assert not hasattr(point, "__dict__")
    with pytest.raises(AttributeError):
        point.z = 3

    with pytest.raises(TypeError, match="already specifies __slots__"):

        @dataclass(slots=True)
        class DuplicateSlots:
            __slots__ = ("x",)
            x: int


def test_descriptor_typed_field_routes_generated_init_through_descriptor_set():
    class PositiveInteger:
        def __init__(self, default=0):
            self.default = default
            self.storage_name = None

        def __set_name__(self, owner, name):
            self.storage_name = f"_{name}"

        def __get__(self, instance, owner=None):
            if instance is None:
                return self.default
            return getattr(instance, self.storage_name, self.default)

        def __set__(self, instance, value):
            value = int(value)
            if value < 0:
                raise ValueError("must be non-negative")
            setattr(instance, self.storage_name, value)

    @dataclass
    class Stock:
        quantity: PositiveInteger = PositiveInteger(default=5)

    default_stock = Stock()
    converted_stock = Stock("7")
    assert default_stock.quantity == 5
    assert converted_stock.quantity == 7
    with pytest.raises(ValueError, match="non-negative"):
        Stock(-1)


def test_asdict_and_astuple_recurse_and_deepcopy_non_dataclass_values():
    @dataclass
    class Point:
        x: int
        y: int

    @dataclass
    class Shape:
        name: str
        points: list
        metadata: dict

    original_metadata = {"colors": ["red"]}
    shape = Shape("line", [Point(0, 0), Point(2, 3)], original_metadata)
    mapping = asdict(shape)
    sequence = astuple(shape)

    assert mapping == {
        "name": "line",
        "points": [{"x": 0, "y": 0}, {"x": 2, "y": 3}],
        "metadata": {"colors": ["red"]},
    }
    assert sequence == ("line", [(0, 0), (2, 3)], {"colors": ["red"]})
    assert mapping["metadata"] is not original_metadata
    assert mapping["metadata"]["colors"] is not original_metadata["colors"]


def test_conversion_factories_change_the_outer_result_container():
    @dataclass
    class Pair:
        left: int
        right: int

    pair = Pair(1, 2)
    assert asdict(pair, dict_factory=lambda items: tuple(items)) == (
        ("left", 1),
        ("right", 2),
    )
    assert astuple(pair, tuple_factory=list) == [1, 2]


def test_fields_recipe_makes_a_shallow_view_when_deepcopy_is_not_wanted():
    @dataclass
    class Payload:
        values: list

    original_values = [1, 2]
    payload = Payload(original_values)
    shallow = {item.name: getattr(payload, item.name) for item in fields(payload)}
    deep = asdict(payload)

    assert shallow["values"] is original_values
    assert deep["values"] is not original_values


def test_replace_calls_init_and_post_init_to_build_a_new_instance():
    @dataclass
    class Rectangle:
        width: int
        height: int
        area: int = field(init=False)

        def __post_init__(self):
            self.area = self.width * self.height

    original = Rectangle(3, 4)
    changed = replace(original, width=5)
    assert changed is not original
    assert changed == Rectangle(5, 4)
    assert changed.area == 20

    with pytest.raises(ValueError, match="init=False"):
        replace(original, area=999)
    with pytest.raises(TypeError):
        replace(original, unknown=1)


def test_replace_requires_initvar_without_a_default_again():
    @dataclass
    class SecuredValue:
        value: str
        secret: InitVar[str]
        digest: str = field(init=False)

        def __post_init__(self, secret):
            self.digest = f"{secret}:{self.value}"

    original = SecuredValue("first", secret="key")
    with pytest.raises(ValueError, match="InitVar"):
        replace(original, value="second")

    changed = replace(original, value="second", secret="new-key")
    assert changed.digest == "new-key:second"


def test_is_dataclass_accepts_both_class_and_instance_so_distinguish_them():
    assert is_dataclass(InventoryItem)
    assert is_dataclass(InventoryItem("pen", 1.0))
    assert not is_dataclass(object)

    def is_dataclass_instance(value):
        return is_dataclass(value) and not isinstance(value, type)

    assert is_dataclass_instance(InventoryItem("pen", 1.0))
    assert not is_dataclass_instance(InventoryItem)


def test_make_dataclass_builds_a_dynamic_type_with_the_same_generation_rules():
    DynamicRecord = make_dataclass(
        "DynamicRecord",
        [
            ("identifier", int),
            "payload",
            ("enabled", bool, field(default=True, kw_only=True)),
        ],
        namespace={"describe": lambda self: f"record:{self.identifier}"},
        slots=True,
    )
    record = DynamicRecord(7, {"answer": 42}, enabled=False)

    assert is_dataclass(DynamicRecord)
    assert record.describe() == "record:7"
    assert record.enabled is False
    assert fields(DynamicRecord)[1].type is Any
    assert not hasattr(record, "__dict__")
