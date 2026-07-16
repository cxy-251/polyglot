"""016｜Python 3.10 ``match`` / ``case`` 结构化模式匹配示例。

match 只求值一次 subject，再从上到下尝试 case，首个 pattern 与 guard 都成功
的分支执行后结束，不会 fall through。pattern 不是普通布尔条件：裸名称会捕获
任意值，dotted name 才是常量 value pattern；sequence、mapping 和 class
pattern 还会按各自协议拆解结构。

内容基于 Python 3.10 Match statement、Patterns、PEP 634 与 PEP 636。
"""

# polyglot-covers: python.statement.match python.pattern.literal
# polyglot-covers: python.pattern.singleton python.pattern.capture
# polyglot-covers: python.pattern.wildcard python.pattern.value
# polyglot-covers: python.pattern.or python.pattern.as python.pattern.guard
# polyglot-covers: python.pattern.sequence python.pattern.star
# polyglot-covers: python.pattern.mapping python.pattern.double-star
# polyglot-covers: python.pattern.class python.protocol.__match_args__

import pytest


def test_match_subject_is_evaluated_once_and_first_case_does_not_fall_through():
    """subject 只求值一次，选中分支后整个 match 结束。"""

    events = []

    def subject():
        events.append("subject")
        return "ready"

    match subject():
        case "ready":
            events.append("first-ready")
        case "ready":
            events.append("second-ready")
        case _:
            events.append("fallback")

    assert events == ["subject", "first-ready"]


def test_literal_pattern_uses_equality_while_singleton_pattern_uses_identity():
    """数字/字符串 literal 按相等性匹配，None/True/False 按身份匹配。"""

    class EqualToOneAndNone:
        def __eq__(self, other):
            return other in (1, None)

    value = EqualToOneAndNone()

    match value:
        case 1:
            numeric_result = "equal-to-one"
        case _:
            numeric_result = "no numeric match"

    match value:
        case None:
            singleton_result = "is-none"
        case _:
            singleton_result = "not-none"

    assert numeric_result == "equal-to-one"
    assert singleton_result == "not-none"

    # value == None 虽然为真，case None 仍不会命中，因为 singleton pattern
    # 使用 is。普通代码同样应优先写 value is None。


def test_numeric_literal_can_match_bool_before_true_singleton_case():
    """``bool`` 是 ``int`` 子类，因此 True 可先被数值 literal ``1`` 匹配。"""

    def classify(value):
        match value:
            case 1:
                return "numeric-one"
            case True:
                return "true-singleton"
            case _:
                return "other"

    assert classify(1) == "numeric-one"
    assert classify(True) == "numeric-one"

    # 如果业务必须区分布尔值和数值 1，应把 case True 放在 case 1 前面，或在
    # 数值 case 增加类型 guard。


def test_capture_pattern_matches_anything_and_binds_the_subject():
    """裸名称是 capture，不会读取外部同名“常量”。"""

    READY = "this outer value is not compared"

    def capture(subject):
        match subject:
            case READY:
                return READY

    assert capture("anything") == "anything"
    assert capture(42) == 42
    assert READY == "this outer value is not compared"

    # case READY 在 capture 函数作用域创建局部绑定，因此这个唯一 case 永远
    # 成功。若后面还有 case，编译器会因为后续分支不可达而直接报 SyntaxError。


def test_bare_constant_name_before_fallback_is_a_compile_time_error():
    """要匹配常量必须使用 dotted name；裸名会成为不可反驳的 capture。"""

    source = """
READY = "ready"
def classify(value):
    match value:
        case READY:
            return "ready"
        case _:
            return "other"
"""

    with pytest.raises(SyntaxError, match="name capture.*remaining patterns"):
        compile(source, "<bare-value-pattern>", "exec")


def test_dotted_name_is_a_value_pattern_instead_of_a_capture():
    """限定名称在匹配时解析其值，不创建新的局部变量。"""

    class Status:
        READY = "ready"
        FAILED = "failed"

    def classify(value):
        match value:
            case Status.READY:
                return "can-run"
            case Status.FAILED:
                return "must-stop"
            case _:
                return "unknown"

    assert classify("ready") == "can-run"
    assert classify("failed") == "must-stop"
    assert classify("waiting") == "unknown"


def test_wildcard_matches_without_binding_an_underscore_name():
    """``_`` 是明确丢弃值的 wildcard，不会写入局部命名空间。"""

    def discard(value):
        match value:
            case _:
                return "_" in locals()

    assert discard("anything") is False


def test_or_pattern_tries_alternatives_that_bind_the_same_names():
    """``|`` 共享一个 suite，每个 alternative 必须产生一致的绑定集合。"""

    def command_key(command):
        match command:
            case ("get", key) | ("delete", key):
                return key
            case _:
                return None

    assert command_key(("get", "language")) == "language"
    assert command_key(("delete", "cache")) == "cache"
    assert command_key(("set", "mode", "safe")) is None


def test_or_pattern_with_different_bindings_is_a_syntax_error():
    """alternative 若绑定不同名称，后续 suite 无法获得确定的局部变量。"""

    source = """
def broken(value):
    match value:
        case ("left", left) | ("right", right):
            return left, right
"""

    with pytest.raises(SyntaxError, match="alternative patterns bind different names"):
        compile(source, "<or-pattern-bindings>", "exec")


def test_as_pattern_keeps_the_whole_value_and_its_deconstructed_part():
    """``pattern as name`` 在结构匹配成功后额外绑定完整 subject。"""

    event = ("ok", {"count": 3})

    match event:
        case ("ok", {"count": count}) as whole:
            result = count, whole
        case _:
            result = None

    assert result == (3, event)


def test_guard_runs_only_after_pattern_success_and_can_reject_a_case():
    """guard 不是 pattern 的一部分；结构先绑定，随后条件决定是否选中 suite。"""

    events = []

    def positive(number):
        events.append(("guard", number))
        return number > 0

    def classify(value):
        match value:
            case int() as number if positive(number):
                return "positive-int"
            case int():
                return "other-int"
            case _:
                return "not-int"

    assert classify("1") == "not-int"
    assert events == []
    assert classify(-1) == "other-int"
    assert events == [("guard", -1)]
    assert classify(2) == "positive-int"
    assert events == [("guard", -1), ("guard", 2)]


def test_guard_exception_propagates_instead_of_becoming_a_failed_match():
    """guard 中的异常是普通运行时异常，不会让解释器静默尝试下一 case。"""

    def broken_guard(value):
        raise RuntimeError(f"cannot check {value}")

    def classify(value):
        match value:
            case int() as number if broken_guard(number):
                return "matched"
            case _:
                return "fallback"

    with pytest.raises(RuntimeError, match="cannot check 3"):
        classify(3)

    # guard 应保持短小、无副作用；复杂 I/O 或状态修改会因 case 尝试顺序而变得
    # 难以推理。


def test_sequence_pattern_supports_fixed_and_starred_parts():
    """序列 pattern 可拆固定位置，并把中间剩余项捕获成新 list。"""

    def split(sequence):
        match sequence:
            case [first, *middle, last]:
                return first, middle, last
            case _:
                return None

    assert split([1, 2, 3, 4]) == (1, [2, 3], 4)
    assert split((1, 2)) == (1, [], 2)
    assert split([1]) is None


def test_group_pattern_and_single_item_sequence_pattern_are_different():
    """``(name)`` 只是分组，``(name,)`` 才要求长度为一的 sequence。"""

    def grouped(value):
        match value:
            case (captured):
                return captured

    def single_item(value):
        match value:
            case (only,):
                return only
            case _:
                return None

    assert grouped("not a sequence requirement") == "not a sequence requirement"
    assert single_item([42]) == 42
    assert single_item((42,)) == 42
    assert single_item(42) is None


def test_string_bytes_and_bytearray_are_excluded_from_sequence_patterns():
    """文本/二进制标量不会被 pattern 自动拆成字符或整数。"""

    def is_two_item_sequence(value):
        match value:
            case [first, second]:
                return first, second
            case _:
                return None

    assert is_two_item_sequence(["a", "b"]) == ("a", "b")
    assert is_two_item_sequence("ab") is None
    assert is_two_item_sequence(b"ab") is None
    assert is_two_item_sequence(bytearray(b"ab")) is None


def test_mapping_pattern_requires_listed_keys_but_allows_extras():
    """mapping pattern 是子集约束，``**rest`` 可显式收集额外键。"""

    event = {
        "type": "lesson",
        "id": 7,
        "title": "Pattern matching",
        "draft": True,
    }

    match event:
        case {"type": "lesson", "id": identifier, **rest}:
            result = identifier, rest
        case _:
            result = None

    assert result == (
        7,
        {"title": "Pattern matching", "draft": True},
    )

    # 未写 **rest 时额外键也不会导致失败；mapping pattern 默认不是“键集合必须
    # 完全相等”的校验器。


def test_mapping_pattern_uses_get_without_triggering_missing_hook():
    """缺键检查通过 mapping ``get`` 完成，不应制造 ``__missing__`` 默认值。"""

    class MissingAwareDict(dict):
        def __init__(self):
            super().__init__()
            self.missing_calls = []

        def __missing__(self, key):
            self.missing_calls.append(key)
            return "created"

    values = MissingAwareDict()
    values["other"] = 1

    match values:
        case {"required": captured}:
            result = captured
        case _:
            result = "not-matched"

    assert result == "not-matched"
    assert values.missing_calls == []
    assert values == {"other": 1}


class Point:
    __match_args__ = ("x", "y")

    def __init__(self, x, y, label=None):
        self.x = x
        self.y = y
        self.label = label


def test_class_pattern_uses_type_attributes_and_match_args():
    """位置子模式由 ``__match_args__`` 映射，关键字子模式直接读取属性。"""

    def describe(point):
        match point:
            case Point(0, y, label="axis"):
                return f"y-axis:{y}"
            case Point(x=x, y=y):
                return f"point:{x},{y}"
            case _:
                return "not-a-point"

    assert describe(Point(0, 5, "axis")) == "y-axis:5"
    assert describe(Point(2, 3)) == "point:2,3"
    assert describe((2, 3)) == "not-a-point"

    # 调整公开类的 __match_args__ 顺序会改变所有位置 class pattern 的含义；
    # 需要长期稳定时，关键字 pattern 通常更明确。


def test_builtin_class_pattern_can_capture_the_whole_builtin_value():
    """若干内置类型允许一个位置子模式直接匹配对象自身。"""

    def normalize(value):
        match value:
            case int(number):
                return "int", number
            case str(text):
                return "str", text
            case _:
                return "other", value

    assert normalize(7) == ("int", 7)
    assert normalize("python") == ("str", "python")
    assert normalize(3.5) == ("other", 3.5)


def test_class_pattern_attribute_error_means_no_match_but_other_errors_propagate():
    """属性提取的 ``AttributeError`` 使 pattern 失败，其他异常保持可见。"""

    class MaybeValue:
        def __init__(self, failure):
            self.failure = failure

        @property
        def value(self):
            if self.failure == "missing":
                raise AttributeError("value unavailable")
            if self.failure == "broken":
                raise RuntimeError("storage broken")
            return 42

    def extract(subject):
        match subject:
            case MaybeValue(value=value):
                return value
            case _:
                return None

    assert extract(MaybeValue("missing")) is None
    assert extract(MaybeValue(None)) == 42

    with pytest.raises(RuntimeError, match="storage broken"):
        extract(MaybeValue("broken"))


def test_too_many_positional_class_subpatterns_raise_type_error():
    """位置子模式数量不能超过 ``__match_args__`` 暴露的名称数。"""

    class SingleField:
        __match_args__ = ("value",)

        def __init__(self, value):
            self.value = value

    def extract(subject):
        match subject:
            case SingleField(first, second):
                return first, second
            case _:
                return None

    with pytest.raises(TypeError, match="accepts 1 positional sub-pattern"):
        extract(SingleField(1))


def test_successful_pattern_bindings_remain_in_the_surrounding_scope():
    """case 不创建独立局部作用域，成功捕获的名称可在 match 后使用。"""

    def extract_name(subject):
        match subject:
            case {"name": name}:
                matched = True
            case _:
                return None
        assert matched
        return name

    assert extract_name({"name": "Python"}) == "Python"
    assert extract_name({"title": "missing name"}) is None

    # 不要依赖失败 pattern 的“部分绑定”状态，规范刻意不给出统一保证。只在确定
    # 成功的 suite 或其后明确可达路径读取捕获名称。
