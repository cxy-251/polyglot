"""函数定义、调用和参数绑定的可执行示例。

函数调用包含两个不同阶段：先从左到右求值所有实参表达式，再按函数签名完成
位置与关键字绑定。``*`` / ``**`` 在定义端负责收集，在调用端负责解包；仅限
位置参数、仅限关键字参数和默认值又会进一步约束绑定方式。函数注解只记录
元数据，不会替代运行时校验。任何实现 ``__call__`` 的对象也能进入相同调用
语法。

内容基于 Python 3.10 Function definitions、Calls、Lambdas 和 Data Model
``object.__call__``。当前项目处于只编写、暂不执行的阶段，本文件尚未经过
pytest 验证。
"""

# polyglot-covers: python.statement.function-definition
# polyglot-covers: python.expression.call python.expression.lambda
# polyglot-covers: python.function.return python.function.default-arguments
# polyglot-covers: python.function.positional-only python.function.keyword-only
# polyglot-covers: python.function.var-positional python.function.var-keyword
# polyglot-covers: python.call.star-unpacking python.call.double-star-unpacking
# polyglot-covers: python.function.annotations python.function.closure-late-binding
# polyglot-covers: python.protocol.__call__ python.builtin.callable

import pytest


def test_def_creates_a_callable_function_object_with_metadata():
    """``def`` 绑定一个函数对象；函数名和文档字符串保存在对象上。"""

    def greeting(name):
        """Return one readable greeting."""

        return f"Hello, {name}!"

    assert callable(greeting)
    assert greeting("Python") == "Hello, Python!"
    assert greeting.__name__ == "greeting"
    assert greeting.__doc__ == "Return one readable greeting."


def test_falling_off_a_function_body_returns_none():
    """没有执行带值 ``return`` 的函数会隐式返回 ``None``。"""

    events = []

    def remember(value):
        events.append(value)

    result = remember("called")

    assert result is None
    assert events == ["called"]

    # 常见坑：副作用已经发生并不意味着函数也返回了被保存的值。调用者若需要
    # 链式使用结果，函数必须显式 return；否则变量只会接收到 None。


def test_regular_parameters_accept_positional_and_keyword_arguments():
    """普通参数可按位置绑定，也可用名称绑定；默认值补足省略项。"""

    def describe(language, version="3.10", stable=True):
        return language, version, stable

    assert describe("Python") == ("Python", "3.10", True)
    assert describe("Python", "3.11", False) == ("Python", "3.11", False)
    assert describe(stable=False, language="Python") == ("Python", "3.10", False)

    # 关键字实参的书写顺序不需要与形参顺序一致；绑定依据名称完成。


def test_positional_only_and_keyword_only_parameters_enforce_the_api_boundary():
    """``/`` 左侧只能按位置传递，裸 ``*`` 右侧只能按关键字传递。"""

    def connect(host, /, port=443, *, timeout, secure=True):
        return host, port, timeout, secure

    assert connect("example.com", timeout=5) == ("example.com", 443, 5, True)
    assert connect("example.com", 80, timeout=2, secure=False) == (
        "example.com",
        80,
        2,
        False,
    )

    with pytest.raises(TypeError):
        connect(host="example.com", timeout=5)

    with pytest.raises(TypeError):
        connect("example.com", 443, 5)


def test_positional_only_name_can_also_appear_inside_keyword_options():
    """仅限位置参数的名称不会占用 ``**kwargs`` 中的同名键。"""

    def register(name, /, **metadata):
        return name, metadata

    assert register("primary", name="display name", active=True) == (
        "primary",
        {"name": "display name", "active": True},
    )

    # 这是 / 的一个实用理由：API 可以保留位置参数名的重命名自由，同时允许
    # **metadata 接收任何外部字段，即使字段刚好与内部形参同名。


def test_default_argument_expression_is_evaluated_once_at_definition_time():
    """默认值属于函数对象，不会在每次省略实参时重新创建。"""

    events = []

    def build_default():
        events.append("built")
        return object()

    def choose(value=build_default()):
        return value

    assert events == ["built"]

    first = choose()
    second = choose()

    assert first is second
    assert events == ["built"]


def test_mutable_default_argument_leaks_state_between_calls():
    """可变默认对象会被后续调用复用，是常见且隐蔽的状态泄漏。"""

    def append_incorrectly(item, bucket=[]):
        bucket.append(item)
        return bucket

    first = append_incorrectly("syntax")
    second = append_incorrectly("protocol")

    assert first is second
    assert second == ["syntax", "protocol"]

    # 这个默认 list 在 def 执行时只创建一次，因此不是“每次调用的临时列表”。
    # 除非函数有意缓存状态，否则不要用可变对象作为默认值。


def test_none_sentinel_creates_a_fresh_mutable_value_per_call():
    """用不可变哨兵表示“未提供”，再在函数体内创建容器。"""

    def append_safely(item, bucket=None):
        if bucket is None:
            bucket = []
        bucket.append(item)
        return bucket

    first = append_safely("syntax")
    second = append_safely("protocol")
    supplied = append_safely("testing", ["stdlib"])

    assert first == ["syntax"]
    assert second == ["protocol"]
    assert first is not second
    assert supplied == ["stdlib", "testing"]


def test_var_positional_and_var_keyword_parameters_collect_extra_arguments():
    """定义端的 ``*args`` 收集 tuple，``**kwargs`` 收集新的 dict。"""

    def collect(first, *items, **options):
        return first, items, options

    result = collect("python", "syntax", "stdlib", strict=True, version="3.10")

    assert result == (
        "python",
        ("syntax", "stdlib"),
        {"strict": True, "version": "3.10"},
    )
    assert type(result[1]) is tuple
    assert type(result[2]) is dict


def test_call_side_unpacking_expands_iterables_and_mappings():
    """调用端 ``*`` 展开 iterable，``**`` 按键名展开 mapping。"""

    def collect(*items, **options):
        return items, options

    positional = ["syntax", "protocol"]
    more_positional = ("stdlib",)
    keywords = {"version": "3.10", "verified": False}

    assert collect("python", *positional, *more_positional, **keywords) == (
        ("python", "syntax", "protocol", "stdlib"),
        {"version": "3.10", "verified": False},
    )

    # 定义端 *items 是“收集”，调用端 *positional 是“展开”；符号相同但数据
    # 流向相反。** 的两端同理，不能把 list of pairs 直接当作调用端 mapping。


def test_argument_binding_rejects_missing_extra_duplicate_and_unknown_values():
    """实参与签名无法形成唯一绑定时，函数体不会开始执行。"""

    body_calls = []

    def add(left, right):
        body_calls.append((left, right))
        return left + right

    with pytest.raises(TypeError):
        add(1)

    with pytest.raises(TypeError):
        add(1, 2, 3)

    with pytest.raises(TypeError):
        add(1, left=2, right=3)

    with pytest.raises(TypeError):
        add(left=1, right=2, unexpected=3)

    assert body_calls == []


def test_double_star_requires_string_keys_and_rejects_duplicate_names():
    """``**mapping`` 的键必须是字符串，多个来源也不能绑定同一名称。"""

    def configure(**options):
        return options

    with pytest.raises(TypeError):
        configure(**{1: "not a keyword name"})

    with pytest.raises(TypeError):
        configure(mode="safe", **{"mode": "fast"})

    # dict 本身能使用任意可哈希键，但 **mapping 要把键变成关键字实参，因此
    # 额外要求 str。重复键也不会采用“后者覆盖前者”的 dict 合并规则。


def test_argument_expressions_are_evaluated_left_to_right_before_binding():
    """调用先求值实参，再进入目标函数。"""

    events = []

    def evaluate(label, value):
        events.append(label)
        return value

    def target(first, second, *, third):
        events.append("body")
        return first, second, third

    result = target(
        evaluate("first", 1),
        evaluate("second", 2),
        third=evaluate("third", 3),
    )

    assert result == (1, 2, 3)
    assert events == ["first", "second", "third", "body"]


def test_binding_failure_does_not_undo_argument_expression_side_effects():
    """即使重复绑定最终报错，已经求值的实参表达式也不会回滚。"""

    events = []

    def evaluate(label, value):
        events.append(label)
        return value

    def target(value):
        events.append("body")
        return value

    with pytest.raises(TypeError):
        target(evaluate("positional", 1), value=evaluate("keyword", 2))

    assert events == ["positional", "keyword"]

    # 常见坑：TypeError 只阻止函数体执行，不会让实参表达式“从未发生”。把网络
    # 写入、计数等副作用放在复杂调用参数中，会让绑定错误更难安全恢复。


def test_annotations_are_metadata_not_automatic_runtime_type_checks():
    """注解保存在 ``__annotations__``，Python 不据此拦截调用。"""

    def repeat(text: str, times: int = 2) -> str:
        return text * times

    assert repeat.__annotations__ == {
        "text": str,
        "times": int,
        "return": str,
    }
    assert repeat("py", 3) == "pypypy"

    # list 明显不符合 text: str，但乘法本身合法，所以函数仍正常运行并返回
    # list。需要运行时校验时必须显式编写，或使用项目选择的外部验证工具。
    assert repeat(["py"], 2) == ["py", "py"]


def test_lambda_creates_a_function_from_one_expression():
    """lambda 适合短小表达式，参数规则与普通函数一致。"""

    scale = lambda value, factor=2: value * factor

    assert callable(scale)
    assert scale(4) == 8
    assert scale(4, factor=3) == 12

    # lambda 的函数体只能是一个表达式；需要语句、多个步骤或说明性文档时，
    # 使用 def 会比强行嵌套表达式更清楚。


def test_lambdas_in_a_loop_capture_the_variable_not_its_current_value():
    """闭包中的自由变量在调用时读取，因此循环创建的 lambda 会晚绑定。"""

    late_bound = [lambda: number for number in range(3)]
    captured_by_default = [lambda number=number: number for number in range(3)]

    assert [function() for function in late_bound] == [2, 2, 2]
    assert [function() for function in captured_by_default] == [0, 1, 2]

    # 默认参数在函数创建时求值，因而能保存每轮值；自由变量则在稍后调用时才
    # 查找，此时循环已经结束并停在 2。这不是 lambda 独有，而是闭包语义。


class RunningTotal:
    def __init__(self, initial=0):
        self.total = initial

    def __call__(self, amount=1):
        self.total += amount
        return self.total


def test_call_method_makes_an_instance_stateful_and_callable():
    """实现 ``__call__`` 后，对象能像函数一样调用，同时保留实例状态。"""

    counter = RunningTotal(10)

    assert callable(counter)
    assert counter() == 11
    assert counter(4) == 15
    assert counter.total == 15


def test_callable_true_does_not_guarantee_every_call_will_succeed():
    """``callable`` 只判断是否具有调用入口，不预测特定调用的业务结果。"""

    class AlwaysFails:
        def __call__(self):
            raise RuntimeError("configured callable failed")

    operation = AlwaysFails()

    assert callable(operation)
    assert not callable(object())

    with pytest.raises(RuntimeError):
        operation()
