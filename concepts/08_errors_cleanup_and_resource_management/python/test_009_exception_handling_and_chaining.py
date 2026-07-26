"""009｜异常匹配、清理控制流与异常链的可执行示例。

``try`` 语句先按书写顺序选择第一个匹配的 ``except``，正常完成时才进入
``else``，无论如何都要执行 ``finally``。异常处理器可以用裸 ``raise`` 保留
原异常，也可用 ``raise ... from ...`` 建立明确的抽象边界。``finally`` 能保证
清理，却也有能力覆盖返回值、吞掉异常或制造新异常，因此其中的控制流要格外
克制。

内容基于 Python 3.10 Try statement、Raise statement、Exceptions data model
和 Built-in Exceptions。
"""

# polyglot-covers: python.statement.try python.statement.except
# polyglot-covers: python.statement.try-else python.statement.finally
# polyglot-covers: python.statement.raise python.statement.bare-raise
# polyglot-covers: python.exception.matching python.exception.custom-exception
# polyglot-covers: python.exception.args python.exception.traceback
# polyglot-covers: python.exception.__context__ python.exception.__cause__
# polyglot-covers: python.exception.__suppress_context__
# polyglot-covers: python.control-flow.finally-return

import traceback

import pytest


class ConfigurationError(Exception):
    """本测试套使用的领域异常基类。"""


class MissingSettingError(ConfigurationError):
    pass


def test_except_matches_subclasses_and_stops_at_the_first_matching_clause():
    """异常类型按继承关系匹配，只执行从上到下第一个命中的处理器。"""

    events = []

    try:
        raise MissingSettingError("token")
    except MissingSettingError:
        events.append("specific")
    except ConfigurationError:
        events.append("base")

    assert events == ["specific"]

    # MissingSettingError 也是 ConfigurationError，但第一个子句已处理后不会再
    # 继续执行基类子句。因此具体类型应放在宽泛基类之前。


def test_broad_handler_first_makes_a_later_specific_handler_unreachable():
    """语法允许把基类写在前面，但它会抢先捕获所有相关子类。"""

    events = []

    try:
        raise MissingSettingError("token")
    except ConfigurationError:
        events.append("broad")
    except MissingSettingError:
        events.append("specific")

    assert events == ["broad"]

    # 这是故意保留的反例。真实代码中后一个 except 永远没有机会执行，细粒度
    # 的恢复逻辑会静默失效。


def test_one_handler_can_catch_a_tuple_of_expected_exception_types():
    """恢复策略相同时，可在一个 except 中列出多个异常类型。"""

    def parse_ratio(numerator, denominator):
        try:
            return int(numerator) / int(denominator)
        except (ValueError, ZeroDivisionError) as error:
            return type(error).__name__

    assert parse_ratio("six", "2") == "ValueError"
    assert parse_ratio("6", "0") == "ZeroDivisionError"
    assert parse_ratio("6", "2") == 3.0


def test_exception_does_not_include_process_exit_signals():
    """常规 ``Exception`` 处理不会捕获 ``KeyboardInterrupt`` 和 ``SystemExit``。"""

    assert issubclass(Exception, BaseException)
    assert issubclass(KeyboardInterrupt, BaseException)
    assert issubclass(SystemExit, BaseException)
    assert not issubclass(KeyboardInterrupt, Exception)
    assert not issubclass(SystemExit, Exception)

    # 裸 except 等价于捕获 BaseException 范围，可能阻止用户中断或进程退出。
    # 除了必须清理后重新抛出的最外层边界，业务代码通常应捕获具体 Exception。


def test_try_else_runs_only_after_the_try_suite_completes_normally():
    """``else`` 把成功路径与可能抛异常的最小 try 区域分开。"""

    def parse(value):
        events = []
        try:
            number = int(value)
        except ValueError:
            events.append("invalid")
        else:
            events.append(("parsed", number))
        finally:
            events.append("finished")
        return events

    assert parse("10") == [("parsed", 10), "finished"]
    assert parse("ten") == ["invalid", "finished"]

    # 把后续成功逻辑放在 else，可避免 except 意外捕获成功逻辑自身抛出的同类
    # 异常；try 区域越小，异常来源越清楚。


def test_overly_wide_try_block_can_swallow_an_unrelated_key_error():
    """捕获范围过大时，恢复逻辑可能误把内部 bug 当成预期缺键。"""

    def transform(record):
        return record["normalized"]

    def load_incorrectly(records, key):
        try:
            record = records[key]
            return transform(record)
        except KeyError:
            return "default"

    records = {"python": {"name": "Python"}}

    assert load_incorrectly(records, "missing") == "default"
    assert load_incorrectly(records, "python") == "default"

    # 第二次并不是 records 缺少 python，而是 transform 内部缺少 normalized。
    # 宽 try 把两种 KeyError 混在一起，掩盖了数据处理 bug。


def test_narrow_try_with_else_preserves_unexpected_errors():
    """只包住预期失败操作，让后续同类型异常继续向外传播。"""

    def transform(record):
        return record["normalized"]

    def load_safely(records, key):
        try:
            record = records[key]
        except KeyError:
            return "default"
        else:
            return transform(record)

    records = {"python": {"name": "Python"}}

    assert load_safely(records, "missing") == "default"

    with pytest.raises(KeyError) as error:
        load_safely(records, "python")

    assert error.value.args == ("normalized",)


def test_finally_runs_for_normal_return_and_for_exceptions():
    """``finally`` 在离开 try 语句前执行，不依赖离开原因。"""

    events = []

    def successful():
        try:
            return "result"
        finally:
            events.append("success-cleanup")

    def failing():
        try:
            raise ValueError("failed")
        finally:
            events.append("failure-cleanup")

    assert successful() == "result"

    with pytest.raises(ValueError, match="failed"):
        failing()

    assert events == ["success-cleanup", "failure-cleanup"]


def test_finally_runs_before_continue_and_break_finish_their_control_flow():
    """循环跳转也要先执行当前迭代对应的 ``finally``。"""

    events = []

    for value in range(3):
        try:
            events.append(("body", value))
            if value == 0:
                continue
            if value == 1:
                break
        finally:
            events.append(("cleanup", value))

    assert events == [
        ("body", 0),
        ("cleanup", 0),
        ("body", 1),
        ("cleanup", 1),
    ]


class InvalidFieldError(ValueError):
    def __init__(self, field, value, reason):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"{field}={value!r}: {reason}")


def test_custom_exception_keeps_machine_readable_fields_and_standard_args():
    """领域异常可增加结构化字段，同时正确初始化异常基类。"""

    error = InvalidFieldError("version", "latest", "expected a pinned version")

    assert error.field == "version"
    assert error.value == "latest"
    assert error.reason == "expected a pinned version"
    assert error.args == ("version='latest': expected a pinned version",)
    assert str(error) == "version='latest': expected a pinned version"

    # 调用 super().__init__ 可保留标准 args、str(error)、序列化等基础行为；
    # 额外字段则让调用者无需解析展示字符串就能作出决定。


def test_bare_raise_rethrows_the_current_exception_instance():
    """处理器内的裸 ``raise`` 重新抛出当前异常。"""

    original = ValueError("invalid")
    events = []

    def validate():
        try:
            raise original
        except ValueError:
            events.append("logged")
            raise

    with pytest.raises(ValueError) as caught:
        validate()

    assert caught.value is original
    assert events == ["logged"]


def test_raise_named_exception_adds_a_new_rethrow_location_to_traceback():
    """``raise error`` 与裸 ``raise`` 都抛同一对象，但 traceback 形态不同。"""

    def origin():
        raise ValueError("origin")

    def rethrow_bare():
        try:
            origin()
        except ValueError:
            raise

    def rethrow_named():
        try:
            origin()
        except ValueError as error:
            raise error

    with pytest.raises(ValueError) as bare:
        rethrow_bare()

    with pytest.raises(ValueError) as named:
        rethrow_named()

    bare_names = [frame.name for frame in traceback.extract_tb(bare.value.__traceback__)]
    named_names = [frame.name for frame in traceback.extract_tb(named.value.__traceback__)]

    assert bare_names.count("rethrow_bare") == 1
    assert named_names.count("rethrow_named") == 2

    # 在“记录后原样向上抛”的场景使用裸 raise，避免把 except 中的再次抛出行
    # 伪装成新的异常来源。显式 raise error 只有在确实想重置位置时才合适。


def test_new_exception_inside_handler_keeps_implicit_context():
    """处理一个异常时又抛出新异常，原异常保存为 ``__context__``。"""

    try:
        try:
            int("not-a-number")
        except ValueError:
            raise ConfigurationError("configuration could not be parsed")
    except ConfigurationError as error:
        captured = error

    assert isinstance(captured.__context__, ValueError)
    assert captured.__cause__ is None
    assert captured.__suppress_context__ is False


def test_raise_from_sets_an_explicit_cause_for_abstraction_boundaries():
    """``raise high_level from low_level`` 明确说明两个异常的因果关系。"""

    source = ValueError("raw value was invalid")

    try:
        try:
            raise source
        except ValueError as error:
            raise ConfigurationError("invalid configuration") from error
    except ConfigurationError as error:
        captured = error

    assert captured.__cause__ is source
    assert captured.__context__ is source
    assert captured.__suppress_context__ is True

    # 显式 cause 适合把底层解析/IO 异常翻译成领域异常：调用者看到稳定抽象，
    # 调试者仍能沿 __cause__ 找到根因。


def test_raise_from_none_hides_displayed_chain_but_keeps_context_object():
    """``from None`` 抑制默认展示，不会从异常对象中删除诊断上下文。"""

    try:
        try:
            int("not-a-number")
        except ValueError:
            raise ConfigurationError("invalid public input") from None
    except ConfigurationError as error:
        captured = error

    assert captured.__cause__ is None
    assert isinstance(captured.__context__, ValueError)
    assert captured.__suppress_context__ is True


def test_except_target_name_is_cleared_after_the_handler():
    """异常目标变量在 except 结束后删除，避免 traceback 形成引用环。"""

    try:
        raise ValueError("temporary")
    except ValueError as error:
        message = str(error)

    assert message == "temporary"

    with pytest.raises(UnboundLocalError):
        _ = error

    # 需要稍后使用异常信息时，应在处理器内提取必要数据或保存到另一个名称。


def test_return_in_finally_overrides_a_pending_return_value():
    """``finally`` 自己 return 时，会丢弃 try 中已经计算好的返回值。"""

    def dangerous_result():
        try:
            return "from try"
        finally:
            return "from finally"

    assert dangerous_result() == "from finally"


def test_return_in_finally_can_silently_swallow_an_exception():
    """更危险的是 finally return 会让正在传播的异常彻底消失。"""

    def dangerous_recovery():
        try:
            raise RuntimeError("important failure")
        finally:
            return "looks successful"

    assert dangerous_recovery() == "looks successful"

    # 这是故意保留的反例。finally 应做无条件清理，通常不应包含 return、break
    # 或 continue；否则调用者可能收到成功值，却完全不知道关键操作已经失败。


def test_new_exception_in_finally_replaces_pending_one_but_keeps_context():
    """finally 抛出新异常时，新异常传播，原异常成为隐式上下文。"""

    def fail_during_cleanup():
        try:
            raise ValueError("operation failed")
        finally:
            raise RuntimeError("cleanup failed")

    with pytest.raises(RuntimeError, match="cleanup failed") as error:
        fail_during_cleanup()

    assert isinstance(error.value.__context__, ValueError)
    assert str(error.value.__context__) == "operation failed"
