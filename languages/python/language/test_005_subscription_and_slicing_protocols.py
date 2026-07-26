"""005｜订阅、切片和容器写入协议的可执行示例。

``obj[key]`` 看起来是一种语法，实际既可以表达序列位置、映射键，也可以表达
传给数值容器的多维 key。带冒号的切片不会先变成一组元素，而是先构造
``slice`` 对象交给容器解释。赋值与删除则分别进入 ``__setitem__`` 和
``__delitem__``。类本身被订阅时，分派入口又会切换到元类 ``__getitem__``
或 ``__class_getitem__``。

内容基于 Python 3.10 Expressions 6.3.2--6.3.3、Data Model 3.3.6 和
Built-in Types 的映射协议。
"""

# polyglot-covers: python.expression.subscription python.expression.slicing
# polyglot-covers: python.builtin.slice python.type.sequence-subscription
# polyglot-covers: python.type.mapping-subscription
# polyglot-covers: python.protocol.__getitem__ python.protocol.__setitem__
# polyglot-covers: python.protocol.__delitem__ python.protocol.__missing__
# polyglot-covers: python.protocol.__class_getitem__
# polyglot-covers: python.protocol.metaclass.__getitem__

# 跨语言迁移提示：Python 把索引或 slice 对象交给容器协议，并由序列决定是否解释负索引；
# JavaScript 数组索引仍是属性键，空洞也不同于值为 undefined，不能照搬 Python 序列模型。

import operator

import pytest


def test_builtin_sequences_support_indices_and_slices():
    """索引返回一个元素，切片返回同类序列中的一个范围。"""

    letters = ["a", "b", "c", "d", "e"]

    assert letters[0] == "a"
    assert letters[-1] == "e"
    assert letters[1:4] == ["b", "c", "d"]
    assert letters[::2] == ["a", "c", "e"]
    assert letters[::-1] == ["e", "d", "c", "b", "a"]

    # 切片的 stop 不包含在结果中；负 step 则让默认起止方向反转。它们都遵循
    # range 风格的半开区间，而不是把 stop 所指元素也包含进来。


class KeyRecorder:
    def __init__(self):
        self.keys = []

    def __getitem__(self, key):
        self.keys.append(key)
        return key


def test_subscription_passes_the_key_object_to_getitem():
    """解释器负责形成 key，但 key 的具体含义由 ``__getitem__`` 决定。"""

    recorder = KeyRecorder()
    marker = object()

    assert recorder["language"] == "language"
    assert recorder[marker] is marker
    assert recorder[-1] == -1
    assert recorder.keys == ["language", marker, -1]

    # 常见坑：解释器不会在调用自定义 __getitem__ 前把 -1 自动换成
    # len(self) - 1。内置序列支持负索引，是序列实现自身提供的语义。


def test_slicing_builds_slice_objects_without_filling_missing_bounds():
    """冒号语法把原始 start、stop、step 封装为 ``slice``。"""

    recorder = KeyRecorder()

    assert recorder[1:8:2] == slice(1, 8, 2)
    assert recorder[:5] == slice(None, 5, None)
    assert recorder[3:] == slice(3, None, None)
    assert recorder[::-1] == slice(None, None, -1)

    # 此时 None 仍然是 None，因为解释器不知道容器长度。容器若想获得适用于
    # 自己长度的有效边界，应调用 key.indices(len(self))，不能把 None 直接
    # 传入 range。


def test_slice_indices_normalizes_bounds_for_a_specific_length():
    """``slice.indices`` 根据实际长度补齐、截断边界并处理负步长。"""

    forward = slice(-20, 20, 2)
    backward = slice(None, None, -1)

    assert forward.indices(5) == (0, 5, 2)
    assert list(range(*forward.indices(5))) == [0, 2, 4]
    assert backward.indices(5) == (4, -1, -1)
    assert list(range(*backward.indices(5))) == [4, 3, 2, 1, 0]

    with pytest.raises(ValueError):
        slice(None, None, 0).indices(5)

    # 步长为零没有可执行含义，所以不论使用内置切片还是手动调用 indices，
    # 都应把它视为错误，而不是悄悄返回空结果。


class LearningSequence:
    """实现整数索引和切片的最小只读序列。"""

    def __init__(self, items):
        self._items = list(items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            return [self._items[index] for index in range(start, stop, step)]

        # operator.index 接受 int 及实现 __index__ 的无损整数类型；使用 int(key)
        # 会错误接受只有近似转换语义的对象。
        index = operator.index(key)
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError("LearningSequence index out of range")
        return self._items[index]


def test_custom_sequence_explicitly_implements_index_and_slice_rules():
    """自定义序列负责负索引规范化、切片解释和越界异常。"""

    sequence = LearningSequence(["syntax", "protocol", "stdlib", "testing"])

    assert sequence[1] == "protocol"
    assert sequence[-1] == "testing"
    assert sequence[1::2] == ["protocol", "testing"]
    assert sequence[::-1] == ["testing", "stdlib", "protocol", "syntax"]

    with pytest.raises(IndexError):
        sequence[10]

    with pytest.raises(TypeError):
        sequence["first"]

    # 序列越界应抛 IndexError，键类型不合适应抛 TypeError。除了向调用者准确
    # 表达原因，旧式 __getitem__ 迭代 fallback 也依赖 IndexError 判断结束。


def test_comma_separated_subscription_items_become_a_tuple_key():
    """多维订阅只调用一次 ``__getitem__``，并把各维组合成 tuple。"""

    recorder = KeyRecorder()

    assert recorder[1, 2] == (1, 2)
    assert recorder[1:4, ..., None] == (slice(1, 4, None), Ellipsis, None)

    # Python 核心并不解释“行”和“列”。tuple、slice、Ellipsis 和 None 只是
    # 原样组成 key，具体维度语义由接收对象（例如数组类型）自行定义。


class MutableRecord:
    def __init__(self):
        self.data = {}
        self.events = []

    def __getitem__(self, key):
        self.events.append(("get", key))
        return self.data[key]

    def __setitem__(self, key, value):
        self.events.append(("set", key, value))
        self.data[key] = value

    def __delitem__(self, key):
        self.events.append(("delete", key))
        del self.data[key]


def test_item_read_write_and_delete_use_three_distinct_methods():
    """同一种方括号语法会根据上下文选择读取、写入或删除协议。"""

    record = MutableRecord()

    record["language"] = "Python"
    assert record["language"] == "Python"
    del record["language"]

    assert record.data == {}
    assert record.events == [
        ("set", "language", "Python"),
        ("get", "language"),
        ("delete", "language"),
    ]


def test_immutable_containers_reject_item_assignment_and_deletion():
    """支持读取不代表类型也支持 ``__setitem__`` 或 ``__delitem__``。"""

    coordinates = (10, 20)

    assert coordinates[0] == 10

    with pytest.raises(TypeError):
        coordinates[0] = 99

    with pytest.raises(TypeError):
        del coordinates[0]

    # tuple 有 __getitem__，却没有可用的 item 写入和删除协议。容器“是否可变”
    # 不能从它是否支持方括号读取推断出来。


def test_list_slice_assignment_can_resize_a_contiguous_range():
    """步长为 1 的 list 切片赋值允许替换序列与原区间长度不同。"""

    values = [0, 1, 2, 3, 4]
    values[1:4] = [10, 20]

    assert values == [0, 10, 20, 4]

    del values[1:3]
    assert values == [0, 4]


def test_extended_list_slice_assignment_requires_matching_lengths():
    """步长不为 1 时，各离散位置必须与右侧元素一一对应。"""

    values = [0, 1, 2, 3, 4, 5]
    values[::2] = [10, 20, 30]

    assert values == [10, 1, 20, 3, 30, 5]

    with pytest.raises(ValueError):
        values[::2] = [100, 200]

    assert values == [10, 1, 20, 3, 30, 5]

    # 常见坑：普通切片赋值能够伸缩 list，不代表扩展切片也能。后者描述的是
    # 已经分散确定的目标位置，右侧长度不同就无法完成逐个赋值。


class MissingAwareDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.missing_calls = []

    def __missing__(self, key):
        self.missing_calls.append(key)
        return f"<{key}:missing>"


def test_dict_getitem_alone_invokes_missing_on_a_dict_subclass():
    """``__missing__`` 是 ``dict.__getitem__`` 的专用缺键钩子。"""

    values = MissingAwareDict(existing=1)

    assert values["unknown"] == "<unknown:missing>"
    assert values.missing_calls == ["unknown"]
    assert "unknown" not in values

    # __missing__ 的返回值不会被 dict 自动写回；是否缓存默认值由实现决定。
    # get、成员测试和迭代也不走这个钩子。
    assert values.get("another") is None
    assert "another" not in values
    assert list(values) == ["existing"]
    assert values.missing_calls == ["unknown"]


def test_plain_mapping_lookup_raises_key_error_for_an_absent_key():
    """映射按键查找，缺键使用 ``KeyError``，不同于序列越界的 ``IndexError``。"""

    settings = {"theme": "dark"}

    with pytest.raises(KeyError) as error:
        settings["locale"]

    assert error.value.args == ("locale",)


class GenericRepository:
    def __class_getitem__(cls, item):
        return "class-getitem", cls.__name__, item


def test_class_subscription_uses_class_getitem_when_metaclass_has_no_getitem():
    """``Class[item]`` 可由 ``__class_getitem__`` 构造类型参数化结果。"""

    assert GenericRepository[str] == ("class-getitem", "GenericRepository", str)

    # __class_getitem__ 主要服务泛型类型提示；它处理的是类本身的订阅，不会
    # 改变 GenericRepository 实例的 item 读取能力。
    with pytest.raises(TypeError):
        GenericRepository()["key"]


class SubscriptionMeta(type):
    def __getitem__(cls, item):
        return "metaclass-getitem", cls.__name__, item


class MetaControlledRepository(metaclass=SubscriptionMeta):
    def __class_getitem__(cls, item):
        return "class-getitem", cls.__name__, item


def test_metaclass_getitem_takes_priority_for_class_subscription():
    """元类定义 ``__getitem__`` 时，类订阅先按普通实例订阅处理。"""

    assert MetaControlledRepository[int] == (
        "metaclass-getitem",
        "MetaControlledRepository",
        int,
    )

    # 类是元类的实例，所以查找顺序先检查 type(class) 的 __getitem__；只有
    # 元类没有该入口时，解释器才考虑类上的 __class_getitem__。
