"""013｜函数/类装饰器与 metaclass 创建流水线的可执行示例。

装饰器在 ``def`` / ``class`` 创建对象后接收它，并把返回值重新绑定到原名称；
多层 decorator expression 从上到下求值，却从下到上应用。类本身由 metaclass
创建：``__prepare__`` 提供类体命名空间，metaclass ``__new__`` / ``__init__``
创建并初始化类对象，metaclass ``__call__`` 又包围日后的实例构造。

内容基于 Python 3.10 Function/Class definitions、Customizing class creation、
内置 type 和 functools.wraps。

"""

# polyglot-covers: python.syntax.function-decorator python.syntax.class-decorator
# polyglot-covers: python.decorator.evaluation-order
# polyglot-covers: python.decorator.application-order
# polyglot-covers: python.stdlib.functools.wraps
# polyglot-covers: python.builtin.type-dynamic-construction
# polyglot-covers: python.metaclass.__prepare__ python.metaclass.__new__
# polyglot-covers: python.metaclass.__init__ python.metaclass.__call__
# polyglot-covers: python.metaclass.selection python.metaclass.conflict

import functools
import inspect

import pytest


def test_function_decorator_receives_function_and_rebinds_its_name():
    """最简单的 decorator 返回 wrapper，原函数名随后指向 wrapper。"""

    events = []

    def trace(function):
        events.append(("decorate", function.__name__))

        def wrapper(*args, **kwargs):
            events.append(("call", args, kwargs))
            return function(*args, **kwargs)

        return wrapper

    @trace
    def add(left, right=0):
        return left + right

    assert events == [("decorate", "add")]
    assert add(2, right=3) == 5
    assert events == [
        ("decorate", "add"),
        ("call", (2,), {"right": 3}),
    ]
    assert add.__name__ == "wrapper"

    # 语义近似 `add = trace(add)`。未使用 wraps 时，绑定名称、文档和注解属于
    # wrapper，而不是原函数；这也是调试和 API 文档经常“只看到 wrapper”的原因。


def test_multiple_decorators_evaluate_top_down_and_apply_bottom_up():
    """decorator expression 的求值顺序与实际包裹顺序相反。"""

    events = []

    def configured(label):
        events.append(("evaluate", label))

        def decorate(function):
            events.append(("apply", label))

            @functools.wraps(function)
            def wrapper():
                events.append(("call", label))
                return function()

            return wrapper

        return decorate

    @configured("top")
    @configured("bottom")
    def operation():
        events.append(("body", "operation"))
        return "done"

    assert events == [
        ("evaluate", "top"),
        ("evaluate", "bottom"),
        ("apply", "bottom"),
        ("apply", "top"),
    ]

    assert operation() == "done"
    assert events[-3:] == [
        ("call", "top"),
        ("call", "bottom"),
        ("body", "operation"),
    ]

    # 等价关系是 operation = top(bottom(operation))。最靠近 def 的 bottom
    # 先应用，最上面的 top 成为调用时最外层 wrapper。


def test_decorator_factory_configuration_runs_at_definition_time_once():
    """带参数 decorator 的 factory 在定义函数时执行，不在每次调用时执行。"""

    events = []

    def repeat(times):
        events.append(("configured", times))

        def decorate(function):
            def wrapper(*args, **kwargs):
                return [function(*args, **kwargs) for _ in range(times)]

            return wrapper

        return decorate

    @repeat(2)
    def label(value):
        return f"<{value}>"

    assert events == [("configured", 2)]
    assert label("Python") == ["<Python>", "<Python>"]
    assert label("data") == ["<data>", "<data>"]
    assert events == [("configured", 2)]


def test_wrapper_must_forward_arguments_return_value_and_exceptions():
    """透明 wrapper 应完整转发调用协议，且不意外改变异常。"""

    calls = []

    def transparent(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            calls.append((args, kwargs))
            return function(*args, **kwargs)

        return wrapper

    @transparent
    def divide(numerator, denominator=1):
        return numerator / denominator

    assert divide(6, denominator=2) == 3
    assert calls == [((6,), {"denominator": 2})]

    with pytest.raises(ZeroDivisionError):
        divide(1, 0)

    # wrapper 没有捕获异常，所以原 ZeroDivisionError 自然传播；若装饰器只负责
    # 日志或计时，不应擅自把异常改成 None 或成功值。


def test_wrapper_that_forgets_return_silently_discards_original_result():
    """wrapper 调用了原函数仍可能因漏写 return 而破坏 API。"""

    events = []

    def incorrect(function):
        def wrapper(*args, **kwargs):
            events.append(function(*args, **kwargs))
            # 故意不返回原函数结果。

        return wrapper

    @incorrect
    def multiply(left, right):
        return left * right

    assert multiply(3, 4) is None
    assert events == [12]


def test_functools_wraps_preserves_metadata_and_original_function_link():
    """``wraps`` 复制常用元数据，并通过 ``__wrapped__`` 保留可追踪链。"""

    originals = []

    def documented(function):
        originals.append(function)

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper

    @documented
    def greet(name: str, punctuation: str = "!") -> str:
        """Build one greeting."""

        return f"Hello, {name}{punctuation}"

    original = originals[0]

    assert greet.__name__ == "greet"
    assert greet.__doc__ == "Build one greeting."
    assert greet.__annotations__ == {
        "name": str,
        "punctuation": str,
        "return": str,
    }
    assert greet.__wrapped__ is original
    assert inspect.signature(greet) == inspect.signature(original)
    assert greet("Python", punctuation="?") == "Hello, Python?"


def test_class_decorator_receives_the_created_class_and_can_register_it():
    """class decorator 在类对象创建完成后运行，可原样返回并附加外部行为。"""

    registry = {}

    def register(key):
        def decorate(cls):
            registry[key] = cls
            cls.registry_key = key
            return cls

        return decorate

    @register("json")
    class JsonPlugin:
        pass

    assert registry == {"json": JsonPlugin}
    assert JsonPlugin.registry_key == "json"
    assert isinstance(JsonPlugin(), JsonPlugin)


def test_class_decorator_can_replace_the_class_binding_with_another_object():
    """decorator 返回值不必是类；原类名会绑定到任何返回对象。"""

    created_classes = []

    def instantiate(cls):
        created_classes.append(cls)
        return cls()

    @instantiate
    class Settings:
        mode = "draft"

    assert len(created_classes) == 1
    assert isinstance(Settings, created_classes[0])
    assert not isinstance(Settings, type)
    assert Settings.mode == "draft"

    # 这是合法但会显著改变读者预期的写法。类 decorator 若返回错误对象，名称
    # 仍会静默重绑定，后续继承或实例化才暴露问题。


def test_three_argument_type_dynamically_creates_a_class():
    """``type(name, bases, namespace)`` 是 class 语句底层能力的直接入口。"""

    class Base:
        category = "base"

    def describe(self):
        return self.category, self.value

    DynamicRecord = type(
        "DynamicRecord",
        (Base,),
        {"category": "dynamic", "describe": describe},
    )
    record = DynamicRecord()
    record.value = 42

    assert DynamicRecord.__name__ == "DynamicRecord"
    assert DynamicRecord.__bases__ == (Base,)
    assert type(DynamicRecord) is type
    assert record.describe() == ("dynamic", 42)


def test_metaclass_prepare_new_and_init_run_around_class_body():
    """metaclass 分阶段提供 namespace、创建类对象并初始化类对象。"""

    events = []
    namespace_writes = []

    class RecordingNamespace(dict):
        def __setitem__(self, key, value):
            namespace_writes.append(key)
            super().__setitem__(key, value)

    class TrackingMeta(type):
        @classmethod
        def __prepare__(metacls, name, bases, **kwargs):
            events.append(("prepare", name, kwargs["marker"]))
            return RecordingNamespace()

        def __new__(metacls, name, bases, namespace, **kwargs):
            marker = kwargs.pop("marker")
            events.append(("new", name, marker))
            namespace["created_by_meta"] = True
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        def __init__(cls, name, bases, namespace, **kwargs):
            marker = kwargs.pop("marker")
            events.append(("init", name, marker))
            super().__init__(name, bases, namespace, **kwargs)

    class PreparedClass(metaclass=TrackingMeta, marker="tracked"):
        first = 1
        second = 2

    assert events == [
        ("prepare", "PreparedClass", "tracked"),
        ("new", "PreparedClass", "tracked"),
        ("init", "PreparedClass", "tracked"),
    ]
    assert namespace_writes[:4] == ["__module__", "__qualname__", "first", "second"]
    assert "created_by_meta" in namespace_writes
    assert PreparedClass.created_by_meta is True

    # __prepare__ 在类体执行前返回 mapping；类体的赋值依次写入它。__new__
    # 收到完成的 namespace 并必须返回类对象，随后 __init__ 初始化该类对象。


def test_metaclass_call_wraps_instance_new_and_init():
    """调用类时先进入 metaclass ``__call__``，再运行实例构造两阶段。"""

    events = []

    class ConstructionMeta(type):
        def __call__(cls, *args, **kwargs):
            events.append(("meta-call-before", args, kwargs))
            instance = super().__call__(*args, **kwargs)
            events.append(("meta-call-after", instance.value))
            return instance

    class Product(metaclass=ConstructionMeta):
        def __new__(cls, value):
            events.append(("instance-new", value))
            return super().__new__(cls)

        def __init__(self, value):
            events.append(("instance-init", value))
            self.value = value

    product = Product(7)

    assert product.value == 7
    assert events == [
        ("meta-call-before", (7,), {}),
        ("instance-new", 7),
        ("instance-init", 7),
        ("meta-call-after", 7),
    ]

    # metaclass.__call__ 控制“调用类以创建实例”；实例自身是否可调用则由
    # Product.__call__ 决定，是完全不同的协议层。


def test_metaclass_keyword_can_be_consumed_then_forwarded_to_init_subclass():
    """metaclass 可消费自己的 class keyword，并把其余项交给基类 hook。"""

    class OptionMeta(type):
        def __new__(metacls, name, bases, namespace, **kwargs):
            meta_tag = kwargs.pop("meta_tag", None)
            cls = super().__new__(metacls, name, bases, namespace, **kwargs)
            cls.meta_tag = meta_tag
            return cls

        def __init__(cls, name, bases, namespace, **kwargs):
            # __new__ 已负责把剩余 keyword 交给 __init_subclass__；metaclass
            # initializer 仍会收到原始 class keyword，因此在此消费而不再转发。
            super().__init__(name, bases, namespace)

    class FeatureBase:
        def __init_subclass__(cls, *, feature=None, **kwargs):
            cls.feature = feature
            super().__init_subclass__(**kwargs)

    class Configured(
        FeatureBase,
        metaclass=OptionMeta,
        meta_tag="from-meta",
        feature="from-base-hook",
    ):
        pass

    assert Configured.meta_tag == "from-meta"
    assert Configured.feature == "from-base-hook"


def test_most_derived_compatible_metaclass_is_selected_from_bases():
    """多个基类的 metaclass 有继承关系时，选择最具体的兼容类型。"""

    class BaseMeta(type):
        pass

    class SpecializedMeta(BaseMeta):
        pass

    class First(metaclass=BaseMeta):
        pass

    class Second(metaclass=SpecializedMeta):
        pass

    class Combined(First, Second):
        pass

    assert type(Combined) is SpecializedMeta
    assert issubclass(SpecializedMeta, BaseMeta)


def test_unrelated_base_metaclasses_cause_a_class_creation_conflict():
    """候选 metaclass 互不兼容时，Python 拒绝猜测哪一个应控制新类。"""

    class LeftMeta(type):
        pass

    class RightMeta(type):
        pass

    class Left(metaclass=LeftMeta):
        pass

    class Right(metaclass=RightMeta):
        pass

    with pytest.raises(TypeError, match="metaclass conflict"):
        class Impossible(Left, Right):
            pass
