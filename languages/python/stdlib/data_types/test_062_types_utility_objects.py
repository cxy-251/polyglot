"""062｜``types`` 只读映射视图、轻量 namespace、动态类属性与 coroutine 工具。

``MappingProxyType`` 是底层 mapping 的动态只读视图，不是不可变快照；
``SimpleNamespace`` 是允许任意 attribute 的轻量对象，也不是带字段约束的 record。
``DynamicClassAttribute`` 则让同名属性在 instance 和 class 上走不同分派。

最后一组案例展示 ``types.coroutine`` 对 generator function、返回 Generator 的普通
function 和其他返回值采用不同包装路径。当前文件尚未经过 pytest 验证。
"""

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

import asyncio
from collections.abc import Awaitable
import inspect
import types

import pytest


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
