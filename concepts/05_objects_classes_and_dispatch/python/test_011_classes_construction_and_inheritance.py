"""011｜类定义、实例构造、方法绑定与协作式继承的可执行示例。

``class`` 先执行类体形成命名空间，再由元类创建类对象。调用类时，``__new__``
负责创建并返回对象；只有结果是当前类实例时，``__init__`` 才初始化它。继承中
的 ``super()`` 不是“写死的父类”，而是从当前类之后沿实际实例的 C3 MRO
继续分派，这正是菱形继承能够每层只执行一次的基础。

内容基于 Python 3.10 Class definitions、Basic customization、内置
type/isinstance/issubclass/super 和 MRO 指南。
"""

# polyglot-covers: python.statement.class python.class.namespace
# polyglot-covers: python.builtin.type python.builtin.isinstance
# polyglot-covers: python.builtin.issubclass python.builtin.super
# polyglot-covers: python.protocol.__new__ python.protocol.__init__
# polyglot-covers: python.protocol.__init_subclass__
# polyglot-covers: python.method.instance python.method.classmethod
# polyglot-covers: python.method.staticmethod python.class.mro
# polyglot-covers: python.class.cooperative-multiple-inheritance
# polyglot-covers: python.class.name-mangling

import pytest


def test_class_statement_executes_the_body_and_creates_a_type_object():
    """类体在定义时执行，其局部绑定成为新类的命名空间。"""

    events = []

    class Language:
        events.append("class-body")
        family = "Python"

        def display(self):
            return self.family

    assert events == ["class-body"]
    assert type(Language) is type
    assert Language.__dict__["family"] == "Python"
    assert "display" in Language.__dict__
    assert Language().display() == "Python"

    # 类体只在 class 语句执行时运行一次；每次实例化不会重新执行类体。实例化
    # 调用的是已经创建好的类对象。


def test_type_isinstance_and_issubclass_answer_different_relationships():
    """``type`` 看精确类型，instance/subclass 检查则沿继承关系。"""

    class Document:
        pass

    class MarkdownDocument(Document):
        pass

    document = MarkdownDocument()

    assert type(document) is MarkdownDocument
    assert type(document) is not Document
    assert isinstance(document, MarkdownDocument)
    assert isinstance(document, Document)
    assert isinstance(document, (str, Document))
    assert issubclass(MarkdownDocument, Document)
    assert issubclass(MarkdownDocument, (dict, Document))

    # 需要接受子类的 API 应使用 isinstance，而不是 type(value) is Base；后者
    # 会拒绝遵守同一接口的派生类型。


def test_new_creates_the_instance_before_init_initializes_it():
    """``__new__`` 和 ``__init__`` 接收同一个实例，但承担不同阶段。"""

    events = []

    class Lesson:
        def __new__(cls, title):
            events.append(("new", cls.__name__, title))
            instance = super().__new__(cls)
            instance.created_in_new = True
            return instance

        def __init__(self, title):
            events.append(("init", type(self).__name__, title))
            self.title = title

    lesson = Lesson("data model")

    assert isinstance(lesson, Lesson)
    assert lesson.created_in_new is True
    assert lesson.title == "data model"
    assert events == [
        ("new", "Lesson", "data model"),
        ("init", "Lesson", "data model"),
    ]


def test_init_must_return_none_instead_of_returning_the_instance():
    """初始化器修改既有实例；它不能用返回值替换构造结果。"""

    class IncorrectInitializer:
        def __init__(self):
            return self

    with pytest.raises(TypeError, match="__init__.*None"):
        IncorrectInitializer()

    # 常见坑：__init__ 不是其他语言中的“返回新对象的构造函数”。真正控制创建
    # 结果的是 __new__；__init__ 必须隐式或显式返回 None。


def test_new_that_forgets_to_return_skips_init_and_makes_class_call_none():
    """``__new__`` 的隐式 None 不是当前类实例，因此初始化阶段不会发生。"""

    events = []

    class MissingReturn:
        def __new__(cls):
            events.append("new")
            # 故意遗漏 return super().__new__(cls)。

        def __init__(self):
            events.append("init")

    result = MissingReturn()

    assert result is None
    assert events == ["new"]


def test_new_may_return_another_type_and_then_skips_current_init():
    """factory 风格的 ``__new__`` 可返回其他对象，当前类 initializer 不运行。"""

    events = []

    class MappingFactory:
        def __new__(cls, value):
            events.append("new")
            return {"value": value}

        def __init__(self, value):
            events.append("init")

    result = MappingFactory(42)

    assert result == {"value": 42}
    assert type(result) is dict
    assert events == ["new"]


class NonNegativeInt(int):
    def __new__(cls, value):
        return super().__new__(cls, abs(value))

    def __init__(self, value):
        # int 的数值已经由 __new__ 固定；init 仍可保存额外实例元数据。
        self.original = value


def test_immutable_builtin_subclass_transforms_value_inside_new():
    """不可变基类的核心值必须在 ``__new__`` 创建阶段决定。"""

    value = NonNegativeInt(-7)

    assert value == 7
    assert isinstance(value, int)
    assert type(value) is NonNegativeInt
    assert value.original == -7

    # 到 __init__ 时 int 对象的数值已经不能修改，所以规范化参数应发生在
    # __new__。str、tuple 等其他不可变内置类型子类也遵循同一构造原则。


class Parser:
    format_name = "base"

    def __init__(self, source):
        self.source = source

    def describe(self):
        return type(self).__name__, self.source

    @classmethod
    def from_text(cls, text):
        return cls(text.strip())

    @staticmethod
    def is_blank(text):
        return not text.strip()


class JsonParser(Parser):
    format_name = "json"


def test_instance_class_and_static_methods_bind_different_first_arguments():
    """三种方法分别绑定实例、运行时类，或完全不自动绑定。"""

    parser = JsonParser.from_text("  {}  ")

    assert parser.describe() == ("JsonParser", "{}")
    assert type(parser) is JsonParser
    assert JsonParser.is_blank("   ") is True
    assert parser.is_blank("data") is False

    assert parser.describe.__self__ is parser
    assert JsonParser.from_text.__self__ is JsonParser
    assert not hasattr(JsonParser.is_blank, "__self__")

    # classmethod 使用调用时的 cls，因此继承来的替代构造器能创建 JsonParser，
    # 不会写死为 Parser。staticmethod 只是放在类命名空间中的普通函数。


def test_super_delegates_an_override_to_the_next_mro_implementation():
    """单继承中常用 ``super`` 扩展父类行为而不是复制它。"""

    class BaseFormatter:
        def format(self, value):
            return f"<{value}>"

    class LabeledFormatter(BaseFormatter):
        def format(self, value):
            base = super().format(value)
            return f"label:{base}"

    assert LabeledFormatter().format("Python") == "label:<Python>"


def test_c3_mro_orders_a_diamond_and_super_visits_each_class_once():
    """菱形继承通过 C3 顺序协作，公共祖先不会被重复调用。"""

    events = []

    class Root:
        def process(self):
            events.append("Root")

    class Left(Root):
        def process(self):
            events.append("Left")
            super().process()

    class Right(Root):
        def process(self):
            events.append("Right")
            super().process()

    class Leaf(Left, Right):
        def process(self):
            events.append("Leaf")
            super().process()

    Leaf().process()

    assert Leaf.__mro__ == (Leaf, Left, Right, Root, object)
    assert events == ["Leaf", "Left", "Right", "Root"]

    # Left 中的 super() 对 Leaf 实例而言会前进到 Right，而不是“Left 写死的
    # 父类 Root”。super 的动态 MRO 含义让后来组合的 mixin 能插入调用链。


def test_inconsistent_parent_orders_make_c3_mro_creation_fail():
    """无法同时保持各父类局部顺序时，Python 拒绝创建含糊的新类。"""

    class X:
        pass

    class Y:
        pass

    class XBeforeY(X, Y):
        pass

    class YBeforeX(Y, X):
        pass

    with pytest.raises(TypeError, match=r"(?is)resolution\s+order"):
        type("Impossible", (XBeforeY, YBeforeX), {})


def test_cooperative_initializers_consume_keywords_and_forward_the_rest():
    """多继承 initializer 用一致的 ``**kwargs`` 管道让每一层消费自己的参数。"""

    events = []

    class CooperativeRoot:
        def __init__(self, **kwargs):
            if kwargs:
                raise TypeError(f"unconsumed arguments: {sorted(kwargs)}")
            events.append("root")
            super().__init__()

    class Named(CooperativeRoot):
        def __init__(self, *, name, **kwargs):
            self.name = name
            events.append("named")
            super().__init__(**kwargs)

    class Timestamped(CooperativeRoot):
        def __init__(self, *, created_at, **kwargs):
            self.created_at = created_at
            events.append("timestamped")
            super().__init__(**kwargs)

    class Entity(Named, Timestamped):
        pass

    entity = Entity(name="example", created_at="2026-07-14")

    assert (entity.name, entity.created_at) == ("example", "2026-07-14")
    assert Entity.__mro__ == (Entity, Named, Timestamped, CooperativeRoot, object)
    assert events == ["named", "timestamped", "root"]

    # 每层只消费自己拥有的关键字并把其余参数交给 super。链尾显式拒绝未消费
    # 参数，可让拼写错误尽早暴露，而不是被某个 **kwargs 静默吞掉。


def test_hard_coded_parent_call_skips_a_class_in_diamond_mro():
    """直接调用某个基类会绕开 MRO，破坏 mixin 的协作链。"""

    events = []

    class Root:
        def process(self):
            events.append("Root")

    class Left(Root):
        def process(self):
            events.append("Left")
            Root.process(self)

    class Right(Root):
        def process(self):
            events.append("Right")
            super().process()

    class Leaf(Left, Right):
        pass

    Leaf().process()

    assert Leaf.__mro__ == (Leaf, Left, Right, Root, object)
    assert events == ["Left", "Root"]

    # Right 明明位于 MRO，却因 Left 写死 Root.process 而完全跳过。协作式层级
    # 要求链上的每个实现都使用兼容签名并调用 super，不能只改其中一层。


def test_init_subclass_registers_and_configures_new_subclasses():
    """``__init_subclass__`` 在派生类创建后运行，可消费类定义关键字。"""

    class Plugin:
        registry = {}

        def __init_subclass__(cls, *, key, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.key = key
            cls.registry[key] = cls

    class JsonPlugin(Plugin, key="json"):
        pass

    class TextPlugin(Plugin, key="text"):
        pass

    assert Plugin.registry == {"json": JsonPlugin, "text": TextPlugin}
    assert JsonPlugin.key == "json"

    # __init_subclass__ 自动按类方法方式接收 cls。自定义关键字必须由相应层消费，
    # 剩余项再交给 super，才能与其他基类钩子协作。


def test_unconsumed_class_keyword_eventually_reaches_object_and_fails():
    """object 的 subclass hook 不接受额外关键字，可暴露漏消费的配置。"""

    class ForwardsEverything:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

    with pytest.raises(TypeError):
        class BrokenPlugin(ForwardsEverything, unknown_option=True):
            pass


def test_double_underscore_names_are_mangled_per_defining_class():
    """名称改写避免子类意外覆盖，但不是访问控制或安全边界。"""

    class Base:
        __token = "base"

        def token(self):
            return self.__token

    class Child(Base):
        __token = "child"

        def child_token(self):
            return self.__token

    child = Child()

    assert child.token() == "base"
    assert child.child_token() == "child"
    assert Base.__dict__["_Base__token"] == "base"
    assert Child.__dict__["_Child__token"] == "child"
    assert child._Base__token == "base"

    with pytest.raises(AttributeError):
        _ = child.__token

    # 改写规则是可预测的 `_ClassName__name`，外部仍能访问。它主要防止继承层级
    # 中无意的名字碰撞，不提供真正私有性，更不能保护敏感数据。
