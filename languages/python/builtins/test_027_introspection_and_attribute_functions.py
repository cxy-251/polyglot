"""027｜对象身份、类型检查、属性访问与类接口类内置函数示例。

这些内置函数帮助代码检查对象、按运行时名称访问属性，以及声明 property、
classmethod、staticmethod 等类接口。它们不会让动态访问变成“无副作用”：
getattr/hasattr 仍会触发描述符和用户代码，dir 也只是面向交互使用的尽力清单。

身份/相等、描述符、类构造和继承机制已在 002、007、011、013 展示；本文件聚焦
内置函数的实际使用边界。内容基于 Python 3.10 Built-in Functions。

"""

# polyglot-covers: python.builtin.object python.builtin.id python.builtin.type
# polyglot-covers: python.builtin.isinstance python.builtin.issubclass
# polyglot-covers: python.builtin.callable python.builtin.getattr
# polyglot-covers: python.builtin.hasattr python.builtin.setattr python.builtin.delattr
# polyglot-covers: python.builtin.vars python.builtin.dir
# polyglot-covers: python.builtin.property python.builtin.classmethod
# polyglot-covers: python.builtin.staticmethod python.introspection.side-effects

import pytest


def test_plain_object_instances_make_unique_hashable_sentinels():
    """object() 没有业务状态，默认 equality 是 identity，适合作为缺失哨兵。"""

    missing = object()
    another = object()
    mapping = {"present": None}

    assert missing is not another
    assert missing != another
    assert mapping.get("present", missing) is None
    assert mapping.get("absent", missing) is missing
    assert len({missing, another}) == 2

    with pytest.raises(AttributeError):
        missing.label = "cannot attach state"

    # 模块级私有 sentinel 可区分“未传入”和“显式传 None”；不要用可与业务值相等的值。


def test_id_matches_identity_for_simultaneously_live_objects():
    """同一对象的所有别名共享 id，不同存活对象即使相等也有不同 id。"""

    value = [1, 2]
    alias = value
    equal_but_distinct = [1, 2]

    assert alias is value
    assert id(alias) == id(value)
    assert equal_but_distinct == value
    assert equal_but_distinct is not value
    assert id(equal_but_distinct) != id(value)

    # id 只保证对象生命周期内唯一；对象销毁后可复用，且不承诺是永久内存地址、
    # 跨进程标识或可持久化业务 ID。


def test_type_checks_exact_class_while_isinstance_accepts_subclasses():
    """精确类型判断和继承判断回答不同问题。"""

    class UserId(int):
        pass

    user_id = UserId(7)

    assert type(user_id) is UserId
    assert type(user_id) is not int
    assert isinstance(user_id, UserId)
    assert isinstance(user_id, int)
    assert isinstance(True, int)

    # 公共 API 通常希望接收兼容子类或抽象协议，应优先 isinstance；序列化等必须
    # 区分精确运行时类型的边界才使用 type(x) is T。


def test_isinstance_and_issubclass_accept_tuple_or_union_classinfo():
    """多个允许类型可用 tuple，Python 3.10 也支持 ``A | B`` union type。"""

    assert isinstance("text", (str, bytes))
    assert isinstance(b"data", str | bytes)
    assert not isinstance(3.5, int | str)

    assert issubclass(bool, (int, float))
    assert issubclass(bool, int | float)
    assert not issubclass(str, int | float)

    with pytest.raises(TypeError, match="parameterized generic"):
        isinstance([], list[int])

    # `list[int]` 是带参数的类型注解，不是运行时逐元素验证器；这里只能检查 list。


def test_callable_recognizes_functions_classes_and_call_protocol_instances():
    """函数、类和实现 ``__call__`` 的对象都可能被 callable 识别。"""

    def function(value):
        return value * 2

    class Multiplier:
        def __init__(self, factor):
            self.factor = factor

        def __call__(self, value):
            return value * self.factor

    times_three = Multiplier(3)

    assert callable(function)
    assert callable(Multiplier)
    assert callable(times_three)
    assert not callable(42)
    assert function(4) == 8
    assert times_three(4) == 12


def test_callable_does_not_guarantee_a_particular_signature_or_success():
    """callable 只回答是否支持调用语法，不验证参数、返回值或内部异常。"""

    class NeedsArgument:
        def __call__(self, required):
            return required

    operation = NeedsArgument()
    assert callable(operation)

    with pytest.raises(TypeError):
        operation()

    assert operation("provided") == "provided"


def test_getattr_supports_dynamic_names_default_and_normal_attribute_errors():
    """getattr 的 default 只处理属性不存在，不是任意异常 fallback。"""

    class Record:
        kind = "example"

    record = Record()
    record.value = 42

    assert getattr(record, "value") == 42
    assert getattr(record, "kind") == "example"
    assert getattr(record, "missing", "fallback") == "fallback"

    with pytest.raises(AttributeError):
        getattr(record, "missing")


def test_setattr_and_delattr_can_use_names_not_available_in_dot_syntax():
    """字符串属性名可来自配置，甚至不必是 Python identifier。"""

    class Record:
        pass

    record = Record()
    setattr(record, "display-name", "Alice")

    assert getattr(record, "display-name") == "Alice"
    assert vars(record) == {"display-name": "Alice"}

    delattr(record, "display-name")
    assert not hasattr(record, "display-name")

    with pytest.raises(AttributeError):
        delattr(record, "display-name")

    # 点语法不能写 `record.display-name`；动态名仍应在输入边界做白名单/契约校验。


def test_hasattr_executes_property_and_only_converts_attribute_error_to_false():
    """hasattr 内部调用 getattr；property 的求值、副作用和异常都会真实发生。"""

    class Status:
        def __init__(self):
            self.calls = []

        @property
        def ready(self):
            self.calls.append("ready")
            return True

        @property
        def hidden(self):
            self.calls.append("hidden")
            raise AttributeError("reported as absent")

        @property
        def broken(self):
            self.calls.append("broken")
            raise RuntimeError("real failure")

    status = Status()

    assert hasattr(status, "ready") is True
    assert status.calls == ["ready"]
    assert hasattr(status, "hidden") is False
    assert status.calls == ["ready", "hidden"]

    with pytest.raises(RuntimeError, match="real failure"):
        hasattr(status, "broken")

    # property 内部误抛 AttributeError 会被伪装成“不存在”，这是排查动态属性的常见坑。


def test_property_coordinates_validated_get_set_and_delete_access():
    """property 把方法组合成普通属性接口，并可在写入/删除处维护约束。"""

    class Celsius:
        def __init__(self, value):
            self.temperature = value

        @property
        def temperature(self):
            """以摄氏度返回温度。"""
            return self._temperature

        @temperature.setter
        def temperature(self, value):
            if value < -273.15:
                raise ValueError("below absolute zero")
            self._temperature = float(value)

        @temperature.deleter
        def temperature(self):
            self._temperature = None

    reading = Celsius(20)

    assert reading.temperature == 20.0
    reading.temperature = 21.5
    assert reading.temperature == 21.5
    assert Celsius.temperature.__doc__ == "以摄氏度返回温度。"

    with pytest.raises(ValueError, match="absolute zero"):
        reading.temperature = -300

    del reading.temperature
    assert reading.temperature is None


def test_classmethod_alternative_constructor_receives_actual_subclass():
    """classmethod 绑定访问它的类，使替代构造器自然保留派生类型。"""

    class Record:
        def __init__(self, name, count):
            self.name = name
            self.count = count

        @classmethod
        def from_text(cls, text):
            name, count = text.split(":", 1)
            result = cls(name, int(count))
            result.constructed_by = cls.__name__
            return result

    class SpecialRecord(Record):
        pass

    base = Record.from_text("items:3")
    special = SpecialRecord.from_text("items:4")

    assert type(base) is Record
    assert type(special) is SpecialRecord
    assert (special.name, special.count) == ("items", 4)
    assert special.constructed_by == "SpecialRecord"

    # 在 classmethod 内硬编码 Record(...) 会破坏这个协作式子类行为，应调用 cls(...)。


def test_staticmethod_keeps_a_namespace_function_free_of_implicit_arguments():
    """staticmethod 从类和实例访问都不会注入 self/cls。"""

    class Slug:
        @staticmethod
        def normalize(value):
            return "-".join(value.casefold().split())

    assert Slug.normalize("Hello World") == "hello-world"
    assert Slug().normalize("Two Words") == "two-words"
    assert callable(Slug.normalize)

    # 函数若不依赖类/实例状态但属于该概念的公共命名空间，staticmethod 可以表达归属。


def test_vars_of_instance_returns_its_live_attribute_dictionary():
    """普通实例的 vars(obj) 返回实际 __dict__，修改它会改变实例属性。"""

    class Record:
        category = "example"

    record = Record()
    record.value = 1

    attributes = vars(record)

    assert attributes is record.__dict__
    assert attributes == {"value": 1}
    attributes["value"] = 2
    attributes["new"] = 3

    assert record.value == 2
    assert record.new == 3

    # 继承的 category 在类上，不在实例 __dict__ 中，所以 vars(record) 不会列出它。


def test_vars_without_argument_reads_current_local_namespace():
    """无参数 vars 等价于当前作用域的 locals 读取。"""

    marker = "visible"
    namespace = vars()

    assert namespace["marker"] == "visible"

    # 函数局部作用域中不应修改该 mapping 并期待真实局部变量随之可靠变化。


def test_vars_requires_dunder_dict_and_class_namespace_is_read_only_proxy():
    """slots-only 实例没有 __dict__；类的 vars 返回只读 mappingproxy。"""

    class Slotted:
        __slots__ = ("value",)

    class Regular:
        category = "example"

    with pytest.raises(TypeError):
        vars(Slotted())

    class_namespace = vars(Regular)
    assert class_namespace["category"] == "example"

    with pytest.raises(TypeError):
        class_namespace["category"] = "changed"


def test_dir_is_sorted_and_customizable_for_interactive_discovery():
    """dir 会排序名称；对象可用 __dir__ 提供面向使用者的发现清单。"""

    class DynamicAPI:
        def __dir__(self):
            return ["zeta", "alpha", "virtual"]

        def __getattr__(self, name):
            if name == "virtual":
                return 42
            raise AttributeError(name)

    api = DynamicAPI()

    assert dir(api) == ["alpha", "virtual", "zeta"]
    assert api.virtual == 42
    assert not hasattr(api, "alpha")

    # dir 追求交互便利，不保证列出所有动态属性，也不保证每个列出名称都可成功读取。


def test_default_dir_combines_instance_class_and_base_attributes():
    """未定制时，dir 汇总多层命名空间并返回排序后的名称列表。"""

    class Base:
        inherited = 1

    class Child(Base):
        class_value = 2

    child = Child()
    child.instance_value = 3

    names = dir(child)

    assert names == sorted(names)
    assert {"inherited", "class_value", "instance_value"} <= set(names)

    # 机器可审计接口应读取明确 schema、协议或 inspect 结果，而不是把 dir 当权威 API 清单。
