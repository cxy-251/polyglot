"""007｜属性访问、属性钩子与描述符优先级的可执行示例。

``obj.name`` 不只是从字典中取值：读取先经过 ``__getattribute__``，正常查找
失败后才可能进入 ``__getattr__``；类属性若实现 descriptor 协议，还会按
data descriptor、实例字典、non-data descriptor、普通类属性的顺序参与查找。
赋值和删除则可由 descriptor 或对象的属性钩子接管。函数、property、slots
也都建立在这些规则之上。

内容基于 Python 3.10 Attribute references、Customizing attribute access、
Implementing Descriptors 和 Descriptor Guide。当前项目处于只编写、暂不执行
的阶段，本文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.expression.attribute-reference
# polyglot-covers: python.builtin.getattr python.builtin.setattr
# polyglot-covers: python.builtin.delattr python.builtin.hasattr
# polyglot-covers: python.builtin.property
# polyglot-covers: python.protocol.__getattribute__ python.protocol.__getattr__
# polyglot-covers: python.protocol.__setattr__ python.protocol.__delattr__
# polyglot-covers: python.protocol.__get__ python.protocol.__set__
# polyglot-covers: python.protocol.__delete__ python.protocol.__set_name__
# polyglot-covers: python.protocol.bound-method python.class.__slots__

import pytest


def test_instance_attribute_shadows_plain_class_attribute_until_deleted():
    """普通类属性提供共享 fallback，实例可用同名属性遮蔽它。"""

    class Settings:
        mode = "class-default"

    first = Settings()
    second = Settings()

    first.mode = "instance-choice"

    assert first.mode == "instance-choice"
    assert second.mode == "class-default"
    assert Settings.mode == "class-default"

    del first.mode
    assert first.mode == "class-default"

    # 删除实例字典中的同名项不会删除类属性；下一次读取只是重新沿 MRO 回退。


def test_attribute_builtin_functions_support_dynamic_names_and_defaults():
    """内置属性函数适合名称在运行时才确定的读取、写入和删除。"""

    class Record:
        pass

    record = Record()
    setattr(record, "language", "Python")
    setattr(record, "display-name", "Python 3.10")

    assert getattr(record, "language") == "Python"
    assert getattr(record, "display-name") == "Python 3.10"
    assert getattr(record, "missing", "fallback") == "fallback"
    assert hasattr(record, "language")

    delattr(record, "language")
    assert not hasattr(record, "language")

    with pytest.raises(AttributeError):
        getattr(record, "missing")

    # setattr 甚至能保存不是合法点号标识符的字符串；这种属性只能再用 getattr
    # 等动态入口访问，正常业务仍应优先选择可读的标识符名称。


class DynamicSettings:
    def __init__(self):
        self.existing = "configured"
        self.fallback_calls = []

    def __getattr__(self, name):
        self.fallback_calls.append(name)
        if name.startswith("feature_"):
            return False
        raise AttributeError(name)


def test_getattr_hook_runs_only_after_normal_lookup_fails():
    """``__getattr__`` 是缺失属性 fallback，不会拦截已有属性。"""

    settings = DynamicSettings()

    assert settings.existing == "configured"
    assert settings.fallback_calls == []
    assert settings.feature_preview is False
    assert settings.fallback_calls == ["feature_preview"]

    with pytest.raises(AttributeError):
        settings.unknown

    assert settings.fallback_calls == ["feature_preview", "unknown"]


class AuditedObject:
    def __init__(self):
        self.value = 42
        self.events = []

    def __getattribute__(self, name):
        # 这里必须绕过当前 override。写 self.events 或 self.__dict__ 都会再次
        # 进入 __getattribute__，最终无限递归。
        if name != "events":
            events = object.__getattribute__(self, "events")
            events.append(name)
        return object.__getattribute__(self, name)


def test_getattribute_hook_sees_every_normal_attribute_read():
    """``__getattribute__`` 总是先执行，再委托基础实现完成正常查找。"""

    audited = AuditedObject()

    assert audited.value == 42
    assert object.__getattribute__(audited, "events") == ["value"]

    with pytest.raises(AttributeError):
        audited.missing

    assert object.__getattribute__(audited, "events") == ["value", "missing"]


class NormalizingRecord:
    def __init__(self):
        object.__setattr__(self, "events", [])

    def __setattr__(self, name, value):
        events = object.__getattribute__(self, "events")
        events.append(("set", name, value))
        if name == "language":
            value = value.strip()
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        events = object.__getattribute__(self, "events")
        events.append(("delete", name))
        object.__delattr__(self, name)


def test_setattr_and_delattr_hooks_can_validate_then_delegate():
    """属性写入和删除钩子应显式调用基础实现完成实际操作。"""

    record = NormalizingRecord()
    record.language = "  Python  "

    assert record.language == "Python"

    del record.language
    assert not hasattr(record, "language")
    assert record.events == [
        ("set", "language", "  Python  "),
        ("delete", "language"),
    ]

    # 在 __setattr__ 内再次写 self.language 会重新调用自身。object.__setattr__
    # 才是结束递归并遵守底层 descriptor 规则的委托入口。


class ValidatedField:
    """通过 descriptor 为多个属性复用命名、校验与删除逻辑。"""

    def __init__(self, expected_type):
        self.expected_type = expected_type
        self.public_name = None
        self.private_name = None

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = f"_{name}"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f"{self.public_name} must be {self.expected_type.__name__}")
        setattr(instance, self.private_name, value)

    def __delete__(self, instance):
        delattr(instance, self.private_name)


class Course:
    title = ValidatedField(str)
    lessons = ValidatedField(int)

    def __init__(self, title, lessons):
        self.title = title
        self.lessons = lessons


def test_descriptor_get_set_delete_and_set_name_form_a_reusable_field():
    """descriptor 的四个入口共同实现可复用的托管属性。"""

    course = Course("Python protocols", 12)

    assert Course.title.public_name == "title"
    assert Course.title.private_name == "_title"
    assert course.title == "Python protocols"
    assert course.lessons == 12
    assert course.__dict__ == {"_title": "Python protocols", "_lessons": 12}

    course.lessons = 14
    assert course.lessons == 14

    with pytest.raises(TypeError):
        course.lessons = "many"

    del course.title
    with pytest.raises(AttributeError):
        _ = course.title

    # 类访问 Course.title 时 __get__ 收到 instance=None，因此返回 descriptor
    # 自身；实例访问则读取由 __set_name__ 计算出的私有存储名。


def test_set_name_runs_at_class_creation_but_not_on_late_assignment():
    """类体中的 descriptor 自动获知名称，稍后挂载则要手动通知。"""

    class NameRecorder:
        def __init__(self):
            self.names = []

        def __set_name__(self, owner, name):
            self.names.append((owner.__name__, name))

    declared = NameRecorder()

    class Owner:
        field = declared

    assert declared.names == [("Owner", "field")]

    late = NameRecorder()
    Owner.late = late
    assert late.names == []

    late.__set_name__(Owner, "late")
    assert late.names == [("Owner", "late")]


class DataDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return "data-descriptor"

    def __set__(self, instance, value):
        raise AttributeError("read only")


class NonDataDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return "non-data-descriptor"


def test_data_descriptor_has_priority_over_instance_dictionary():
    """只要类型定义 ``__set__`` 或 ``__delete__``，descriptor 就属于 data。"""

    class Owner:
        value = DataDescriptor()

    owner = Owner()
    owner.__dict__["value"] = "instance-value"

    assert owner.value == "data-descriptor"

    with pytest.raises(AttributeError):
        owner.value = "new value"

    assert owner.__dict__["value"] == "instance-value"

    # 即使 __set__ 只会拒绝写入，它仍让 descriptor 获得 data descriptor 的
    # 最高优先级。直接塞进 __dict__ 的同名值存在，但读取时不会胜出。


def test_instance_dictionary_has_priority_over_non_data_descriptor():
    """只有 ``__get__`` 的 non-data descriptor 可以被实例属性遮蔽。"""

    class Owner:
        value = NonDataDescriptor()

    owner = Owner()

    assert owner.value == "non-data-descriptor"

    owner.value = "instance-value"
    assert owner.value == "instance-value"

    del owner.value
    assert owner.value == "non-data-descriptor"


def test_functions_are_non_data_descriptors_that_create_bound_methods():
    """从实例读取类函数时，函数 descriptor 自动绑定 ``self``。"""

    class Greeter:
        def greet(self, name):
            return f"Hello, {name}"

    greeter = Greeter()
    bound = greeter.greet

    assert bound.__self__ is greeter
    assert bound.__func__ is Greeter.greet
    assert bound("Python") == "Hello, Python"
    assert Greeter.greet(greeter, "descriptors") == "Hello, descriptors"

    greeter.greet = lambda name: f"Overridden, {name}"
    assert greeter.greet("Python") == "Overridden, Python"

    # 普通函数只实现 __get__，属于 non-data descriptor，所以最后一行的实例
    # 属性能遮蔽方法。property 等 data descriptor 的行为不同。


class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._celsius = value

    @celsius.deleter
    def celsius(self):
        del self._celsius


def test_property_packages_getter_setter_and_deleter_as_a_data_descriptor():
    """``property`` 用普通方法定义托管属性，并保持点号调用界面。"""

    temperature = Temperature(20)

    assert temperature.celsius == 20

    temperature.celsius = 25
    assert temperature.celsius == 25

    with pytest.raises(ValueError):
        temperature.celsius = -300

    # property 是 data descriptor，直接写同名实例字典也无法遮蔽它。
    temperature.__dict__["celsius"] = "shadow attempt"
    assert temperature.celsius == 25

    del temperature.celsius
    with pytest.raises(AttributeError):
        _ = temperature.celsius


def test_hasattr_swallows_attribute_error_raised_inside_a_property():
    """``hasattr`` 无法区分“确实缺失”和 getter 内部的 ``AttributeError``。"""

    class BrokenReport:
        @property
        def summary(self):
            raise AttributeError("report storage was not initialized")

    report = BrokenReport()

    assert hasattr(report, "summary") is False

    with pytest.raises(AttributeError, match="storage was not initialized"):
        _ = report.summary

    # 常见坑：hasattr 本质上尝试 getattr 并捕获 AttributeError。property 内部
    # 若因真实 bug 抛同一种异常，hasattr 也会误报属性不存在并掩盖根因。


def test_slots_remove_the_automatic_instance_dictionary_when_fully_slotted():
    """``__slots__`` 为声明字段创建 descriptor，并可省去每实例 ``__dict__``。"""

    class Point:
        __slots__ = ("x", "y")

        def __init__(self, x, y):
            self.x = x
            self.y = y

    point = Point(2, 3)

    assert (point.x, point.y) == (2, 3)
    assert not hasattr(point, "__dict__")

    with pytest.raises(AttributeError):
        point.label = "origin"


def test_unslotted_subclass_restores_an_instance_dictionary():
    """父类有 slots 不代表未声明 slots 的子类也禁止动态属性。"""

    class SlottedBase:
        __slots__ = ("identifier",)

    class FlexibleChild(SlottedBase):
        pass

    child = FlexibleChild()
    child.identifier = 1
    child.note = "stored in child __dict__"

    assert child.identifier == 1
    assert child.note == "stored in child __dict__"
    assert child.__dict__ == {"note": "stored in child __dict__"}

    # 若整个继承链都要保持无 __dict__ 布局，子类也必须显式声明 __slots__，
    # 常用空 tuple 表示该层不新增 slot。
