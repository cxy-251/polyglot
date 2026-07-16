"""158｜inspect：对象分类、源码、签名、栈帧和执行状态。

``inspect`` 把 Python 数据模型中散落的模块、描述符、函数、代码对象、frame、
traceback、生成器与 coroutine 属性整理成稳定查询接口。本套既展示文档
工具、依赖注入器和调试器常用工作流，也强调普通 ``getattr`` 会执行
用户代码、frame
引用会形成环、字符串注解求值会运行表达式等真实边界。

这些案例面向 Python 3.10 当前补丁系列；整个 Python 测试集尚未经过 pytest
统一验证。
"""

# polyglot-covers: python.stdlib.inspect python.inspect.getmembers
# polyglot-covers: python.inspect.member-predicate python.inspect.sorted-members
# polyglot-covers: python.inspect.object-predicates python.inspect.routine
# polyglot-covers: python.inspect.method-function-builtin-descriptor
# polyglot-covers: python.inspect.data-getset-member-descriptor
# polyglot-covers: python.inspect.generator-coroutine-asyncgen-predicates
# polyglot-covers: python.inspect.isawaitable python.inspect.custom-await
# polyglot-covers: python.inspect.getmodulename python.inspect.getmodule
# polyglot-covers: python.inspect.getfile python.inspect.getsourcefile
# polyglot-covers: python.inspect.getsource python.inspect.getsourcelines
# polyglot-covers: python.inspect.getdoc python.inspect.inherited-doc
# polyglot-covers: python.inspect.getcomments python.inspect.cleandoc
# polyglot-covers: python.inspect.signature python.inspect.parameter-kinds
# polyglot-covers: python.inspect.parameter-empty-description
# polyglot-covers: python.inspect.signature-bind python.inspect.bind-partial
# polyglot-covers: python.inspect.bound-arguments python.inspect.apply-defaults
# polyglot-covers: python.inspect.bound-arguments-mutable
# polyglot-covers: python.inspect.parameter-replace python.inspect.signature-replace
# polyglot-covers: python.inspect.signature-validation
# polyglot-covers: python.inspect.wrapped-signature python.inspect.follow-wrapped
# polyglot-covers: python.inspect.custom-signature python.inspect.unwrap
# polyglot-covers: python.inspect.unwrap-stop-cycle
# polyglot-covers: python.inspect.get-annotations python.inspect.eval-string-annotations
# polyglot-covers: python.inspect.fresh-annotations python.inspect.no-inherited-annotations
# polyglot-covers: python.inspect.getclosurevars python.inspect.closure-categories
# polyglot-covers: python.inspect.getclasstree python.inspect.classify-class-attrs
# polyglot-covers: python.inspect.getfullargspec python.inspect.getcallargs
# polyglot-covers: python.inspect.currentframe python.inspect.getframeinfo
# polyglot-covers: python.inspect.stack python.inspect.getouterframes
# polyglot-covers: python.inspect.trace python.inspect.getinnerframes
# polyglot-covers: python.inspect.frame-reference-cycle
# polyglot-covers: python.inspect.getattr-static python.inspect.descriptor-no-execution
# polyglot-covers: python.inspect.static-dynamic-attribute-boundary
# polyglot-covers: python.inspect.generator-state python.inspect.generator-locals
# polyglot-covers: python.inspect.coroutine-state python.inspect.coroutine-locals
# polyglot-covers: python.inspect.code-object python.inspect.code-flags
# polyglot-covers: python.inspect.command-line-interface

import asyncio
import builtins
import functools
import inspect
from pathlib import Path
import subprocess
import sys

import pytest


GLOBAL_FOR_CLOSURE = 10


# inspect.getcomments 应找到这条紧邻函数定义的源代码注释。
def documented_function(value: int, scale: int = 2) -> int:
    """Return ``value`` multiplied by ``scale``."""

    return value * scale


class DocumentedParent:
    def operation(self):
        """Perform the inherited operation.

        The indentation is normalized by inspect.getdoc.
        """


class UndocumentedChild(DocumentedParent):
    def operation(self):
        pass


def signature_target(
    positional_only,
    /,
    positional_or_keyword: int = 2,
    *values: float,
    required_name: str,
    enabled: bool = True,
    **options: object,
) -> bool:
    return bool(
        positional_only
        and positional_or_keyword
        and required_name
        and enabled
        and values is not None
        and options is not None
    )


class ExampleService:
    """A service used by the introspection examples."""

    category = "example"

    def method(self, value):
        return value

    @classmethod
    def build(cls):
        return cls()

    @property
    def label(self):
        return "service"


def generator_function(limit=2):
    for value in range(limit):
        yield value


async def coroutine_function(value=1):
    return value


async def async_generator_function():
    yield 1


def test_getmembers_returns_sorted_pairs_and_accepts_a_value_predicate():
    members = inspect.getmembers(ExampleService)
    names = [name for name, value in members]
    assert names == sorted(names)
    assert "method" in names
    assert "label" in names

    routines = dict(inspect.getmembers(ExampleService, inspect.isroutine))
    assert "method" in routines
    assert "build" in routines
    assert "category" not in routines


def test_core_predicates_distinguish_modules_classes_functions_and_bound_methods():
    service = ExampleService()
    assert inspect.ismodule(inspect)
    assert inspect.isclass(ExampleService)
    assert inspect.isfunction(ExampleService.method)
    assert inspect.ismethod(service.method)
    assert service.method.__func__ is ExampleService.method
    assert service.method.__self__ is service
    assert inspect.isbuiltin(len)
    assert inspect.isroutine(len)
    assert inspect.isroutine(service.method)
    assert inspect.iscode(documented_function.__code__)

    try:
        raise RuntimeError("traceback predicate")
    except RuntimeError as error:
        saved_traceback = error.__traceback__
    assert inspect.istraceback(saved_traceback)
    assert inspect.isframe(saved_traceback.tb_frame)


def test_descriptor_predicates_offer_specific_and_general_classification():
    class Slotted:
        __slots__ = ("value",)

    assert inspect.ismethoddescriptor(int.__add__)
    assert inspect.isdatadescriptor(ExampleService.label)
    assert inspect.isgetsetdescriptor(type.__dict__["__dict__"])
    assert inspect.ismemberdescriptor(Slotted.__dict__["value"])
    # getset/member 是 CPython C 层描述符的更具体分类；其他实现允许始终 False。


def test_generator_coroutine_and_async_generator_predicates_check_both_factory_and_value():
    generator = generator_function()
    coroutine = coroutine_function()
    async_generator = async_generator_function()
    try:
        assert inspect.isgeneratorfunction(generator_function)
        assert inspect.isgenerator(generator)
        assert inspect.iscoroutinefunction(coroutine_function)
        assert inspect.iscoroutine(coroutine)
        assert inspect.isasyncgenfunction(async_generator_function)
        assert inspect.isasyncgen(async_generator)
    finally:
        generator.close()
        coroutine.close()

        async def close_async_generator():
            await async_generator.aclose()

        asyncio.run(close_async_generator())


def test_isawaitable_recognizes_native_and_custom_await_protocol_objects():
    class CustomAwaitable:
        def __await__(self):
            async def result():
                return 42

            return result().__await__()

    native = coroutine_function()
    custom = CustomAwaitable()

    async def await_custom():
        return await custom

    try:
        assert inspect.isawaitable(native)
        assert inspect.isawaitable(custom)
        assert not inspect.iscoroutine(custom)
        assert asyncio.run(await_custom()) == 42
    finally:
        native.close()


def test_module_name_file_and_module_queries_keep_different_responsibilities():
    assert inspect.getmodulename("/tmp/example.py") == "example"
    assert inspect.getmodulename("/tmp/example.not-a-module") is None
    assert inspect.getmodule(documented_function) is sys.modules[__name__]
    assert Path(inspect.getfile(documented_function)) == Path(__file__)
    assert Path(inspect.getsourcefile(documented_function)) == Path(__file__)

    with pytest.raises(TypeError, match="builtin_function_or_method"):
        inspect.getfile(len)


def test_source_queries_return_text_lines_and_original_starting_line():
    source = inspect.getsource(documented_function)
    lines, starting_line = inspect.getsourcelines(documented_function)

    assert source == "".join(lines)
    assert source.startswith("def documented_function")
    assert "return value * scale" in source
    assert starting_line == documented_function.__code__.co_firstlineno
    with pytest.raises(TypeError, match="builtin_function_or_method"):
        inspect.getsource(len)


def test_getdoc_cleans_indentation_and_can_inherit_parent_documentation():
    # _finddoc 通过模块和 qualname 找父定义；函数内局部类无法从模块路径重新定位。
    inherited = inspect.getdoc(UndocumentedChild.operation)
    assert inherited.startswith("Perform the inherited operation.")
    assert "\nThe indentation is normalized" in inherited

    raw = """
        First line.
            Indented detail.
    """
    assert inspect.cleandoc(raw) == "First line.\n    Indented detail."


def test_getcomments_reads_source_comments_immediately_before_an_object():
    comments = inspect.getcomments(documented_function)
    assert comments is not None
    assert "inspect.getcomments" in comments


def test_signature_exposes_all_five_parameter_kinds_in_definition_order():
    signature = inspect.signature(signature_target)
    parameters = signature.parameters

    assert list(parameters) == [
        "positional_only",
        "positional_or_keyword",
        "values",
        "required_name",
        "enabled",
        "options",
    ]
    assert parameters["positional_only"].kind is inspect.Parameter.POSITIONAL_ONLY
    assert parameters["positional_or_keyword"].kind is (
        inspect.Parameter.POSITIONAL_OR_KEYWORD
    )
    assert parameters["values"].kind is inspect.Parameter.VAR_POSITIONAL
    assert parameters["required_name"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["options"].kind is inspect.Parameter.VAR_KEYWORD
    assert parameters["positional_only"].default is inspect.Parameter.empty
    assert parameters["required_name"].kind.description == "keyword-only"
    assert signature.return_annotation is bool


def test_signature_bind_validates_calls_without_executing_the_callable():
    signature = inspect.signature(signature_target)
    bound = signature.bind(
        "first",
        3,
        4.0,
        5.0,
        required_name="job",
        trace=True,
    )

    assert bound.arguments == {
        "positional_only": "first",
        "positional_or_keyword": 3,
        "values": (4.0, 5.0),
        "required_name": "job",
        "options": {"trace": True},
    }
    assert bound.args == ("first", 3, 4.0, 5.0)
    assert bound.kwargs == {"required_name": "job", "trace": True}
    assert signature_target(*bound.args, **bound.kwargs) is True

    with pytest.raises(TypeError, match="missing a required argument"):
        signature.bind("first")
    with pytest.raises(TypeError, match="positional only"):
        signature.bind(positional_only="first", required_name="job")


def test_bind_partial_allows_missing_required_values_like_functools_partial():
    signature = inspect.signature(signature_target)
    partial = signature.bind_partial("first", enabled=False)

    assert partial.arguments == {"positional_only": "first", "enabled": False}
    assert partial.args == ("first",)
    assert partial.kwargs == {"enabled": False}


def test_apply_defaults_adds_defaults_and_empty_variadic_collections():
    signature = inspect.signature(signature_target)
    bound = signature.bind("first", required_name="job")
    assert "enabled" not in bound.arguments
    assert "values" not in bound.arguments

    bound.apply_defaults()
    assert bound.arguments == {
        "positional_only": "first",
        "positional_or_keyword": 2,
        "values": (),
        "required_name": "job",
        "enabled": True,
        "options": {},
    }


def test_bound_arguments_mapping_is_mutable_and_args_kwargs_are_dynamic_views():
    signature = inspect.signature(signature_target)
    bound = signature.bind("original", required_name="job")

    bound.arguments["positional_only"] = "changed"
    bound.arguments["enabled"] = False
    assert bound.args == ("changed",)
    assert bound.kwargs == {"required_name": "job", "enabled": False}
    assert bound.signature is signature


def test_parameter_and_signature_replace_create_validated_immutable_copies():
    signature = inspect.signature(documented_function)
    value = signature.parameters["value"]
    optional_value = value.replace(default=1, annotation=float)
    replaced = signature.replace(
        parameters=[optional_value, signature.parameters["scale"]],
        return_annotation=float,
    )

    assert value.default is inspect.Parameter.empty
    assert optional_value.default == 1
    assert optional_value.annotation is float
    assert str(replaced) == "(value: float = 1, scale: int = 2) -> float"
    assert replaced.return_annotation is float

    with pytest.raises(ValueError, match="wrong parameter order"):
        inspect.Signature(
            [
                inspect.Parameter("named", inspect.Parameter.KEYWORD_ONLY),
                inspect.Parameter("positional", inspect.Parameter.POSITIONAL_ONLY),
            ]
        )


def test_signature_follows_wrapped_by_default_and_can_inspect_wrapper_itself():
    def original(value: int, *, scale: int = 2) -> int:
        return value * scale

    @functools.wraps(original)
    def wrapper(*args, **kwargs):
        return original(*args, **kwargs)

    assert inspect.signature(wrapper) == inspect.signature(original)
    # 停止追踪 __wrapped__ 不会撤销 functools.wraps 已复制到 wrapper 的返回注解。
    assert str(inspect.signature(wrapper, follow_wrapped=False)) == "(*args, **kwargs) -> int"
    assert inspect.unwrap(wrapper) is original


def test_custom_signature_can_describe_a_dynamic_callable_contract():
    class DynamicCallable:
        def __call__(self, *args, **kwargs):
            return args, kwargs

    callable_object = DynamicCallable()
    callable_object.__signature__ = inspect.Signature(
        [
            inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter(
                "mode",
                inspect.Parameter.KEYWORD_ONLY,
                default="safe",
            ),
        ],
        return_annotation=tuple,
    )

    assert str(inspect.signature(callable_object)) == "(value, /, *, mode='safe') -> tuple"
    assert inspect.signature(callable_object).bind(3, mode="fast").arguments == {
        "value": 3,
        "mode": "fast",
    }


def test_unwrap_stop_can_keep_an_intermediate_wrapper_and_cycles_are_rejected():
    def original(value):
        return value

    @functools.wraps(original)
    def inner(*args, **kwargs):
        return original(*args, **kwargs)

    @functools.wraps(inner)
    def outer(*args, **kwargs):
        return inner(*args, **kwargs)

    inner.stop_here = True
    assert inspect.unwrap(outer, stop=lambda value: hasattr(value, "stop_here")) is inner

    def cyclic():
        pass

    cyclic.__wrapped__ = cyclic
    with pytest.raises(ValueError, match="wrapper loop"):
        inspect.unwrap(cyclic)


def test_get_annotations_returns_fresh_mapping_and_optionally_evaluates_strings():
    def parse(value):
        return value

    parse.__annotations__ = {"value": "int", "return": "list[str]"}
    raw = inspect.get_annotations(parse)
    second_raw = inspect.get_annotations(parse)
    evaluated = inspect.get_annotations(parse, eval_str=True)

    assert raw == {"value": "int", "return": "list[str]"}
    assert second_raw == raw
    assert second_raw is not raw
    assert evaluated == {"value": int, "return": list[str]}
    raw["value"] = "changed"
    assert parse.__annotations__["value"] == "int"


def test_get_annotations_does_not_inherit_a_parent_class_mapping():
    class Parent:
        identifier: int

    class Child(Parent):
        pass

    assert inspect.get_annotations(Parent) == {"identifier": int}
    assert inspect.get_annotations(Child) == {}
    with pytest.raises(TypeError):
        inspect.get_annotations(Parent())


def test_evaluating_string_annotations_executes_expressions_and_propagates_errors():
    def parse(value):
        return value

    parse.__annotations__ = {"value": "MissingType"}
    with pytest.raises(NameError, match="MissingType"):
        inspect.get_annotations(parse, eval_str=True)
    # eval_str 使用 eval；不可信注解不是被动数据，文档生成器不应
    # 无条件求值。


def test_getclosurevars_separates_nonlocals_globals_builtins_and_unbound_names():
    captured = 5

    def closure(value):
        return captured + GLOBAL_FOR_CLOSURE + len(value) + missing_name

    variables = inspect.getclosurevars(closure)
    assert variables.nonlocals == {"captured": 5}
    assert variables.globals == {"GLOBAL_FOR_CLOSURE": 10}
    assert variables.builtins == {"len": builtins.len}
    assert variables.unbound == {"missing_name"}


def test_getclasstree_represents_inheritance_and_unique_removes_duplicate_entries():
    class Root:
        pass

    class Left(Root):
        pass

    class Right(Root):
        pass

    class Diamond(Left, Right):
        pass

    tree = inspect.getclasstree([Root, Left, Right, Diamond], unique=True)

    def flatten(nodes):
        for node in nodes:
            if isinstance(node, list):
                yield from flatten(node)
            else:
                yield node[0]

    classes = list(flatten(tree))
    assert {Root, Left, Right, Diamond} <= set(classes)
    assert classes.count(Diamond) == 1


def test_classify_class_attrs_reports_defining_class_and_descriptor_kind():
    attributes = {
        item.name: item for item in inspect.classify_class_attrs(ExampleService)
    }

    assert attributes["method"].kind == "method"
    assert attributes["method"].defining_class is ExampleService
    assert attributes["build"].kind == "class method"
    assert attributes["label"].kind == "property"
    assert attributes["category"].kind == "data"


def test_getfullargspec_keeps_legacy_shape_while_signature_is_more_precise():
    specification = inspect.getfullargspec(signature_target)
    assert specification.args == ["positional_only", "positional_or_keyword"]
    assert specification.varargs == "values"
    assert specification.varkw == "options"
    assert specification.defaults == (2,)
    assert specification.kwonlyargs == ["required_name", "enabled"]
    assert specification.kwonlydefaults == {"enabled": True}
    assert specification.annotations["return"] is bool
    # FullArgSpec 不单独表示 positional-only，现代调用适配优先使用 Signature。


def test_getcallargs_returns_binding_mapping_but_signature_bind_is_preferred():
    mapping = inspect.getcallargs(
        signature_target,
        "first",
        required_name="job",
        trace=True,
    )
    assert mapping == {
        "positional_only": "first",
        "positional_or_keyword": 2,
        "values": (),
        "required_name": "job",
        "enabled": True,
        "options": {"trace": True},
    }


def test_currentframe_and_frameinfo_expose_code_location_and_locals_without_leaking():
    teaching_local = "visible"
    frame = inspect.currentframe()
    try:
        assert frame is not None
        information = inspect.getframeinfo(frame, context=1)
        assert information.function.startswith("test_currentframe")
        assert Path(information.filename) == Path(__file__)
        assert frame.f_locals["teaching_local"] == "visible"
        assert frame.f_code is frame.f_locals["frame"].f_code
    finally:
        # 当前 frame 的局部变量引用 frame 自己；显式删除可避免等待循环 GC。
        del frame


def test_stack_and_outerframes_order_from_current_call_to_outermost():
    frame = inspect.currentframe()
    stack = None
    outer = None
    try:
        stack = inspect.stack(context=0)
        outer = inspect.getouterframes(frame, context=0)
        assert stack[0].function.startswith("test_stack_and_outerframes")
        assert outer[0].frame is frame
        assert stack[-1].frame.f_back is None
        assert outer[-1].frame.f_back is None
    finally:
        del stack, outer, frame


def test_trace_and_innerframes_follow_an_exception_toward_its_raise_site():
    def inner():
        raise LookupError("missing")

    def outer():
        inner()

    records = None
    inner_records = None
    try:
        outer()
    except LookupError as error:
        records = inspect.trace(context=0)
        inner_records = inspect.getinnerframes(error.__traceback__, context=0)
        assert records[-1].function == "inner"
        assert inner_records[-1].function == "inner"
        assert inner_records[0].function.startswith("test_trace_and_innerframes")
    finally:
        del records, inner_records


def test_getattr_static_does_not_invoke_property_or_getattr_fallback():
    events = []

    class DynamicObject:
        @property
        def dangerous(self):
            events.append("property executed")
            return 42

        def __getattr__(self, name):
            events.append(f"fallback:{name}")
            return "dynamic"

    value = DynamicObject()
    assert inspect.getattr_static(value, "dangerous") is DynamicObject.__dict__["dangerous"]
    assert events == []
    assert value.dangerous == 42
    assert events == ["property executed"]

    missing = object()
    assert inspect.getattr_static(value, "generated", missing) is missing
    assert value.generated == "dynamic"
    assert events[-1] == "fallback:generated"


def test_getattr_static_returns_slot_descriptor_instead_of_resolving_its_value():
    class Slotted:
        __slots__ = ("value",)

    instance = Slotted()
    instance.value = 7
    descriptor = inspect.getattr_static(instance, "value")

    assert descriptor is Slotted.__dict__["value"]
    assert inspect.ismemberdescriptor(descriptor)
    assert descriptor.__get__(instance, Slotted) == 7


def test_generator_state_and_locals_change_across_created_suspended_running_closed():
    holder = {}

    def stateful_generator(seed):
        local_value = seed * 2
        running_state = inspect.getgeneratorstate(holder["generator"])
        yield running_state, local_value

    generator = stateful_generator(3)
    holder["generator"] = generator
    assert inspect.getgeneratorstate(generator) == inspect.GEN_CREATED
    assert inspect.getgeneratorlocals(generator)["seed"] == 3

    running_state, local_value = next(generator)
    assert running_state == inspect.GEN_RUNNING
    assert local_value == 6
    assert inspect.getgeneratorstate(generator) == inspect.GEN_SUSPENDED
    assert inspect.getgeneratorlocals(generator)["local_value"] == 6

    with pytest.raises(StopIteration):
        next(generator)
    assert inspect.getgeneratorstate(generator) == inspect.GEN_CLOSED
    assert inspect.getgeneratorlocals(generator) == {}


def test_coroutine_state_and_locals_change_while_an_event_suspends_execution():
    async def scenario():
        started = asyncio.Event()
        finish = asyncio.Event()
        holder = {}

        async def worker(seed):
            local_value = seed * 2
            running_state = inspect.getcoroutinestate(holder["coroutine"])
            started.set()
            await finish.wait()
            return running_state, local_value

        coroutine = worker(4)
        holder["coroutine"] = coroutine
        assert inspect.getcoroutinestate(coroutine) == inspect.CORO_CREATED
        assert inspect.getcoroutinelocals(coroutine)["seed"] == 4

        task = asyncio.create_task(coroutine)
        await started.wait()
        assert inspect.getcoroutinestate(coroutine) == inspect.CORO_SUSPENDED
        assert inspect.getcoroutinelocals(coroutine)["local_value"] == 8
        finish.set()
        running_state, local_value = await task

        assert running_state == inspect.CORO_RUNNING
        assert local_value == 8
        assert inspect.getcoroutinestate(coroutine) == inspect.CORO_CLOSED
        assert inspect.getcoroutinelocals(coroutine) == {}

    asyncio.run(scenario())


def test_code_object_fields_and_flags_describe_calling_convention_and_execution_kind():
    code = signature_target.__code__
    assert code.co_name == "signature_target"
    assert Path(code.co_filename) == Path(__file__)
    assert code.co_posonlyargcount == 1
    assert code.co_argcount == 2
    assert code.co_kwonlyargcount == 2
    assert code.co_flags & inspect.CO_OPTIMIZED
    assert code.co_flags & inspect.CO_NEWLOCALS
    assert code.co_flags & inspect.CO_VARARGS
    assert code.co_flags & inspect.CO_VARKEYWORDS

    assert generator_function.__code__.co_flags & inspect.CO_GENERATOR
    assert coroutine_function.__code__.co_flags & inspect.CO_COROUTINE
    assert async_generator_function.__code__.co_flags & inspect.CO_ASYNC_GENERATOR
    # CO_* 是 CPython 实现标志；判断对象类别时优先用 isgeneratorfunction 等
    # 公共谓词，只有编译器/调试器等底层工具才应直接解释位图。


def test_inspect_module_cli_can_print_details_for_a_qualified_object():
    completed = subprocess.run(
        [sys.executable, "-m", "inspect", "json:loads", "--details"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Target: json:loads" in completed.stdout
    assert "Origin:" in completed.stdout
    assert "Cached:" in completed.stdout
    assert "Line:" in completed.stdout
    assert "Loader:" not in completed.stdout
