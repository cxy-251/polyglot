"""156｜contextlib 与 abc：上下文管理协议和抽象接口协议。

``contextlib`` 把 ``__enter__/__exit__``、异步对应协议及清理回调组合成工作流；
``abc`` 则把“哪些方法必须实现”和“哪些类型在语义上属于接口”交给
类创建和
``isinstance/issubclass``。两者都围绕协议而非数据结构，合在一套里更容易看出
显式实现、适配器、fallback、异常抑制和虚拟子类之间的边界。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.contextlib python.contextlib.contextmanager
# polyglot-covers: python.contextmanager.enter-exit python.contextmanager.throw
# polyglot-covers: python.contextmanager.exactly-one-yield
# polyglot-covers: python.contextmanager.exception-suppression
# polyglot-covers: python.contextlib.asynccontextmanager
# polyglot-covers: python.asynccontextmanager.decorator-3.10
# polyglot-covers: python.contextlib.closing python.contextlib.aclosing
# polyglot-covers: python.contextlib.nullcontext python.nullcontext.async-3.10
# polyglot-covers: python.contextlib.suppress python.suppress.subclasses
# polyglot-covers: python.contextlib.redirect-stdout python.contextlib.redirect-stderr
# polyglot-covers: python.redirect-stream.reentrant-global-side-effect
# polyglot-covers: python.contextlib.abstract-context-manager
# polyglot-covers: python.contextlib.abstract-async-context-manager
# polyglot-covers: python.contextlib.context-decorator
# polyglot-covers: python.context-decorator.recreate-generator
# polyglot-covers: python.contextlib.exit-stack python.exit-stack-lifo
# polyglot-covers: python.exit-stack.enter-context python.exit-stack.push
# polyglot-covers: python.exit-stack.callback python.exit-stack.pop-all
# polyglot-covers: python.exit-stack.exception-suppression-replacement
# polyglot-covers: python.exit-stack.catch-enter-separately
# polyglot-covers: python.contextlib.async-exit-stack
# polyglot-covers: python.async-exit-stack.sync-async-cleanup
# polyglot-covers: python.stdlib.abc python.abc.abc python.abc.abc-meta
# polyglot-covers: python.abc.abstractmethod python.abc.instantiation-check
# polyglot-covers: python.abc.abstract-classmethod python.abc.abstract-staticmethod
# polyglot-covers: python.abc.abstract-property python.abc.decorator-order
# polyglot-covers: python.abc.abstract-method-body python.abc.super-endpoint
# polyglot-covers: python.abc.register python.abc.virtual-subclass
# polyglot-covers: python.abc.virtual-no-method-inheritance
# polyglot-covers: python.abc.subclasshook python.abc.not-implemented-fallback
# polyglot-covers: python.abc.get-cache-token python.abc.update-abstractmethods
# polyglot-covers: python.abc.abstractmethods-set
# polyglot-covers: python.abc.deprecated-abstract-decorators

from abc import ABC
from abc import ABCMeta
from abc import abstractclassmethod
from abc import abstractmethod
from abc import abstractproperty
from abc import abstractstaticmethod
from abc import get_cache_token
from abc import update_abstractmethods
import asyncio
from contextlib import AbstractAsyncContextManager
from contextlib import AbstractContextManager
from contextlib import aclosing
from contextlib import asynccontextmanager
from contextlib import AsyncExitStack
from contextlib import closing
from contextlib import contextmanager
from contextlib import ExitStack
from contextlib import nullcontext
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from contextlib import suppress
from io import StringIO
import sys

import pytest


class RecordingContext:
    def __init__(self, name, events, *, suppress_type=None):
        self.name = name
        self.events = events
        self.suppress_type = suppress_type

    def __enter__(self):
        self.events.append(f"enter:{self.name}")
        return f"value:{self.name}"

    def __exit__(self, exc_type, exc_value, traceback):
        exception_name = None if exc_type is None else exc_type.__name__
        self.events.append(f"exit:{self.name}:{exception_name}")
        return exc_type is not None and issubclass(exc_type, self.suppress_type or ())


def test_contextmanager_maps_yield_to_enter_and_finally_to_exit():
    events = []

    @contextmanager
    def resource(name):
        events.append(f"acquire:{name}")
        try:
            yield {"name": name}
        finally:
            events.append(f"release:{name}")

    with resource("database") as value:
        events.append(f"use:{value['name']}")

    assert events == [
        "acquire:database",
        "use:database",
        "release:database",
    ]


def test_contextmanager_throws_body_exception_at_the_yield_expression():
    events = []

    @contextmanager
    def translate_error():
        try:
            yield
        except KeyError as error:
            events.append(f"caught:{error.args[0]}")
            raise LookupError("translated") from error
        finally:
            events.append("finally")

    with pytest.raises(LookupError, match="translated") as captured:
        with translate_error():
            raise KeyError("missing")

    assert isinstance(captured.value.__cause__, KeyError)
    assert events == ["caught:missing", "finally"]


def test_generator_context_manager_must_yield_exactly_once():
    @contextmanager
    def never_yields():
        if False:
            yield

    @contextmanager
    def yields_twice():
        yield "first"
        yield "second"

    with pytest.raises(RuntimeError, match="generator didn't yield"):
        with never_yields():
            pass

    with pytest.raises(RuntimeError, match="generator didn't stop"):
        with yields_twice() as value:
            assert value == "first"


def test_generator_context_manager_can_suppress_by_not_reraising():
    @contextmanager
    def ignore_lookup_error():
        try:
            yield
        except LookupError:
            pass

    with ignore_lookup_error():
        raise KeyError("suppressed")

    @contextmanager
    def observe_but_reraise():
        try:
            yield
        except LookupError:
            raise

    with pytest.raises(KeyError):
        with observe_but_reraise():
            raise KeyError("preserved")


def test_contextmanager_is_also_a_reusable_function_decorator():
    events = []

    @contextmanager
    def transaction():
        events.append("begin")
        try:
            yield
        finally:
            events.append("end")

    @transaction()
    def work(value):
        events.append(f"work:{value}")
        return value * 2

    assert work(3) == 6
    assert work(4) == 8
    assert events == ["begin", "work:3", "end", "begin", "work:4", "end"]
    # generator 只能迭代一次；ContextDecorator 每次调用都会 _recreate_cm，
    # 所以装饰后的函数不会复用已经耗尽的 generator。


def test_asynccontextmanager_supports_async_with_and_function_decoration():
    async def scenario():
        events = []

        @asynccontextmanager
        async def connection():
            events.append("connect")
            try:
                yield "channel"
            finally:
                events.append("disconnect")

        @connection()
        async def send(message):
            events.append(f"send:{message}")
            return len(message)

        async with connection() as channel:
            events.append(f"use:{channel}")
        assert await send("hello") == 5
        assert events == [
            "connect",
            "use:channel",
            "disconnect",
            "connect",
            "send:hello",
            "disconnect",
        ]

    asyncio.run(scenario())


def test_closing_adapts_an_object_that_only_has_close():
    class LegacyResource:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    resource = LegacyResource()
    with closing(resource) as entered:
        assert entered is resource
        assert not resource.closed
    assert resource.closed


def test_aclosing_finalizes_an_async_generator_in_the_same_async_context():
    async def scenario():
        events = []

        async def stream():
            try:
                for value in range(3):
                    yield value
            finally:
                events.append("async generator finalized")

        generator = stream()
        async with aclosing(generator) as values:
            assert await values.__anext__() == 0
        assert events == ["async generator finalized"]

    asyncio.run(scenario())


def test_nullcontext_turns_an_optional_resource_into_one_with_branchless_with():
    events = []
    supplied = RecordingContext("supplied", events)

    def use(resource=None):
        manager = nullcontext("default") if resource is None else resource
        with manager as value:
            return value

    assert use() == "default"
    assert use(supplied) == "value:supplied"
    assert events == ["enter:supplied", "exit:supplied:None"]


def test_nullcontext_supports_async_with_in_python_310():
    async def scenario():
        marker = object()
        async with nullcontext(marker) as entered:
            assert entered is marker

    asyncio.run(scenario())


def test_suppress_uses_exception_subclass_matching_and_only_scopes_its_body():
    with suppress(FileNotFoundError):
        raise FileNotFoundError("optional file")

    with pytest.raises(IsADirectoryError):
        with suppress(FileNotFoundError):
            raise IsADirectoryError("different OSError subclass")

    class SpecificLookup(KeyError):
        pass

    with suppress(LookupError):
        raise SpecificLookup("subclasses match")


def test_redirect_streams_are_reentrant_but_change_process_global_attributes():
    outer = StringIO()
    inner = StringIO()
    errors = StringIO()
    original_stdout = sys.stdout

    with redirect_stdout(outer):
        print("outer one")
        with redirect_stdout(inner), redirect_stderr(errors):
            print("inner")
            print("problem", file=sys.stderr)
        print("outer two")

    assert outer.getvalue().splitlines() == ["outer one", "outer two"]
    assert inner.getvalue().splitlines() == ["inner"]
    assert errors.getvalue().splitlines() == ["problem"]
    assert sys.stdout is original_stdout
    # redirect_stdout 直接改 sys.stdout，适合单线程脚本和文档捕获，不适合作为
    # 多线程库函数的输出隔离机制。


def test_abstract_context_manager_supplies_default_enter_but_requires_exit():
    class Manager(AbstractContextManager):
        def __init__(self):
            self.closed = False

        def __exit__(self, exc_type, exc_value, traceback):
            self.closed = True

    manager = Manager()
    with manager as entered:
        assert entered is manager
    assert manager.closed
    assert Manager.__abstractmethods__ == frozenset()


def test_abstract_async_context_manager_supplies_default_aenter():
    class Manager(AbstractAsyncContextManager):
        def __init__(self):
            self.closed = False

        async def __aexit__(self, exc_type, exc_value, traceback):
            self.closed = True

    async def scenario():
        manager = Manager()
        async with manager as entered:
            assert entered is manager
        assert manager.closed

    asyncio.run(scenario())


def test_exit_stack_enters_contexts_and_unwinds_everything_in_lifo_order():
    events = []
    with ExitStack() as stack:
        first = stack.enter_context(RecordingContext("first", events))
        second = stack.enter_context(RecordingContext("second", events))
        stack.callback(events.append, "callback:last")
        assert first == "value:first"
        assert second == "value:second"
        events.append("body")

    assert events == [
        "enter:first",
        "enter:second",
        "body",
        "callback:last",
        "exit:second:None",
        "exit:first:None",
    ]


def test_exit_stack_push_covers_exit_without_calling_enter():
    events = []
    context = RecordingContext("already acquired", events)

    with ExitStack() as stack:
        returned = stack.push(context)
        assert returned is context
        assert events == []

    assert events == ["exit:already acquired:None"]


def test_exit_stack_callback_cannot_suppress_but_exit_callback_can():
    events = []

    def ordinary_callback(label):
        events.append(label)

    def suppress_key_error(exc_type, exc_value, traceback):
        events.append(exc_type.__name__)
        return exc_type is KeyError

    with ExitStack() as stack:
        stack.callback(ordinary_callback, "ordinary")
        stack.push(suppress_key_error)
        raise KeyError("suppressed")

    assert events == ["KeyError", "ordinary"]
    # callback 注册的函数不接收异常详情，返回值也被忽略；push 注册的
    # __exit__ 形函数才参与异常抑制协议。


def test_inner_exit_can_replace_exception_seen_by_outer_exit():
    events = []

    def observe_outer(exc_type, exc_value, traceback):
        events.append(("outer", exc_type, str(exc_value)))

    def replace_inner(exc_type, exc_value, traceback):
        events.append(("inner", exc_type, str(exc_value)))
        raise RuntimeError("replacement")

    with pytest.raises(RuntimeError, match="replacement"):
        with ExitStack() as stack:
            stack.push(observe_outer)
            stack.push(replace_inner)
            raise ValueError("original")

    assert events[0][0:] == ("inner", ValueError, "original")
    assert events[1][0:] == ("outer", RuntimeError, "replacement")


def test_pop_all_transfers_callbacks_for_two_phase_resource_validation():
    events = []
    stack = ExitStack()
    stack.enter_context(RecordingContext("first", events))
    stack.enter_context(RecordingContext("second", events))

    committed_cleanup = stack.pop_all()
    stack.close()
    assert events == ["enter:first", "enter:second"]

    committed_cleanup.close()
    assert events == [
        "enter:first",
        "enter:second",
        "exit:second:None",
        "exit:first:None",
    ]


def test_enter_context_error_can_be_caught_without_catching_body_or_exit_errors():
    class FailingEnter:
        def __enter__(self):
            raise OSError("acquisition failed")

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    stack = ExitStack()
    try:
        with pytest.raises(OSError, match="acquisition failed"):
            stack.enter_context(FailingEnter())
        with stack:
            pass
    finally:
        stack.close()


def test_async_exit_stack_combines_async_contexts_and_both_callback_kinds():
    async def scenario():
        events = []

        @asynccontextmanager
        async def async_resource():
            events.append("async enter")
            try:
                yield "resource"
            finally:
                events.append("async exit")

        async def async_callback(label):
            events.append(label)

        async with AsyncExitStack() as stack:
            value = await stack.enter_async_context(async_resource())
            stack.callback(events.append, "sync callback")
            stack.push_async_callback(async_callback, "async callback")
            events.append(f"body:{value}")

        assert events == [
            "async enter",
            "body:resource",
            "async callback",
            "sync callback",
            "async exit",
        ]

    asyncio.run(scenario())


def test_abc_prevents_instantiation_until_every_abstract_method_is_overridden():
    class Serializer(ABC):
        @abstractmethod
        def dumps(self, value):
            """Return text for value."""

        @abstractmethod
        def loads(self, text):
            """Return a value from text."""

    class WriteOnly(Serializer):
        def dumps(self, value):
            return str(value)

    assert Serializer.__abstractmethods__ == frozenset({"dumps", "loads"})
    assert WriteOnly.__abstractmethods__ == frozenset({"loads"})
    with pytest.raises(TypeError, match="abstract method"):
        Serializer()
    with pytest.raises(TypeError, match="loads"):
        WriteOnly()

    class Complete(WriteOnly):
        def loads(self, text):
            return int(text)

    serializer = Complete()
    assert serializer.dumps(7) == "7"
    assert serializer.loads("7") == 7


def test_abcmeta_can_be_used_directly_when_abc_base_is_not_desired():
    class Plugin(metaclass=ABCMeta):
        @abstractmethod
        def run(self):
            pass

    class ConcretePlugin(Plugin):
        def run(self):
            return "running"

    assert ConcretePlugin().run() == "running"
    assert isinstance(Plugin, ABCMeta)


def test_abstract_class_static_and_property_decorators_keep_descriptor_outermost():
    class Model(ABC):
        @classmethod
        @abstractmethod
        def from_text(cls, text):
            pass

        @staticmethod
        @abstractmethod
        def validate(text):
            pass

        @property
        @abstractmethod
        def label(self):
            pass

    class ConcreteModel(Model):
        @classmethod
        def from_text(cls, text):
            return cls(text)

        @staticmethod
        def validate(text):
            return bool(text)

        def __init__(self, text):
            self._text = text

        @property
        def label(self):
            return self._text.upper()

    value = ConcreteModel.from_text("python")
    assert ConcreteModel.validate("python") is True
    assert value.label == "PYTHON"
    # abstractmethod 必须最靠近函数，classmethod/staticmethod/property 在外层
    # 创建描述符；颠倒顺序会尝试写只读的 __isabstractmethod__。


def test_abstract_method_may_supply_a_super_endpoint_implementation():
    class CooperativeProcessor(ABC):
        @abstractmethod
        def process(self, values):
            return list(values)

    class SortedProcessor(CooperativeProcessor):
        def process(self, values):
            normalized = super().process(values)
            return sorted(normalized)

    assert SortedProcessor().process({3, 1, 2}) == [1, 2, 3]
    assert getattr(CooperativeProcessor.process, "__isabstractmethod__") is True


def test_register_adds_a_virtual_subclass_without_copying_methods_or_mro():
    class SupportsLength(ABC):
        @abstractmethod
        def __len__(self):
            pass

        def empty(self):
            return len(self) == 0

    @SupportsLength.register
    class LegacyCollection:
        def __init__(self, values):
            self.values = values

        def __len__(self):
            return len(self.values)

    value = LegacyCollection([])
    assert issubclass(LegacyCollection, SupportsLength)
    assert isinstance(value, SupportsLength)
    assert SupportsLength not in LegacyCollection.__mro__
    assert not hasattr(value, "empty")
    # 虚拟注册只影响子类判断；不会注入 mixin 方法，也不会检查抽象方法
    # 是否真的存在。注册表达的是注册者承担的接口契约。


def test_subclasshook_recognizes_structural_capability_and_can_defer():
    class IterableProtocol(ABC):
        @classmethod
        def __subclasshook__(cls, candidate):
            if cls is IterableProtocol:
                if any("__iter__" in base.__dict__ for base in candidate.__mro__):
                    return True
            return NotImplemented

    class StructuralIterable:
        def __iter__(self):
            return iter((1, 2))

    class MissingProtocol:
        pass

    assert issubclass(StructuralIterable, IterableProtocol)
    assert isinstance(StructuralIterable(), IterableProtocol)
    assert not issubclass(MissingProtocol, IterableProtocol)
    assert IterableProtocol.__subclasshook__(MissingProtocol) is NotImplemented


def test_cache_token_changes_when_virtual_subclass_registry_changes():
    class Protocol(ABC):
        pass

    class Candidate:
        pass

    before = get_cache_token()
    Protocol.register(Candidate)
    after = get_cache_token()
    assert after != before
    assert issubclass(Candidate, Protocol)
    # 缓存 isinstance/issubclass 结果的框架可用 token 判断 ABC 注册表是否失效。


def test_update_abstractmethods_recalculates_a_class_modified_after_creation():
    class DynamicProtocol(ABC):
        pass

    @abstractmethod
    def required(self):
        return "fallback"

    DynamicProtocol.required = required
    assert DynamicProtocol.__abstractmethods__ == frozenset()

    returned = update_abstractmethods(DynamicProtocol)
    assert returned is DynamicProtocol
    assert DynamicProtocol.__abstractmethods__ == frozenset({"required"})
    with pytest.raises(TypeError):
        DynamicProtocol()

    DynamicProtocol.required = lambda self: "implemented"
    update_abstractmethods(DynamicProtocol)
    assert DynamicProtocol().required() == "implemented"


def test_deprecated_abstract_descriptor_helpers_mark_members_but_new_code_composes():
    assert abstractclassmethod(lambda cls: None).__isabstractmethod__ is True
    assert abstractstaticmethod(lambda: None).__isabstractmethod__ is True
    assert abstractproperty(lambda self: None).__isabstractmethod__ is True
    # 这些组合类保留给旧代码；当前写法应组合 @classmethod/@staticmethod/
    # @property 与最内层 @abstractmethod。
