"""053｜``types`` 动态建类与 CPython 解释器类型名称示例。

``types.new_class``、``prepare_class`` 和 ``resolve_bases`` 暴露了 class statement
背后的 metaclass 选择、namespace 准备与 ``__mro_entries__`` 分派。模块还为 function、
code、frame、descriptor 等没有独立 builtin 名称的运行时类型提供稳定的检查入口；
直接实例化这些底层类型时则要注意签名可能随 Python 版本变化。


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
from collections.abc import Awaitable
import inspect

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


# ``types`` 只读映射视图、轻量 namespace、动态类属性与 coroutine 工具。
#
# ``MappingProxyType`` 是底层 mapping 的动态只读视图，不是不可变快照；
# ``SimpleNamespace`` 是允许任意 attribute 的轻量对象，也不是带字段约束的 record。
# ``DynamicClassAttribute`` 则让同名属性在 instance 和 class 上走不同分派。
#
# 最后一组案例展示 ``types.coroutine`` 对 generator function、返回 Generator 的普通
# function 和其他返回值采用不同包装路径。

# polyglot-covers: python.types.MappingProxyType python.mapping-proxy.dynamic-view
# polyglot-covers: python.mapping-proxy.read-only python.mapping-proxy.shallow-readonly
# polyglot-covers: python.mapping-proxy.copy python.mapping-proxy.union
# polyglot-covers: python.mapping-proxy.views python.mapping-proxy.reversed
# polyglot-covers: python.types.SimpleNamespace python.simple-namespace.attributes
# polyglot-covers: python.simple-namespace.vars python.simple-namespace.equality
# polyglot-covers: python.simple-namespace.repr-order python.simple-namespace.not-record
# polyglot-covers: python.types.DynamicClassAttribute python.dynamic-class-attribute.instance
# polyglot-covers: python.dynamic-class-attribute.class-getattr
# polyglot-covers: python.dynamic-class-attribute.setter-deleter
# polyglot-covers: python.types.coroutine python.types.coroutine-generator-in-place
# polyglot-covers: python.types.coroutine-generator-wrapper
# polyglot-covers: python.types.coroutine-unvalidated-return




async def await_value(value):
    """让 asyncio.run 消费任意 awaitable，而不要求输入本身是 native coroutine。"""

    return await value


def test_mapping_proxy_is_read_only_but_reflects_source_mapping_changes():
    """proxy 禁止经自身增删改；原 mapping 的后续变化仍实时可见。"""

    source = {"mode": "development"}
    proxy = types.MappingProxyType(source)

    assert proxy["mode"] == "development"
    assert len(proxy) == 1

    with pytest.raises(TypeError, match="does not support item assignment"):
        proxy["mode"] = "production"
    with pytest.raises(TypeError, match="does not support item deletion"):
        del proxy["mode"]

    source["mode"] = "production"
    source["debug"] = False

    assert dict(proxy) == {"mode": "production", "debug": False}


def test_mapping_proxy_readonly_rule_is_shallow_not_recursive_immutability():
    """不能替换 mapping value，但若 value 自身可变，读取后仍能修改那个对象。"""

    source = {"features": ["search"]}
    proxy = types.MappingProxyType(source)

    proxy["features"].append("export")

    assert source == {"features": ["search", "export"]}
    assert proxy["features"] is source["features"]


def test_mapping_proxy_views_remain_live_and_reversed_uses_mapping_order():
    """keys/items 是动态 view；3.9+ reversed(proxy) 按底层 mapping 插入顺序反向。"""

    source = {"first": 1, "second": 2}
    proxy = types.MappingProxyType(source)
    keys = proxy.keys()
    items = proxy.items()

    source["third"] = 3

    assert list(keys) == ["first", "second", "third"]
    assert list(items) == [("first", 1), ("second", 2), ("third", 3)]
    assert list(reversed(proxy)) == ["third", "second", "first"]


def test_mapping_proxy_copy_is_snapshot_structure_but_still_shares_nested_values():
    """copy 返回普通浅拷贝 dict：顶层不再动态，内部可变 value 仍是同一对象。"""

    source = {"options": ["fast"]}
    proxy = types.MappingProxyType(source)
    copied = proxy.copy()

    source["enabled"] = True
    source["options"].append("safe")

    assert isinstance(copied, dict)
    assert "enabled" not in copied
    assert copied["options"] == ["fast", "safe"]
    assert copied["options"] is source["options"]


def test_mapping_proxy_union_delegates_and_returns_a_new_mutable_dict():
    """3.9+ ``|`` 交给底层 mapping；右侧覆盖同名键，结果不是另一个 proxy。"""

    source = {"timeout": 10, "retries": 2}
    proxy = types.MappingProxyType(source)

    merged = proxy | {"timeout": 30, "verbose": True}

    assert merged == {"timeout": 30, "retries": 2, "verbose": True}
    assert type(merged) is dict
    merged["retries"] = 5
    assert source["retries"] == 2


def test_class_dict_is_a_real_mapping_proxy_that_tracks_setattr():
    """class.__dict__ 使用 mappingproxy 保护类型 namespace；setattr 是合法修改入口。"""

    class Configuration:
        mode = "development"

    namespace = Configuration.__dict__

    assert type(namespace) is types.MappingProxyType
    with pytest.raises(TypeError):
        namespace["mode"] = "production"

    setattr(Configuration, "mode", "production")
    assert namespace["mode"] == "production"


def test_simple_namespace_initializes_keywords_and_allows_add_change_delete():
    """关键字直接进入 __dict__；attribute 操作没有 schema 或类型验证。"""

    namespace = types.SimpleNamespace(host="localhost", port=8000)

    assert namespace.host == "localhost"
    assert namespace.port == 8000

    namespace.port = "not validated"
    namespace.debug = True
    del namespace.host

    assert vars(namespace) == {"port": "not validated", "debug": True}
    with pytest.raises(AttributeError):
        namespace.host


def test_simple_namespace_only_accepts_keyword_initialization_in_python_310():
    """3.10 构造器不是 dict 构造器；位置 mapping 会被拒绝，应使用 ``**mapping``。"""

    with pytest.raises(TypeError):
        types.SimpleNamespace({"answer": 42})

    namespace = types.SimpleNamespace(**{"answer": 42})
    assert namespace.answer == 42


def test_simple_namespace_equality_compares_namespace_dicts_not_arbitrary_mappings():
    """两个 SimpleNamespace 按 __dict__ 相等；普通 dict 走 NotImplemented 后并不相等。"""

    first = types.SimpleNamespace(name="Ada", skills=["Python"])
    second = types.SimpleNamespace(name="Ada", skills=["Python"])

    assert first == second
    assert first != {"name": "Ada", "skills": ["Python"]}

    second.skills.append("C++")
    assert first != second


def test_simple_namespace_repr_uses_attribute_insertion_order_since_python_39():
    """repr 适合调试且保留 __dict__ 插入顺序，但不应当作持久序列化格式。"""

    namespace = types.SimpleNamespace(beta=2)
    namespace.alpha = 1

    assert repr(namespace) == "namespace(beta=2, alpha=1)"


def test_simple_namespace_is_attribute_container_not_mapping_or_structured_record():
    """它没有订阅接口、必填字段或冻结能力；结构化数据应选择 dataclass/namedtuple。"""

    namespace = types.SimpleNamespace(answer=42)

    with pytest.raises(TypeError, match="not subscriptable"):
        namespace["answer"]

    namespace.answer = None
    namespace.unexpected = object()
    assert set(vars(namespace)) == {"answer", "unexpected"}


def test_dynamic_class_attribute_routes_instance_and_class_access_differently():
    """instance 调用 descriptor getter；class 访问触发 AttributeError 后交给 metaclass。"""

    class VirtualAttributeMeta(type):
        def __getattr__(cls, name):
            if name == "label":
                return f"class-label:{cls.__name__}"
            raise AttributeError(name)

    class Item(metaclass=VirtualAttributeMeta):
        def __init__(self, label):
            self._label = label

        @types.DynamicClassAttribute
        def label(self):
            return f"instance-label:{self._label}"

    assert Item("one").label == "instance-label:one"
    assert Item.label == "class-label:Item"
    assert isinstance(vars(Item)["label"], types.DynamicClassAttribute)


def test_dynamic_class_attribute_without_metaclass_fallback_raises_on_class_access():
    """descriptor 故意在 class access 抛 AttributeError；没有 __getattr__ 就没有虚拟类值。"""

    class Item:
        @types.DynamicClassAttribute
        def label(self):
            return "instance-only"

    assert Item().label == "instance-only"
    with pytest.raises(AttributeError):
        Item.label


def test_dynamic_class_attribute_supports_property_style_setter_and_deleter():
    """与 property 相同，setter/deleter 只操作 instance；class 分派规则保持不变。"""

    class Item:
        def __init__(self):
            self._value = 1

        @types.DynamicClassAttribute
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            self._value = new_value

        @value.deleter
        def value(self):
            del self._value

    item = Item()
    item.value = 2
    assert item.value == 2

    del item.value
    with pytest.raises(AttributeError):
        item.value


def test_coroutine_marks_generator_function_in_place_as_generator_based_coroutine():
    """输入本来就是 generator function 时，装饰器修改 code flag 并返回同一 function。"""

    def legacy_operation():
        if False:
            yield None
        return "legacy result"

    original = legacy_operation
    decorated = types.coroutine(legacy_operation)
    value = decorated()

    assert decorated is original
    assert inspect.isgeneratorfunction(decorated)
    assert inspect.isawaitable(value)
    assert isinstance(value, types.GeneratorType)
    assert not isinstance(value, Awaitable)
    assert asyncio.run(await_value(value)) == "legacy result"


def test_coroutine_wraps_non_generator_function_that_returns_a_generator():
    """普通 factory 返回 Generator 时会得到 awaitable proxy，而不是修改原 function。"""

    def completed_generator():
        if False:
            yield None
        return "wrapped result"

    def factory():
        return completed_generator()

    decorated = types.coroutine(factory)
    value = decorated()

    assert decorated is not factory
    assert not inspect.isgenerator(value)
    assert inspect.isawaitable(value)
    assert asyncio.run(await_value(value)) == "wrapped result"


def test_coroutine_wrapper_returns_unrecognized_result_unchanged_until_real_await():
    """非 generator factory 的其他返回值直接透传；装饰器不保证每次结果都可 await。"""

    marker = object()

    def factory():
        return marker

    decorated = types.coroutine(factory)
    result = decorated()

    assert result is marker
    assert not inspect.isawaitable(result)
