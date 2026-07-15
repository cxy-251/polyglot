"""089｜``contextvars.ContextVar`` lookup precedence、Token 与 reset discipline。

ContextVar 先查当前 Context binding，再按 ``get(call_default)``、variable default、
LookupError 的顺序 fallback。``set`` 返回只属于该 variable/Context/调用的一次性 Token；
按嵌套顺序 reset 可恢复旧 binding。Python 3.10 Token 还不是 context manager。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.contextvars.ContextVar python.contextvars.ContextVar.name
# polyglot-covers: python.contextvars.ContextVar-default
# polyglot-covers: python.contextvars.ContextVar.get
# polyglot-covers: python.contextvars.ContextVar-get-call-default-precedence
# polyglot-covers: python.contextvars.ContextVar-get-lookuperror
# polyglot-covers: python.contextvars.ContextVar.set
# polyglot-covers: python.contextvars.ContextVar.reset
# polyglot-covers: python.contextvars.Token python.contextvars.Token.var
# polyglot-covers: python.contextvars.Token.old_value python.contextvars.Token.MISSING
# polyglot-covers: python.contextvars.Token-single-use
# polyglot-covers: python.contextvars.Token-wrong-variable
# polyglot-covers: python.contextvars.Token-not-context-manager-in-3.10




import contextvars
import pytest
import threading
import asyncio
import queue

REQUEST_ID_229 = contextvars.ContextVar("request_id")
THEME = contextvars.ContextVar("theme", default="system")
OTHER = contextvars.ContextVar("other")


def test_get_fallback_precedence_and_read_only_name():
    """call default 只在没有 binding 时优先于 constructor default；set 后 binding 最优先。"""

    def scenario():
        assert REQUEST_ID_229.name == "request_id"
        assert REQUEST_ID_229.get("anonymous") == "anonymous"
        with pytest.raises(LookupError):
            REQUEST_ID_229.get()

        assert THEME.get() == "system"
        assert THEME.get("call-default") == "call-default"
        token = THEME.set("dark")
        try:
            assert THEME.get() == "dark"
            assert THEME.get("ignored") == "dark"
        finally:
            THEME.reset(token)

        with pytest.raises(AttributeError):
            THEME.name = "renamed"

    contextvars.Context().run(scenario)


def test_nested_tokens_restore_previous_binding_in_reverse_order():
    """variable default 不是 Context binding，因此第一次 token.old_value 仍是 MISSING。"""

    def scenario():
        outer = THEME.set("outer")
        inner = THEME.set("inner")

        assert outer.var is THEME
        assert outer.old_value is contextvars.Token.MISSING
        assert inner.old_value == "outer"
        assert THEME.get() == "inner"

        THEME.reset(inner)
        assert THEME.get() == "outer"
        THEME.reset(outer)
        assert THEME.get() == "system"

    contextvars.Context().run(scenario)


def test_token_is_single_use_and_bound_to_creating_variable():
    """用错 variable 与重复 reset 都立即失败，避免悄悄恢复不相关状态。"""

    def scenario():
        token = REQUEST_ID_229.set("req-42")

        with pytest.raises(ValueError, match="different ContextVar"):
            OTHER.reset(token)
        REQUEST_ID_229.reset(token)
        with pytest.raises(RuntimeError, match="has already been used once"):
            REQUEST_ID_229.reset(token)

    contextvars.Context().run(scenario)


def test_python_310_token_does_not_implement_context_manager_protocol():
    """``with var.set(...)`` 是更高版本功能；3.10 必须 try/finally + reset。"""

    def scenario():
        token = REQUEST_ID_229.set("req-7")
        try:
            with pytest.raises(AttributeError, match="__enter__"):
                with token:
                    pass
        finally:
            REQUEST_ID_229.reset(token)

    contextvars.Context().run(scenario)


# ``contextvars.Context`` mapping、copy、``run`` isolation 与 re-entry guard。
#
# Context 是 ContextVar→value 的 Mapping。``Context()`` 为空，``copy_context`` 捕获当前
# binding，``copy`` 是 shallow copy。``run`` 临时把指定 Context 压入当前 thread stack；
# 调用中的 set 留在该 Context，返回后恢复调用者 Context，同一 object 不能递归或并发进入。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

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




REQUEST_ID_230 = contextvars.ContextVar("mapping_request_id")
PAYLOAD = contextvars.ContextVar("mapping_payload")


def test_context_is_mapping_and_run_contains_binding_changes():
    """run 返回 callable 结果；离开后 current Context 不会自动看到 captured Context 的值。"""

    context = contextvars.Context()
    assert len(context) == 0
    assert REQUEST_ID_230 not in context
    assert context.get(REQUEST_ID_230) is None
    assert context.get(REQUEST_ID_230, "fallback") == "fallback"
    with pytest.raises(KeyError):
        _ = context[REQUEST_ID_230]

    def bind(prefix, *, number):
        REQUEST_ID_230.set(f"{prefix}-{number}")
        return REQUEST_ID_230.get()

    assert context.run(bind, "req", number=42) == "req-42"
    assert context[REQUEST_ID_230] == "req-42"
    assert REQUEST_ID_230 in context
    assert list(context) == [REQUEST_ID_230]
    assert list(context.keys()) == [REQUEST_ID_230]
    assert list(context.values()) == ["req-42"]
    assert list(context.items()) == [(REQUEST_ID_230, "req-42")]
    with pytest.raises(LookupError):
        REQUEST_ID_230.get()


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
        REQUEST_ID_230.set("inside-failure")
        raise LookupError("failed inside context")

    with pytest.raises(LookupError, match="failed inside context"):
        context.run(fail)

    assert context[REQUEST_ID_230] == "inside-failure"
    with pytest.raises(LookupError):
        REQUEST_ID_230.get()


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


# Context 的 thread top-level isolation 与 ``asyncio.Task`` propagation。
#
# 每个 OS thread 有独立的 top-level Context，新 thread 不自动继承创建者 binding；需要时
# 显式把 ``copy_context().run`` 作为 target。asyncio 则在 Task 创建时自动复制 current
# Context，使 sibling tasks 可继承共同起点又各自修改，不发生 request-local 状态串线。
#
# 这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。

# polyglot-covers: python.contextvars.thread-top-level-context
# polyglot-covers: python.contextvars.new-thread-does-not-inherit-context
# polyglot-covers: python.contextvars.copy-context-to-thread
# polyglot-covers: python.contextvars.asyncio-native-support
# polyglot-covers: python.contextvars.asyncio-task-context-capture
# polyglot-covers: python.contextvars.asyncio-task-creation-snapshot
# polyglot-covers: python.contextvars.asyncio-sibling-task-isolation



REQUEST_ID_231 = contextvars.ContextVar("async_request_id")


def test_new_thread_is_empty_unless_captured_context_is_run_explicitly():
    """同一 Context object 只能单点进入，但 copy 可安全交给此时尚未进入它的 worker。"""

    results = queue.Queue()

    def scenario():
        REQUEST_ID_231.set("main-request")
        captured = contextvars.copy_context()

        plain = threading.Thread(
            target=lambda: results.put(("plain", REQUEST_ID_231.get("missing")))
        )
        propagated = threading.Thread(
            target=captured.run,
            args=(lambda: results.put(("propagated", REQUEST_ID_231.get())),),
        )
        plain.start()
        propagated.start()
        plain.join()
        propagated.join()

    contextvars.Context().run(scenario)

    assert sorted([results.get_nowait(), results.get_nowait()]) == [
        ("plain", "missing"),
        ("propagated", "main-request"),
    ]


def test_task_captures_context_at_creation_not_first_execution():
    """parent 在 create_task 后重新绑定；尚未放行的 child 仍看到创建瞬间的值。"""

    async def scenario():
        gate = asyncio.Event()
        REQUEST_ID_231.set("captured-at-create")

        async def child():
            await gate.wait()
            return REQUEST_ID_231.get()

        task = asyncio.create_task(child())
        REQUEST_ID_231.set("parent-after-create")
        gate.set()

        return await task, REQUEST_ID_231.get()

    result = contextvars.Context().run(lambda: asyncio.run(scenario()))

    assert result == ("captured-at-create", "parent-after-create")


def test_sibling_tasks_mutate_independent_context_copies():
    """两个 Task 都继承 parent，随后各自 set；Event 让两者都写完再读取。"""

    async def scenario():
        REQUEST_ID_231.set("parent")
        ready = []
        both_ready = asyncio.Event()

        async def child(value):
            assert REQUEST_ID_231.get() == "parent"
            REQUEST_ID_231.set(value)
            ready.append(value)
            if len(ready) == 2:
                both_ready.set()
            await both_ready.wait()
            return REQUEST_ID_231.get()

        results = await asyncio.gather(child("left"), child("right"))
        return results, REQUEST_ID_231.get()

    results, parent_value = contextvars.Context().run(
        lambda: asyncio.run(scenario())
    )

    assert results == ["left", "right"]
    assert parent_value == "parent"
