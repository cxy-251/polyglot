"""010｜同步上下文管理器和 ``with`` 展开规则的可执行示例。

``with expression as target`` 只求值一次 expression，随后在类型上查找
``__enter__`` / ``__exit__``。enter 的返回值绑定给 target；离开 suite 时，
exit 接收正常退出的三个 ``None``，或接收异常类型、实例与 traceback。exit
的返回值按真假判断是否抑制异常。多个管理器等价于嵌套 with，因此按从左到右
进入、从右到左退出，并且只清理已经成功进入的部分。

内容基于 Python 3.10 With statement、With Statement Context Managers 和
Context Manager Types。当前项目处于只编写、暂不执行的阶段，本文件尚未经过
pytest 验证。
"""

# polyglot-covers: python.statement.with python.statement.with-as
# polyglot-covers: python.protocol.__enter__ python.protocol.__exit__
# polyglot-covers: python.context.normal-exit python.context.exception-exit
# polyglot-covers: python.context.exception-suppression
# polyglot-covers: python.context.multiple-managers
# polyglot-covers: python.context.non-local-control-flow

import pytest


class RecordingContext:
    """记录 enter/exit 顺序和 exit 参数的通用同步管理器。"""

    def __init__(self, name, events, enter_value=None, suppress=False):
        self.name = name
        self.events = events
        self.enter_value = enter_value
        self.suppress = suppress
        self.exit_arguments = None

    def __enter__(self):
        self.events.append(("enter", self.name))
        if self.enter_value is None:
            return self
        return self.enter_value

    def __exit__(self, exception_type, exception, traceback):
        self.events.append(("exit", self.name))
        self.exit_arguments = (exception_type, exception, traceback)
        return self.suppress


def test_with_evaluates_expression_once_and_binds_enter_return_value():
    """``as`` 目标接收 enter 的结果，不保证是 manager 自身。"""

    events = []
    resource = {"state": "open"}
    manager = RecordingContext("resource", events, enter_value=resource)

    def build_manager():
        events.append(("build", "resource"))
        return manager

    with build_manager() as bound:
        events.append(("body", bound["state"]))
        assert bound is resource
        assert bound is not manager

    assert events == [
        ("build", "resource"),
        ("enter", "resource"),
        ("body", "open"),
        ("exit", "resource"),
    ]
    assert manager.exit_arguments == (None, None, None)

    # manager 常负责生命周期，enter 返回的则可以是连接、文件句柄或代理对象。
    # 因此不要假定 `with manager as value` 中 value is manager。


def test_exception_exit_receives_the_exact_exception_and_traceback():
    """suite 抛异常时，exit 获得与 except 处理器相同的诊断三元组。"""

    events = []
    manager = RecordingContext("operation", events)
    original = ValueError("invalid input")

    with pytest.raises(ValueError) as caught:
        with manager:
            raise original

    exception_type, exception, exception_traceback = manager.exit_arguments

    assert caught.value is original
    assert exception_type is ValueError
    assert exception is original
    assert exception_traceback is original.__traceback__
    assert events == [("enter", "operation"), ("exit", "operation")]


def test_false_exit_result_allows_the_original_exception_to_propagate():
    """返回假值表示 manager 已清理，但没有处理业务异常。"""

    events = []
    manager = RecordingContext("no-suppression", events, suppress=False)

    with pytest.raises(RuntimeError, match="operation failed"):
        with manager:
            raise RuntimeError("operation failed")


def test_truthy_exit_result_suppresses_the_exception():
    """exit 返回值按真假判断；真值表示异常已经被完整处理。"""

    events = []
    manager = RecordingContext("suppression", events, suppress="handled")

    with manager:
        events.append(("body", "before-error"))
        raise LookupError("hidden by manager")

    events.append(("after", "continued"))

    assert events == [
        ("enter", "suppression"),
        ("body", "before-error"),
        ("exit", "suppression"),
        ("after", "continued"),
    ]
    assert manager.exit_arguments[0] is LookupError

    # 无条件返回真值会吞掉所有异常，包括管理器并不理解的 bug。更安全的实现
    # 通常只对明确可恢复的异常类型返回 True，其余返回 False/None。


class SelectiveSuppressor:
    def __init__(self, accepted_type):
        self.accepted_type = accepted_type

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        return exception_type is not None and issubclass(
            exception_type, self.accepted_type
        )


def test_context_manager_can_suppress_only_an_expected_exception_family():
    """按异常类型选择性恢复，其他错误继续传播。"""

    with SelectiveSuppressor(ValueError):
        raise ValueError("expected parse failure")

    with pytest.raises(TypeError, match="programming error"):
        with SelectiveSuppressor(ValueError):
            raise TypeError("programming error")


def test_enter_failure_does_not_call_exit_on_the_same_manager():
    """只有 enter 正常返回后，with 才承担调用对应 exit 的责任。"""

    events = []

    class FailingEnter:
        def __enter__(self):
            events.append("enter-started")
            raise RuntimeError("acquisition failed")

        def __exit__(self, exception_type, exception, traceback):
            events.append("exit")

    with pytest.raises(RuntimeError, match="acquisition failed"):
        with FailingEnter():
            events.append("body")

    assert events == ["enter-started"]

    # 如果 __enter__ 分多步获取资源并在中途失败，它必须自行回滚已完成的步骤；
    # 同一对象的 __exit__ 不会自动救场。


def test_as_target_binding_failure_is_sent_to_exit():
    """enter 已返回后，连 ``as`` 解包失败也属于需要 exit 处理的异常。"""

    events = []
    manager = RecordingContext("binding", events, enter_value=["only-one"])

    with pytest.raises(ValueError):
        with manager as (first, second):
            events.append((first, second))

    assert events == [("enter", "binding"), ("exit", "binding")]
    assert manager.exit_arguments[0] is ValueError


def test_multiple_managers_enter_left_to_right_and_exit_right_to_left():
    """逗号形式的多个 manager 等价于多层嵌套 with。"""

    events = []
    outer = RecordingContext("outer", events)
    inner = RecordingContext("inner", events)

    with outer, inner:
        events.append(("body", "running"))

    assert events == [
        ("enter", "outer"),
        ("enter", "inner"),
        ("body", "running"),
        ("exit", "inner"),
        ("exit", "outer"),
    ]

    # 逆序退出保证依赖后创建的内部资源先释放，再释放它所依赖的外部资源。


def test_later_enter_failure_still_exits_already_entered_managers():
    """部分进入时只清理成功 enter 的前序 manager。"""

    events = []
    first = RecordingContext("first", events)

    class FailingSecond:
        def __enter__(self):
            events.append(("enter", "second"))
            raise RuntimeError("second failed")

        def __exit__(self, exception_type, exception, traceback):
            events.append(("exit", "second"))

    with pytest.raises(RuntimeError, match="second failed"):
        with first, FailingSecond():
            events.append(("body", "unreachable"))

    assert events == [
        ("enter", "first"),
        ("enter", "second"),
        ("exit", "first"),
    ]
    assert first.exit_arguments[0] is RuntimeError


def test_inner_suppression_makes_outer_manager_see_a_normal_exit():
    """内层吞掉异常后，外层 exit 接收三个 ``None``。"""

    events = []
    outer = RecordingContext("outer", events)
    inner = RecordingContext("inner", events, suppress=True)

    with outer, inner:
        raise ValueError("handled by inner")

    assert inner.exit_arguments[0] is ValueError
    assert outer.exit_arguments == (None, None, None)
    assert events == [
        ("enter", "outer"),
        ("enter", "inner"),
        ("exit", "inner"),
        ("exit", "outer"),
    ]


def test_return_runs_exit_before_the_value_leaves_the_function():
    """函数 return 是非局部跳转，但不能绕过上下文清理。"""

    events = []
    manager = RecordingContext("return", events)

    def operation():
        with manager:
            events.append(("body", "returning"))
            return "result"

    assert operation() == "result"
    assert events == [
        ("enter", "return"),
        ("body", "returning"),
        ("exit", "return"),
    ]
    assert manager.exit_arguments == (None, None, None)


def test_break_runs_exit_before_the_loop_finishes():
    """``break`` 同样先退出当前 with，再离开循环。"""

    events = []
    manager = RecordingContext("break", events)

    for value in range(3):
        with manager:
            events.append(("body", value))
            break

    assert events == [
        ("enter", "break"),
        ("body", 0),
        ("exit", "break"),
    ]
    assert manager.exit_arguments == (None, None, None)


def test_exit_failure_replaces_body_exception_and_keeps_it_as_context():
    """清理阶段抛新异常时，新异常传播，原业务异常成为上下文。"""

    class FailingExit:
        def __enter__(self):
            return self

        def __exit__(self, exception_type, exception, traceback):
            raise RuntimeError("cleanup failed")

    with pytest.raises(RuntimeError, match="cleanup failed") as error:
        with FailingExit():
            raise ValueError("body failed")

    assert isinstance(error.value.__context__, ValueError)
    assert str(error.value.__context__) == "body failed"

    # 清理失败可能比业务失败更接近最终观察点，却不应让日志丢失原始上下文。


def test_with_looks_up_protocol_methods_on_the_manager_type():
    """实例上的同名属性不会遮蔽类型定义的 with 特殊方法。"""

    events = []

    class Manager:
        def __enter__(self):
            events.append("type-enter")
            return self

        def __exit__(self, exception_type, exception, traceback):
            events.append("type-exit")

    manager = Manager()
    manager.__enter__ = lambda: events.append("instance-enter")
    manager.__exit__ = lambda *arguments: events.append("instance-exit")

    with manager:
        events.append("body")

    assert events == ["type-enter", "body", "type-exit"]

    # 与运算符等特殊方法相同，with 在类型上做隐式协议查找；手工调用
    # manager.__enter__() 才会看到实例字典中的替代函数。
