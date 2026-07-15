"""144｜typing：静态类型表达式的运行时元数据、泛型、协议与辅助对象。

``typing`` 主要服务静态检查器，但类型表达式、``TypedDict``、``Protocol``、
``NamedTuple`` 和注解解析也具有可观察的运行时行为。本套刻意区分
“供工具读取的元数据”和“解释器真正执行的约束”，避免把 type hint
误当成运行时验证器。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.typing python.typing.annotation-runtime-metadata
# polyglot-covers: python.typing.get-origin python.typing.get-args
# polyglot-covers: python.typing.builtin-generic-alias python.typing.parameterized-isinstance
# polyglot-covers: python.typing.union python.typing.pep604-union
# polyglot-covers: python.typing.optional python.typing.union-runtime-short-circuit
# polyglot-covers: python.typing.annotated python.typing.annotated-flattening
# polyglot-covers: python.typing.literal python.typing.callable
# polyglot-covers: python.typing.typevar-constraints-bound-variance
# polyglot-covers: python.typing.paramspec python.typing.concatenate
# polyglot-covers: python.typing.generic python.typing.orig-class-timing
# polyglot-covers: python.typing.generic-specialization-metadata
# polyglot-covers: python.typing.namedtuple-class-syntax-and-defaults
# polyglot-covers: python.typing.typeddict-required-optional-runtime-boundary
# polyglot-covers: python.typing.is-typeddict
# polyglot-covers: python.typing.protocol python.typing.runtime-checkable
# polyglot-covers: python.typing.protocol-method-only-subclass-check
# polyglot-covers: python.typing.protocol-data-member-subclass-restriction
# polyglot-covers: python.typing.protocol-runtime-check-is-shallow
# polyglot-covers: python.typing.get-type-hints-forward-reference
# polyglot-covers: python.typing.get-type-hints-include-extras
# polyglot-covers: python.typing.get-type-hints-localns-and-code-execution-warning
# polyglot-covers: python.typing.newtype python.typing.cast
# polyglot-covers: python.typing.type-alias python.typing.type-guard
# polyglot-covers: python.typing.final python.typing.classvar
# polyglot-covers: python.typing.overload-runtime-implementation
# polyglot-covers: python.typing.no-type-check python.typing.any-runtime-boundary

from collections.abc import Callable as ABCCallable
import types
from typing import Annotated
from typing import Any
from typing import Callable
from typing import ClassVar
from typing import Concatenate
from typing import Final
from typing import Generic
from typing import Literal
from typing import NamedTuple
from typing import NewType
from typing import NoReturn
from typing import Optional
from typing import ParamSpec
from typing import Protocol
from typing import TypeAlias
from typing import TypeGuard
from typing import TypeVar
from typing import TypedDict
from typing import Union
from typing import cast
from typing import final
from typing import get_args
from typing import get_origin
from typing import get_type_hints
from typing import is_typeddict
from typing import no_type_check
from typing import overload
from typing import runtime_checkable

import pytest


T = TypeVar("T")
NumberT = TypeVar("NumberT", int, float)
SizedT = TypeVar("SizedT", bound="SizedRecord")
CovariantT = TypeVar("CovariantT", covariant=True)
ContravariantT = TypeVar("ContravariantT", contravariant=True)
P = ParamSpec("P")


class SizedRecord:
    def __len__(self):
        return 1


class Box(Generic[T]):
    def __init__(self, value: T):
        self.value = value
        # typing 在 __init__ 返回之后才补写 __orig_class__；构造函数不能依赖它。
        self.specialization_seen_during_init = getattr(self, "__orig_class__", None)


class IntBox(Box[int]):
    pass


class Employee(NamedTuple):
    name: str
    employee_id: int = 0


class RequiredMovie(TypedDict):
    title: str
    year: int


class MoviePatch(RequiredMovie, total=False):
    note: str


@runtime_checkable
class Closable(Protocol):
    def close(self) -> None:
        ...


@runtime_checkable
class HasName(Protocol):
    name: str


class Resource:
    name = "cache"

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class AnnotationNode:
    parent: "AnnotationNode | None"
    payload: Annotated[int, "non-negative"]


def accepts_none(value: None) -> None:
    return None


def is_string_list(values: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(value, str) for value in values)


@overload
def identity(value: int) -> int:
    ...


@overload
def identity(value: str) -> str:
    ...


def identity(value):
    # 运行时只剩这个实现；overload 分支不会自动做参数检查或分派。
    return value


def test_builtin_generic_aliases_retain_origin_and_arguments():
    alias = list[dict[str, int]]

    assert isinstance(alias, types.GenericAlias)
    assert get_origin(alias) is list
    assert get_args(alias) == (dict[str, int],)
    assert get_origin(get_args(alias)[0]) is dict
    assert get_args(get_args(alias)[0]) == (str, int)

    # 参数化类型可以构造普通对象，
    # 但不会把元素类型变成运行时检查规则。
    assert alias([{"ok": 1}, {"still accepted": "wrong"}]) == [
        {"ok": 1},
        {"still accepted": "wrong"},
    ]
    with pytest.raises(TypeError, match="parameterized generic"):
        isinstance([], list[int])


def test_union_optional_and_pep604_runtime_behavior():
    pep604 = int | str

    assert get_origin(pep604) is types.UnionType
    assert get_args(pep604) == (int, str)
    assert isinstance("text", pep604)
    assert int | int is int

    classic = Union[int, str]
    assert get_origin(classic) is Union
    assert set(get_args(classic)) == {int, str}
    assert get_args(Optional[int]) == (int, type(None))

    # isinstance 会从左到右短路。参数化 generic 本身非法，因此把它放进
    # union 并不能保证总是合法：前面已经命中时可能成功，
    # 真正走到该分支时仍会报错。
    mixed = int | list[int]
    assert isinstance(1, mixed)
    with pytest.raises(TypeError, match="parameterized generic"):
        isinstance([], mixed)


def test_annotated_flattens_metadata_and_type_hints_can_preserve_it():
    qualified = Annotated[Annotated[int, "database-id"], "positive"]

    assert get_origin(qualified) is Annotated
    assert get_args(qualified) == (int, "database-id", "positive")
    assert qualified.__origin__ is int
    assert qualified.__metadata__ == ("database-id", "positive")

    plain_hints = get_type_hints(AnnotationNode)
    rich_hints = get_type_hints(AnnotationNode, include_extras=True)
    assert plain_hints["payload"] is int
    assert rich_hints["payload"] == Annotated[int, "non-negative"]


def test_literal_callable_and_marker_annotations_are_metadata_not_guards():
    mode = Literal["r", "w", 0]
    callback = Callable[[int, str], bool]

    assert get_origin(mode) is Literal
    assert get_args(mode) == ("r", "w", 0)
    assert get_origin(callback) is ABCCallable
    assert get_args(callback) == ([int, str], bool)

    class Configuration:
        schema: ClassVar[str] = "v1"
        retries: Final[int] = 3

    # ClassVar/Final 不会阻止实例遮蔽或重新赋值；约束由类型检查器执行。
    configuration = Configuration()
    configuration.schema = "instance"
    configuration.retries = 4
    assert (configuration.schema, configuration.retries) == ("instance", 4)
    assert get_type_hints(Configuration) == {
        "schema": ClassVar[str],
        "retries": Final[int],
    }


def test_typevar_metadata_records_constraints_bounds_and_variance():
    assert T.__constraints__ == ()
    assert T.__bound__ is None

    assert NumberT.__constraints__ == (int, float)
    assert NumberT.__bound__ is None

    # 字符串 bound 先保存为 ForwardRef；只有解析某个注解时才会求值。
    assert SizedT.__constraints__ == ()
    assert SizedT.__bound__.__forward_arg__ == "SizedRecord"

    assert CovariantT.__covariant__ is True
    assert CovariantT.__contravariant__ is False
    assert ContravariantT.__covariant__ is False
    assert ContravariantT.__contravariant__ is True


def test_paramspec_and_concatenate_expose_callable_shape_metadata():
    decorated_shape = Callable[Concatenate[str, P], int]

    assert get_origin(P.args) is P
    assert get_origin(P.kwargs) is P
    assert get_origin(decorated_shape) is ABCCallable

    callable_arguments, return_type = get_args(decorated_shape)
    assert get_origin(callable_arguments) is Concatenate
    assert get_args(callable_arguments) == (str, P)
    assert return_type is int


def test_generic_specialization_is_attached_after_init():
    box = Box[int](42)

    assert box.value == 42
    assert box.specialization_seen_during_init is None
    assert box.__orig_class__ == Box[int]
    assert Box[int].__origin__ is Box
    assert Box[int].__args__ == (int,)

    # 继承一个 specialization 与调用 Box[int](...) 不同。类型参数记录在类的
    # __orig_bases__，普通 IntBox 实例通常没有 __orig_class__。
    specialized_subclass = IntBox(7)
    assert IntBox.__orig_bases__ == (Box[int],)
    assert not hasattr(specialized_subclass, "__orig_class__")


def test_namedtuple_class_syntax_builds_an_immutable_tuple_subclass():
    employee = Employee("Ada")

    assert employee == ("Ada", 0)
    assert employee.name == "Ada"
    assert employee.employee_id == 0
    assert Employee.__annotations__ == {"name": str, "employee_id": int}
    assert Employee._fields == ("name", "employee_id")
    assert Employee._field_defaults == {"employee_id": 0}
    assert employee._asdict() == {"name": "Ada", "employee_id": 0}
    assert employee._replace(employee_id=9) == Employee("Ada", 9)

    with pytest.raises(AttributeError):
        employee.name = "Grace"


def test_typeddict_exposes_schema_but_constructs_an_unchecked_dict():
    assert is_typeddict(RequiredMovie)
    assert is_typeddict(MoviePatch)
    assert not is_typeddict(dict)

    assert RequiredMovie.__required_keys__ == frozenset({"title", "year"})
    assert RequiredMovie.__optional_keys__ == frozenset()
    assert MoviePatch.__required_keys__ == frozenset({"title", "year"})
    assert MoviePatch.__optional_keys__ == frozenset({"note"})
    assert MoviePatch.__total__ is False

    movie = MoviePatch(title="Primer", year="runtime accepts wrong type", extra=True)
    assert type(movie) is dict
    assert movie["extra"] is True

    # TypedDict 没有 runtime instance check；要校验外部数据仍需显式 validator。
    with pytest.raises(TypeError, match="TypedDict"):
        isinstance(movie, MoviePatch)


def test_runtime_protocol_checks_presence_without_signature_validation():
    resource = Resource()

    assert isinstance(resource, Closable)
    assert issubclass(Resource, Closable)
    resource.close()
    assert resource.closed is True

    class Misleading:
        # runtime protocol check 只看属性是否存在且不是 None，
        # 不检查它能否调用，
        # 也不比较签名和返回注解。
        close = 42

    assert isinstance(Misleading(), Closable)
    with pytest.raises(TypeError):
        Misleading().close()


def test_data_protocol_allows_instance_check_but_not_issubclass():
    assert isinstance(Resource(), HasName)

    # 含非方法成员的 protocol 不能安全地做 issubclass：实例属性可能只在
    # __init__ 中出现，所以 typing 明确拒绝这种类级判断。
    with pytest.raises(TypeError, match="non-method members"):
        issubclass(Resource, HasName)


def test_protocol_without_runtime_checkable_rejects_runtime_checks():
    class Serializable(Protocol):
        def serialize(self) -> bytes:
            ...

    class Payload:
        def serialize(self):
            return b"payload"

    with pytest.raises(TypeError, match="runtime_checkable"):
        isinstance(Payload(), Serializable)


def test_get_type_hints_resolves_forward_refs_none_and_local_names():
    hints = get_type_hints(AnnotationNode)

    assert hints["parent"] == AnnotationNode | None
    assert hints["payload"] is int
    assert get_type_hints(accepts_none) == {
        "value": type(None),
        "return": type(None),
    }

    class LocalPayload:
        pass

    def consume(value: "LocalPayload") -> "list[LocalPayload]":
        return [value]

    with pytest.raises(NameError, match="LocalPayload"):
        get_type_hints(consume)

    resolved = get_type_hints(consume, localns={"LocalPayload": LocalPayload})
    assert resolved == {"value": LocalPayload, "return": list[LocalPayload]}

    # get_type_hints 会 eval 字符串 forward reference。不要对不可信注解调用它；
    # 传 globalns/localns 解决名字，并不能把求值过程变成 sandbox。


def test_newtype_cast_typealias_and_typeguard_have_lightweight_runtime_behavior():
    Token = NewType("Token", object)
    marker = object()
    assert Token(marker) is marker
    assert Token.__name__ == "Token"
    assert Token.__supertype__ is object

    payload = {"count": "not really an int"}
    assert cast(dict[str, int], payload) is payload

    Identifier: TypeAlias = int | str
    assert Identifier == int | str
    assert is_string_list(["a", "b"]) is True
    assert is_string_list(["a", 1]) is False
    assert get_type_hints(is_string_list)["return"] == TypeGuard[list[str]]


def test_final_overload_and_no_type_check_are_tooling_contracts():
    @final
    class BaseService:
        pass

    class RuntimeSubclass(BaseService):
        pass

    assert BaseService.__final__ is True
    assert isinstance(RuntimeSubclass(), BaseService)
    assert identity(3) == 3
    assert identity("value") == "value"
    assert identity([]) == []

    @no_type_check
    def legacy(value: "NameThatDoesNotExist") -> int:
        return value

    assert legacy.__no_type_check__ is True
    assert get_type_hints(legacy) == {}


def test_any_and_noreturn_do_not_create_runtime_value_categories():
    with pytest.raises(TypeError, match="typing.Any"):
        isinstance(object(), Any)

    def declared_to_never_return() -> NoReturn:
        # 解释器不会根据 NoReturn 阻止返回；这是静态控制流信息。
        return "still returned"

    assert declared_to_never_return() == "still returned"
