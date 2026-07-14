"""248｜``concurrent.futures.Future`` pending/running/cancelled/finished state machine。

Executor 通常创建 Future；官方也允许 unit test/Executor implementation 直接构造。
cancel 只对尚未 running 的 work 成功。result/exception 根据 terminal state 返回或重抛；
callback 按注册顺序执行，若注册时已完成则在 add_done_callback 调用内立即执行。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.concurrent.futures.Future
# polyglot-covers: python.concurrent.futures.Future.cancel
# polyglot-covers: python.concurrent.futures.Future.cancelled
# polyglot-covers: python.concurrent.futures.Future.running
# polyglot-covers: python.concurrent.futures.Future.done
# polyglot-covers: python.concurrent.futures.Future.result
# polyglot-covers: python.concurrent.futures.Future.exception
# polyglot-covers: python.concurrent.futures.Future.add_done_callback
# polyglot-covers: python.concurrent.futures.Future-callback-order
# polyglot-covers: python.concurrent.futures.Future-completed-callback-immediate
# polyglot-covers: python.concurrent.futures.Future.set_running_or_notify_cancel
# polyglot-covers: python.concurrent.futures.Future.set_result
# polyglot-covers: python.concurrent.futures.Future.set_exception
# polyglot-covers: python.concurrent.futures.CancelledError
# polyglot-covers: python.concurrent.futures.InvalidStateError

import concurrent.futures

import pytest


def test_pending_future_can_be_cancelled_and_wakes_callbacks():
    """cancelled 也属于 done；result/exception 都用 CancelledError 表示没有 outcome。"""

    future = concurrent.futures.Future()
    callbacks = []
    future.add_done_callback(lambda completed: callbacks.append(completed.cancelled()))

    assert future.running() is False
    assert future.done() is False
    assert future.cancel() is True

    assert future.cancelled() is True
    assert future.done() is True
    assert future.cancel() is True
    assert callbacks == [True]
    with pytest.raises(concurrent.futures.CancelledError):
        future.result()
    with pytest.raises(concurrent.futures.CancelledError):
        future.exception()


def test_executor_transition_refuses_cancel_once_future_is_running():
    """set_running_or_notify_cancel 是 Executor 开工前的原子关口。"""

    future = concurrent.futures.Future()

    assert future.set_running_or_notify_cancel() is True
    assert future.running() is True
    assert future.cancel() is False

    future.set_result(42)

    assert future.running() is False
    assert future.done() is True
    assert future.cancelled() is False
    assert future.result() == 42
    assert future.exception() is None


def test_cancelled_future_tells_executor_not_to_run_callable():
    """cancel 先赢得 state transition 后，Executor gate 返回 False。"""

    future = concurrent.futures.Future()
    future.cancel()

    assert future.set_running_or_notify_cancel() is False
    assert future.cancelled() is True


def test_set_exception_is_observable_and_result_reraises_same_object():
    """exception() 返回 exception instance；result() 以该 instance 失败。"""

    future = concurrent.futures.Future()
    error = LookupError("missing")
    future.set_exception(error)

    assert future.exception() is error
    with pytest.raises(LookupError, match="missing") as raised:
        future.result()
    assert raised.value is error


def test_terminal_result_is_single_assignment_and_callbacks_preserve_order():
    """完成后 callback 立即执行；第二次 set result/exception 是 InvalidStateError。"""

    future = concurrent.futures.Future()
    calls = []
    future.add_done_callback(lambda completed: calls.append(("first", completed.result())))
    future.add_done_callback(lambda completed: calls.append(("second", completed.result())))

    future.set_result("ready")
    future.add_done_callback(lambda completed: calls.append(("late", completed.result())))

    assert calls == [
        ("first", "ready"),
        ("second", "ready"),
        ("late", "ready"),
    ]
    with pytest.raises(concurrent.futures.InvalidStateError):
        future.set_result("again")
    with pytest.raises(concurrent.futures.InvalidStateError):
        future.set_exception(RuntimeError("too late"))
