"""014｜对象表示、格式化、字节转换与哈希协议的可执行示例。

``repr`` 面向无歧义诊断，``str`` 面向可读显示；``format`` 和 f-string 把
format spec 交给 ``__format__``，但 ``!s`` / ``!r`` / ``!a`` 会先把对象
转换成字符串，再格式化那个字符串。``hash`` 则服务 dict/set：相等对象必须
给出相同且在生命周期内稳定的 hash，否则查找结构会出现违反直觉的结果。

内容基于 Python 3.10 Basic customization、Formatted string literals 和内置
repr/str/ascii/format/bytes/hash。当前项目处于只编写、暂不执行的阶段，本文件
尚未经过 pytest 验证。
"""

# polyglot-covers: python.builtin.repr python.builtin.str python.builtin.ascii
# polyglot-covers: python.builtin.format python.builtin.bytes python.builtin.hash
# polyglot-covers: python.protocol.__repr__ python.protocol.__str__
# polyglot-covers: python.protocol.__format__ python.protocol.__bytes__
# polyglot-covers: python.protocol.__hash__ python.protocol.__eq__
# polyglot-covers: python.syntax.f-string python.syntax.f-string-conversion
# polyglot-covers: python.syntax.f-string-debug

import pytest


class ReprOnlyRecord:
    def __init__(self, identifier):
        self.identifier = identifier

    def __repr__(self):
        return f"ReprOnlyRecord(identifier={self.identifier!r})"


def test_str_falls_back_to_repr_when_type_has_no_custom_str():
    """只实现 ``__repr__`` 时，``object.__str__`` 使用同一诊断表示。"""

    record = ReprOnlyRecord("python")

    assert repr(record) == "ReprOnlyRecord(identifier='python')"
    assert str(record) == "ReprOnlyRecord(identifier='python')"

    # repr 通常应包含类型和区分对象所需的信息，但“能被 eval 重建”只是建议，
    # 不是强制契约。表示字符串也不应泄漏密码、token 等敏感字段。


class DisplayRecord:
    def __init__(self, identifier, title):
        self.identifier = identifier
        self.title = title

    def __repr__(self):
        return f"DisplayRecord(identifier={self.identifier!r}, title={self.title!r})"

    def __str__(self):
        return self.title


def test_repr_and_str_can_serve_diagnostic_and_user_facing_views():
    """同一对象可提供详细开发者表示和简洁用户显示。"""

    record = DisplayRecord(7, "Python data model")

    assert repr(record) == "DisplayRecord(identifier=7, title='Python data model')"
    assert str(record) == "Python data model"
    assert str([record]) == "[DisplayRecord(identifier=7, title='Python data model')]"

    # list/dict 等容器显示元素时使用 repr，避免多个用户字符串混在一起失去
    # 边界和类型信息。因此只实现 __str__ 不能改善容器里的对象表示。


def test_class_with_only_str_keeps_default_repr_inside_containers():
    """只定义 ``__str__`` 不会让 ``repr`` 自动采用相同结果。"""

    class StrOnly:
        def __str__(self):
            return "readable text"

    value = StrOnly()

    assert str(value) == "readable text"
    assert "StrOnly" in repr(value)
    assert "readable text" not in repr(value)
    assert str([value]) == f"[{repr(value)}]"


def test_ascii_escapes_non_ascii_characters_from_repr():
    """``ascii`` 先取得 repr，再把其中非 ASCII 字符转成转义序列。"""

    class Snow:
        def __repr__(self):
            return "Snow(雪)"

    snow = Snow()

    assert repr(snow) == "Snow(雪)"
    assert ascii(snow) == "Snow(\\u96ea)"


class Temperature:
    def __init__(self, celsius):
        self.celsius = celsius

    def __format__(self, format_spec):
        if format_spec == "":
            return f"{self.celsius} °C"
        if format_spec == "short":
            return f"{self.celsius}C"
        if format_spec.endswith("f"):
            return f"{format(self.celsius, format_spec)} °C"
        raise ValueError(f"unsupported temperature format: {format_spec}")


def test_format_and_f_string_delegate_the_raw_spec_to_format_method():
    """类型自行定义 format spec 的含义，也必须处理常见的空 spec。"""

    temperature = Temperature(23.456)

    assert format(temperature) == "23.456 °C"
    assert format(temperature, "short") == "23.456C"
    assert format(temperature, ".1f") == "23.5 °C"
    assert f"room={temperature:.2f}" == "room=23.46 °C"

    with pytest.raises(ValueError, match="unsupported temperature format"):
        format(temperature, "unknown")

    # 未知 spec 应明确失败，避免格式拼写错误悄悄输出错误数据。format(value)
    # 等价于 format(value, "")，自定义实现不能遗漏空字符串路径。


class ConversionProbe:
    def __init__(self):
        self.events = []

    def __str__(self):
        self.events.append("__str__")
        return "S"

    def __repr__(self):
        self.events.append("__repr__")
        return "R"

    def __format__(self, format_spec):
        self.events.append(("__format__", format_spec))
        return f"F({format_spec})"


def test_f_string_conversions_run_before_string_formatting():
    """无 conversion 时格式化原对象；``!s`` / ``!r`` 则先得到 str。"""

    direct = ConversionProbe()
    as_string = ConversionProbe()
    as_repr = ConversionProbe()

    assert f"{direct:custom}" == "F(custom)"
    assert direct.events == [("__format__", "custom")]

    assert f"{as_string!s:>3}" == "  S"
    assert as_string.events == ["__str__"]

    assert f"{as_repr!r:>3}" == "  R"
    assert as_repr.events == ["__repr__"]

    # conversion 后的 `>3` 由结果字符串处理，原对象的 __format__ 不再参与。
    # !a 同理，只是先调用 ascii(value)。


def test_f_string_ascii_conversion_uses_ascii_repr():
    """``!a`` 适合要求日志只含 ASCII 的场景。"""

    class Label:
        def __repr__(self):
            return "标签"

    assert f"{Label()!a}" == "\\u6807\\u7b7e"


def test_f_string_debug_syntax_keeps_expression_text_and_uses_repr_by_default():
    """``value=`` 同时输出表达式文本和值，便于临时诊断。"""

    answer = 42
    label = "Python"

    assert f"{answer=}" == "answer=42"
    assert f"{label=}" == "label='Python'"
    assert f"{answer=:04d}" == "answer=0042"


class Packet:
    def __init__(self, payload):
        self.payload = payload

    def __bytes__(self):
        return b"PKT:" + self.payload


def test_bytes_delegates_to_bytes_method_for_custom_binary_representation():
    """``__bytes__`` 提供对象的标准 bytes 表示，与人类可读 str 分开。"""

    packet = Packet(b"data")

    assert bytes(packet) == b"PKT:data"


def test_representation_protocols_enforce_strict_return_types():
    """表示方法必须直接返回契约类型，不会再做一次自动转换。"""

    class BadRepr:
        def __repr__(self):
            return 123

    class BadStr:
        def __str__(self):
            return b"text"

    class BadFormat:
        def __format__(self, format_spec):
            return 1.5

    class BadBytes:
        def __bytes__(self):
            return "not bytes"

    with pytest.raises(TypeError):
        repr(BadRepr())

    with pytest.raises(TypeError):
        str(BadStr())

    with pytest.raises(TypeError):
        format(BadFormat())

    with pytest.raises(TypeError):
        bytes(BadBytes())


class HashProbe:
    def __init__(self):
        self.calls = 0

    def __hash__(self):
        self.calls += 1
        return 12345


def test_hash_delegates_to_hash_method_and_requires_an_integer():
    """``hash`` 调用类型的 ``__hash__``，协议结果必须是整数。"""

    value = HashProbe()

    assert hash(value) == 12345
    assert value.calls == 1

    class BadHash:
        def __hash__(self):
            return "12345"

    with pytest.raises(TypeError):
        hash(BadHash())


def test_defining_eq_without_hash_makes_instances_unhashable():
    """值相等类型若未提供一致 hash，Python 自动设置 ``__hash__ = None``。"""

    class UnhashableCoordinate:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def __eq__(self, other):
            if not isinstance(other, UnhashableCoordinate):
                return NotImplemented
            return (self.x, self.y) == (other.x, other.y)

    coordinate = UnhashableCoordinate(1, 2)

    assert UnhashableCoordinate.__hash__ is None

    with pytest.raises(TypeError, match="unhashable type"):
        hash(coordinate)

    with pytest.raises(TypeError):
        {coordinate}


class Coordinate:
    """核心字段只读，并以同一字段组合实现 eq/hash。"""

    __slots__ = ("x", "y")

    def __init__(self, x, y):
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)

    def __setattr__(self, name, value):
        raise AttributeError("Coordinate is immutable")

    def __eq__(self, other):
        if not isinstance(other, Coordinate):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        return hash((self.x, self.y))


def test_equal_immutable_value_objects_share_hash_and_work_as_mapping_keys():
    """eq/hash 基于同一不可变状态，等价值可互换查找。"""

    first = Coordinate(3, 4)
    equal = Coordinate(3, 4)
    different = Coordinate(4, 3)

    assert first == equal
    assert first != different
    assert hash(first) == hash(equal)

    locations = {first: "origin-offset"}
    assert locations[equal] == "origin-offset"

    with pytest.raises(AttributeError):
        first.x = 99


def test_inconsistent_equal_objects_can_both_appear_in_a_set():
    """Python 信任用户实现；违反“相等则同 hash”会直接破坏集合语义。"""

    class InconsistentValue:
        def __init__(self, value, forced_hash):
            self.value = value
            self.forced_hash = forced_hash

        def __eq__(self, other):
            if not isinstance(other, InconsistentValue):
                return NotImplemented
            return self.value == other.value

        def __hash__(self):
            return self.forced_hash

    first = InconsistentValue("same", 1)
    second = InconsistentValue("same", 2)

    assert first == second
    assert hash(first) != hash(second)
    assert len({first, second}) == 2

    # set 先按 hash 缩小候选，再比较相等性；不同 hash 的两个对象不会进入同一
    # 等价检查路径。解释器不会替用户修复这个不变量。


def test_mutating_a_hashed_field_makes_existing_dict_entry_unfindable():
    """键入表后的 hash 必须稳定，否则同一对象也可能找不到原条目。"""

    class MutableKey:
        def __init__(self, number):
            self.number = number

        def __eq__(self, other):
            if not isinstance(other, MutableKey):
                return NotImplemented
            return self.number == other.number

        def __hash__(self):
            return hash(self.number)

    key = MutableKey(1)
    mapping = {key: "stored"}

    assert mapping[key] == "stored"

    key.number = 2

    assert next(iter(mapping)) is key
    assert key not in mapping

    with pytest.raises(KeyError):
        mapping[key]

    # dict 内仍保存同一对象，但条目记录的是插入时 hash(1)；现在查找从 hash(2)
    # 的探测路径开始。参与 hash 的字段应在键的整个在表生命周期内不可变。
