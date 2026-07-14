"""061｜``types`` 动态建类与 CPython 解释器类型名称示例。

``types.new_class``、``prepare_class`` 和 ``resolve_bases`` 暴露了 class statement
背后的 metaclass 选择、namespace 准备与 ``__mro_entries__`` 分派。模块还为 function、
code、frame、descriptor 等没有独立 builtin 名称的运行时类型提供稳定的检查入口；
直接实例化这些底层类型时则要注意签名可能随 Python 版本变化。

当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.types.new-class python.types.exec-body
# polyglot-covers: python.types.prepare-class python.types.metaclass-prepare
# polyglot-covers: python.types.metaclass-keyword python.types.metaclass-conflict
# polyglot-covers: python.types.resolve-bases python.protocol.__mro_entries__
# polyglot-covers: python.class.__orig_bases__ python.types.NoneType
# polyglot-covers: python.types.NotImplementedType python.types.EllipsisType
# polyglot-covers: python.types.FunctionType python.types.LambdaType
# polyglot-covers: python.types.MethodType python.types.GeneratorType
# polyglot-covers: python.types.CoroutineType python.types.AsyncGeneratorType
# polyglot-covers: python.types.CodeType python.code.replace
# polyglot-covers: python.types.CellType python.types.ModuleType
# polyglot-covers: python.types.TracebackType python.types.FrameType
# polyglot-covers: python.types.builtin-callable-types python.types.descriptor-types
# polyglot-covers: python.types.GenericAlias python.types.UnionType

import asyncio
import sys
import types

import pytest


def test_new_class_exec_body_populates_namespace_and_creates_working_methods():
    """exec_body 接收将交给 metaclass 的 namespace；它必须原地写入，返回值会被忽略。"""

    def populate(namespace):
        def __init__(self, value):
            self.value = value

        def doubled(self):
            return self.value * 2

        namespace["category"] = "dynamic"
        namespace["__init__"] = __init__
        namespace["doubled"] = doubled
        return {"ignored": True}

    Generated = types.new_class("Generated", exec_body=populate)
    instance = Generated(21)

    assert Generated.__name__ == "Generated"
    assert Generated.category == "dynamic"
    assert instance.doubled() == 42
    assert not hasattr(Generated, "ignored")


def test_new_class_selects_metaclass_and_forwards_class_header_keywords():
    """kwds 中 metaclass 用于选择工厂，其余 class header 关键字传给 prepare/new。"""

    events = []

    class RecordingMeta(type):
        @classmethod
        def __prepare__(metaclass, name, bases, **keywords):
            events.append(("prepare", name, bases, dict(keywords)))
            return {"prepared": True}

        def __new__(metaclass, name, bases, namespace, **keywords):
            events.append(("new", name, bases, dict(keywords), list(namespace)))
            created = super().__new__(metaclass, name, bases, namespace)
            created.class_options = dict(keywords)
            return created

    def populate(namespace):
        namespace["answer"] = 42

    Generated = types.new_class(
        "Generated",
        kwds={"metaclass": RecordingMeta, "frozen": True},
        exec_body=populate,
    )

    assert isinstance(Generated, RecordingMeta)
    assert Generated.prepared is True
    assert Generated.answer == 42
    assert Generated.class_options == {"frozen": True}
    assert events[0] == ("prepare", "Generated", (), {"frozen": True})
    assert events[1][:4] == ("new", "Generated", (), {"frozen": True})
    assert events[1][4] == ["prepared", "answer"]


def test_prepare_class_returns_metaclass_ordered_namespace_and_cleaned_kwds_copy():
    """返回三元组可让框架分阶段建类；metaclass 项被移除，调用方原 dict 不变。"""

    class PreparedMeta(type):
        @classmethod
        def __prepare__(metaclass, name, bases, **keywords):
            return {"from_prepare": (name, dict(keywords))}

    original_keywords = {"metaclass": PreparedMeta, "mode": "strict"}

    metaclass, namespace, remaining = types.prepare_class(
        "Prepared",
        (),
        original_keywords,
    )
    namespace["first"] = 1
    namespace["second"] = 2

    assert metaclass is PreparedMeta
    assert namespace["from_prepare"] == ("Prepared", {"mode": "strict"})
    assert list(namespace) == ["from_prepare", "first", "second"]
    assert remaining == {"mode": "strict"}
    assert original_keywords == {"metaclass": PreparedMeta, "mode": "strict"}


def test_prepare_class_default_namespace_preserves_insertion_order():
    """没有自定义 __prepare__ 时，3.6+ 默认 namespace 仍按写入顺序迭代。"""

    metaclass, namespace, keywords = types.prepare_class("Plain")
    namespace["zebra"] = 1
    namespace["apple"] = 2

    assert metaclass is type
    assert list(namespace) == ["zebra", "apple"]
    assert keywords == {}


def test_prepare_class_reports_incompatible_metaclasses_before_body_execution():
    """多个 base 的 metaclass 必须存在共同的最派生候选，否则 class header 本身失败。"""

    class FirstMeta(type):
        pass

    class SecondMeta(type):
        pass

    class FirstBase(metaclass=FirstMeta):
        pass

    class SecondBase(metaclass=SecondMeta):
        pass

    with pytest.raises(TypeError, match="metaclass conflict"):
        types.prepare_class("Broken", (FirstBase, SecondBase))


def test_resolve_bases_expands_non_type_mro_entries_and_new_class_records_originals():
    """非 type base 可用 __mro_entries__ 替换为真实 base；原表达式保存在 __orig_bases__。"""

    class ConcreteBase:
        inherited = "base value"

    class BaseProvider:
        def __init__(self):
            self.seen_bases = None

        def __mro_entries__(self, original_bases):
            self.seen_bases = original_bases
            return (ConcreteBase,)

    provider = BaseProvider()

    assert types.resolve_bases((provider,)) == (ConcreteBase,)
    assert provider.seen_bases == (provider,)

    Generated = types.new_class("Generated", (provider,))

    assert Generated.__bases__ == (ConcreteBase,)
    assert Generated.__orig_bases__ == (provider,)
    assert Generated().inherited == "base value"


def test_resolve_bases_leaves_types_and_objects_without_mro_entries_unchanged():
    """只有非 type 且实现 __mro_entries__ 的项会展开；函数本身不验证最终 base 合法性。"""

    marker = object()
    bases = (dict, marker)

    resolved = types.resolve_bases(bases)

    assert resolved == bases


def test_python_310_exposes_types_for_singleton_values_and_union_expressions():
    """NoneType、NotImplementedType、EllipsisType 与 UnionType 在 3.10 获得公开名称。"""

    union = int | str

    assert types.NoneType is type(None)
    assert types.NotImplementedType is type(NotImplemented)
    assert types.EllipsisType is type(Ellipsis)
    assert type(union) is types.UnionType
    assert union == str | int
    assert isinstance(42, union)
    assert isinstance("text", union)


def test_function_and_lambda_names_refer_to_the_same_runtime_type():
    """def 与 lambda 都创建 FunctionType；名称不同只是提供语义友好的检查入口。"""

    def named_function():
        return "named"

    anonymous = lambda: "lambda"

    assert types.FunctionType is types.LambdaType
    assert isinstance(named_function, types.FunctionType)
    assert isinstance(anonymous, types.LambdaType)
    assert named_function() == "named"
    assert anonymous() == "lambda"


def test_function_type_can_bind_existing_code_to_a_different_globals_mapping():
    """FunctionType 可重用 code 并提供新 globals；这种底层构造签名具有版本敏感性。"""

    def template(value):
        return factor * value

    triple = types.FunctionType(template.__code__, {"factor": 3}, "triple")

    assert triple.__name__ == "triple"
    assert triple(14) == 42
    assert triple.__code__ is template.__code__


def test_method_type_explicitly_binds_function_to_an_instance():
    """MethodType 组合 function 与 self，得到具有 __func__/__self__ 的 bound method。"""

    class Greeter:
        def __init__(self, name):
            self.name = name

    def greet(self, punctuation="!"):
        return f"Hello, {self.name}{punctuation}"

    instance = Greeter("Ada")
    bound = types.MethodType(greet, instance)

    assert bound.__self__ is instance
    assert bound.__func__ is greet
    assert bound(".") == "Hello, Ada."


def test_generator_coroutine_and_async_generator_have_distinct_runtime_types():
    """三种暂停状态机由不同语法产生；coroutine 与 async generator 都在测试内消费。"""

    def generator_function():
        yield "generator"

    async def coroutine_function():
        return "coroutine"

    async def async_generator_function():
        yield "async-generator"

    generator = generator_function()
    coroutine = coroutine_function()
    async_generator = async_generator_function()

    assert type(generator) is types.GeneratorType
    assert type(coroutine) is types.CoroutineType
    assert type(async_generator) is types.AsyncGeneratorType
    assert next(generator) == "generator"
    generator.close()
    assert asyncio.run(coroutine) == "coroutine"

    async def consume_async_generator():
        return [value async for value in async_generator]

    assert asyncio.run(consume_async_generator()) == ["async-generator"]


def test_code_replace_copies_code_object_without_direct_version_sensitive_constructor():
    """CodeType.replace 只改指定字段，避免手工传递随版本变化的 CodeType 全参数列表。"""

    def add(left, right=1):
        return left + right

    original = add.__code__
    replaced = original.replace(co_name="sum_values", co_filename="generated.py")
    rebuilt = types.FunctionType(
        replaced,
        add.__globals__,
        "public_sum",
        add.__defaults__,
    )

    assert isinstance(original, types.CodeType)
    assert isinstance(replaced, types.CodeType)
    assert replaced is not original
    assert rebuilt.__name__ == "public_sum"
    assert rebuilt.__code__.co_name == "sum_values"
    assert rebuilt.__code__.co_filename == "generated.py"
    assert rebuilt(41) == 42


def test_cell_type_identifies_storage_for_a_closure_free_variable():
    """闭包的 __closure__ 保存 cell tuple；cell_contents 是被多个函数共享的绑定。"""

    def outer(value):
        def inner():
            return value

        return inner

    closure = outer("captured")
    cell = closure.__closure__[0]

    assert type(cell) is types.CellType
    assert cell.cell_contents == "captured"
    assert closure() == "captured"


def test_module_type_creates_basic_module_but_not_full_import_system_state():
    """ModuleType 适合简单动态 namespace；真正导入模块应由 module_from_spec 补齐状态。"""

    module = types.ModuleType("plugins.demo", "demo module")
    module.enabled = True

    assert module.__name__ == "plugins.demo"
    assert module.__doc__ == "demo module"
    assert module.enabled is True
    assert getattr(module, "__loader__", None) is None
    assert module.__package__ is None
    assert module.__spec__ is None


def test_traceback_and_frame_types_name_objects_from_exception_execution_state():
    """异常 traceback 链接 FrameType；保留 frame 也会保留局部变量，检查后应释放引用。"""

    traceback = None
    frame = None
    try:
        1 / 0
    except ZeroDivisionError:
        traceback = sys.exc_info()[2]
        frame = traceback.tb_frame

    assert type(traceback) is types.TracebackType
    assert type(frame) is types.FrameType
    assert traceback.tb_frame is frame
    assert frame.f_code.co_name == (
        "test_traceback_and_frame_types_name_objects_from_exception_execution_state"
    )

    del traceback, frame


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        (len, types.BuiltinFunctionType),
        ([].append, types.BuiltinMethodType),
        (object.__init__, types.WrapperDescriptorType),
        (object().__str__, types.MethodWrapperType),
        (str.join, types.MethodDescriptorType),
        (dict.__dict__["fromkeys"], types.ClassMethodDescriptorType),
        (types.FrameType.f_locals, types.GetSetDescriptorType),
    ],
)
def test_types_names_common_builtin_callable_and_descriptor_kinds(value, expected_type):
    """不要用易变的 repr 猜底层 callable/descriptor 种类，直接使用 types 公共名称。"""

    assert type(value) is expected_type


def test_member_descriptor_type_matches_slot_storage_descriptor_on_cpython():
    """CPython 为普通 __slots__ 字段创建 member_descriptor；其他实现允许与 getset 相同。"""

    class Slotted:
        __slots__ = ("value",)

    assert type(Slotted.value) is types.MemberDescriptorType
    instance = Slotted()
    instance.value = 42
    assert Slotted.value.__get__(instance, Slotted) == 42


def test_generic_alias_constructor_matches_bracket_syntax_and_exposes_metadata():
    """GenericAlias 可显式构造；origin 是裸容器，args 保存参数化类型元数据。"""

    explicit = types.GenericAlias(dict, (str, int))
    bracketed = dict[str, int]

    assert explicit == bracketed
    assert type(explicit) is types.GenericAlias
    assert explicit.__origin__ is dict
    assert explicit.__args__ == (str, int)
