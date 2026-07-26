"""001｜真假值判断、布尔运算与 ``__bool__`` / ``__len__`` 协议。

这个测试套把日常代码里的 ``if``、``not``、``and``、``or`` 和
``bool(value)`` 放在同一个主题中，因为它们最终都依赖对象的真假值。
重点不是记住一张“哪些值是假”的表，而是理解 Python 如何询问一个对象
“你应当被视为真还是假”。

内容基于 Python 3.10 的 Truth Value Testing、Boolean Operations 和 Data
Model。
"""

# polyglot-covers: python.core.truth-value-testing
# polyglot-covers: python.expression.boolean-operations
# polyglot-covers: python.builtin.bool
# polyglot-covers: python.protocol.__bool__
# polyglot-covers: python.protocol.__len__
# polyglot-covers: python.data-model.special-method-lookup

# 跨语言迁移提示：Python 允许对象用 __bool__ / __len__ 定义真假，空容器通常为假；
# JavaScript 的对象（包括空数组）始终为真，C++ 则使用数值、指针或 explicit operator bool 的上下文转换。

import pytest


def test_builtin_values_follow_zero_empty_and_none_truth_rules():
    """内置对象通常以“零、空、None”为假，其余对象为真。"""

    # 这里选择不同类别的代表值，而不是穷举每一种内置类型。整数、浮点数、
    # 复数都遵循数值零为假的规则；容器则以是否为空决定真假值。
    falsy_values = [None, False, 0, 0.0, 0j, "", (), [], {}, set(), range(0)]
    truthy_values = [True, 1, -1, 0.1, "False", (0,), [False], {"enabled": False}]

    assert all(bool(value) is False for value in falsy_values)
    assert all(bool(value) is True for value in truthy_values)

    # 常见坑：Python 不理解字符串或容器内容的“人类含义”。字符串 "False"
    # 不是空字符串，所以是真；列表 [False] 不是空列表，所以也是真。
    assert bool("False") is True
    assert bool([False]) is True


def test_not_always_returns_a_real_boolean():
    """``not`` 根据真假值取反，但结果一定是 ``True`` 或 ``False``。"""

    marker = object()

    assert (not marker) is False
    assert (not []) is True


def test_and_and_or_return_operands_instead_of_forcing_bool_results():
    """``and`` 和 ``or`` 选择并返回操作数本身。"""

    default_settings = {"theme": "light"}
    configured_settings = {"theme": "dark"}

    # ``or`` 返回第一个真值操作数；如果左侧是假值，就返回右侧对象本身。
    # 这正是 ``configured or default`` 默认值写法能够保留原始对象类型的原因。
    assert (configured_settings or default_settings) is configured_settings
    assert ({} or default_settings) is default_settings

    # ``and`` 返回第一个假值操作数；只有左侧为真时才返回右侧。
    # 常见坑是误以为布尔运算符总返回 bool，进而写出依赖错误返回类型的代码。
    payload = ["ready"]
    assert (payload and "send") == "send"
    assert ([] and "send") == []


def test_and_and_or_short_circuit_the_right_operand():
    """结果已经由左侧决定时，右侧表达式不会求值。"""

    events = []

    def record_evaluation():
        events.append("evaluated")
        return "right operand"

    assert (False and record_evaluation()) is False
    assert (True or record_evaluation()) is True
    assert events == []

    # 左侧无法决定结果时才会计算右侧；这也是用 ``value and operation()``
    # 编写条件调用时必须理解的求值行为。
    assert (True and record_evaluation()) == "right operand"
    assert events == ["evaluated"]


class FeatureFlag:
    """用最小自定义类型展示 ``__bool__`` 如何定义业务真假值。"""

    def __init__(self, enabled):
        self.enabled = enabled

    def __bool__(self):
        return self.enabled


def test_bool_and_if_dispatch_to_dunder_bool():
    """``bool(value)`` 和条件语句使用相同的 ``__bool__`` 协议。"""

    enabled_flag = FeatureFlag(True)
    disabled_flag = FeatureFlag(False)

    assert bool(enabled_flag) is True
    assert bool(disabled_flag) is False

    observed = []
    if enabled_flag:
        observed.append("enabled")
    if disabled_flag:
        observed.append("disabled")

    assert observed == ["enabled"]


class PendingJobs:
    """没有 ``__bool__`` 时，容器式对象可以用长度表达真假值。"""

    def __init__(self, jobs):
        self.jobs = list(jobs)

    def __len__(self):
        return len(self.jobs)


def test_truth_testing_falls_back_to_dunder_len():
    """对象未定义 ``__bool__`` 时，Python 使用 ``__len__`` 的结果。"""

    assert bool(PendingJobs([])) is False
    assert bool(PendingJobs(["backup"])) is True

    # 如果一个类既没有 __bool__ 也没有 __len__，实例默认被视为真。
    assert bool(object()) is True


def test_condition_contexts_reuse_the_same_truth_protocol():
    """``if``、``while`` 和条件表达式不会各自发明一套真假规则。"""

    pending = PendingJobs(["backup", "report"])

    # 条件表达式和 if 一样对条件对象做真假值测试，所以这里会调用 __len__。
    state = "work available" if pending else "idle"
    assert state == "work available"

    processed = []
    while pending:
        processed.append(pending.jobs.pop(0))

    assert processed == ["backup", "report"]
    assert bool(pending) is False


class BoolTakesPriority:
    """同时定义两个协议，用调用记录证明 ``__bool__`` 优先。"""

    def __init__(self):
        self.calls = []

    def __bool__(self):
        self.calls.append("__bool__")
        return False

    def __len__(self):
        self.calls.append("__len__")
        return 5


def test_dunder_bool_takes_priority_over_dunder_len():
    """``__len__`` 是 fallback，不是与 ``__bool__`` 并列执行的检查。"""

    value = BoolTakesPriority()

    assert bool(value) is False
    assert value.calls == ["__bool__"]


class InvalidBoolResult:
    def __bool__(self):
        # 常见协议实现错误：1 虽然本身是真值，但 __bool__ 的契约要求真正的 bool。
        return 1


def test_dunder_bool_must_return_bool_not_merely_a_truthy_value():
    """``__bool__`` 返回普通真值对象时，Python 不会再次替它做真假转换。"""

    with pytest.raises(TypeError):
        bool(InvalidBoolResult())


class InvalidNegativeLength:
    def __len__(self):
        return -1


def test_dunder_len_cannot_use_a_negative_number_as_false():
    """长度协议必须返回非负整数；负数不是另一种表示“空”的方式。"""

    with pytest.raises(ValueError):
        bool(InvalidNegativeLength())


class PlainObject:
    pass


def test_special_method_lookup_uses_the_type_not_an_instance_attribute():
    """给单个实例临时添加 ``__bool__`` 不会改变内置真假值操作。"""

    value = PlainObject()
    value.__bool__ = lambda: False

    # 普通显式属性访问能够找到刚写入实例字典的函数。
    assert value.__bool__() is False

    # 但 bool(value) 对特殊方法做隐式查找时直接查看类型，跳过实例属性。
    # 这是数据模型中非常容易误解的规则；需要改变行为时应在类上定义
    # __bool__，而不是给某个实例 monkey-patch 同名属性。
    assert bool(value) is True
