"""230｜``contextvars.Context`` mapping、copy、``run`` isolation 与 re-entry guard。

Context 是 ContextVar→value 的 Mapping。``Context()`` 为空，``copy_context`` 捕获当前
binding，``copy`` 是 shallow copy。``run`` 临时把指定 Context 压入当前 thread stack；
调用中的 set 留在该 Context，返回后恢复调用者 Context，同一 object 不能递归或并发进入。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.contextvars.Context python.contextvars.Context-empty
# polyglot-covers: python.contextvars.Context-mapping
# polyglot-covers: python.contextvars.Context.__contains__
# polyglot-covers: python.contextvars.Context.__getitem__
# polyglot-covers: python.contextvars.Context.get python.contextvars.Context.__iter__
# polyglot-covers: python.contextvars.Context.keys python.contextvars.Context.values
# polyglot-covers: python.contextvars.Context.items python.contextvars.Context.__len__
# polyglot-covers: python.contextvars.copy_context
# polyglot-covers: python.contextvars.Context.copy-shallow
# polyglot-covers: python.contextvars.Context.run
# polyglot-covers: python.contextvars.Context-run-return-and-exception
# polyglot-covers: python.contextvars.Context-run-contained-mutations
# polyglot-covers: python.contextvars.Context-recursive-entry-error
# polyglot-covers: python.contextvars.Context-concurrent-entry-error

import contextvars
import threading

import pytest


REQUEST_ID = contextvars.ContextVar("mapping_request_id")
PAYLOAD = contextvars.ContextVar("mapping_payload")


def test_context_is_mapping_and_run_contains_binding_changes():
    """run 返回 callable 结果；离开后 current Context 不会自动看到 captured Context 的值。"""

    context = contextvars.Context()
    assert len(context) == 0
    assert REQUEST_ID not in context
    assert context.get(REQUEST_ID) is None
    assert context.get(REQUEST_ID, "fallback") == "fallback"
    with pytest.raises(KeyError):
        _ = context[REQUEST_ID]

    def bind(prefix, *, number):
        REQUEST_ID.set(f"{prefix}-{number}")
        return REQUEST_ID.get()

    assert context.run(bind, "req", number=42) == "req-42"
    assert context[REQUEST_ID] == "req-42"
    assert REQUEST_ID in context
    assert list(context) == [REQUEST_ID]
    assert context.keys() == [REQUEST_ID]
    assert context.values() == ["req-42"]
    assert context.items() == [(REQUEST_ID, "req-42")]
    with pytest.raises(LookupError):
        REQUEST_ID.get()


def test_copy_context_captures_current_bindings_and_copy_is_shallow():
    """Context copy 复制 mapping，不深拷贝 value；之后重新绑定只改变目标 Context。"""

    payload = []
    container = {}

    def capture():
        PAYLOAD.set(payload)
        container["captured"] = contextvars.copy_context()

    contextvars.Context().run(capture)
    captured = container["captured"]
    cloned = captured.copy()

    assert captured[PAYLOAD] is payload
    assert cloned[PAYLOAD] is payload
    payload.append("shared-mutation")
    assert captured[PAYLOAD] == ["shared-mutation"]

    replacement = ["replacement"]
    cloned.run(PAYLOAD.set, replacement)
    assert cloned[PAYLOAD] is replacement
    assert captured[PAYLOAD] is payload


def test_context_run_propagates_exception_but_still_restores_caller_context():
    """异常不被包装；Context stack 的 pop 仍像 finally 一样执行。"""

    context = contextvars.Context()

    def fail():
        REQUEST_ID.set("inside-failure")
        raise LookupError("failed inside context")

    with pytest.raises(LookupError, match="failed inside context"):
        context.run(fail)

    assert context[REQUEST_ID] == "inside-failure"
    with pytest.raises(LookupError):
        REQUEST_ID.get()


def test_same_context_cannot_be_entered_recursively():
    """递归 run 同一 object 会混淆 stack entry，因而在 inner callable 前抛 RuntimeError。"""

    context = contextvars.Context()

    with pytest.raises(RuntimeError, match="already entered"):
        context.run(lambda: context.run(lambda: None))


def test_same_context_cannot_be_entered_by_two_threads_at_once():
    """Event 保持 worker 位于 Context.run 中，main 的并发 run 确定失败而无需 sleep。"""

    context = contextvars.Context()
    entered = threading.Event()
    release = threading.Event()

    def hold_context():
        entered.set()
        assert release.wait(timeout=2)

    thread = threading.Thread(target=context.run, args=(hold_context,))
    thread.start()
    assert entered.wait(timeout=2)

    try:
        with pytest.raises(RuntimeError, match="already entered"):
            context.run(lambda: None)
    finally:
        release.set()
        thread.join(timeout=2)

    assert thread.is_alive() is False
    assert context.run(lambda: "re-entered after exit") == "re-entered after exit"
