"""229｜``contextvars.ContextVar`` lookup precedence、Token 与 reset discipline。

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


REQUEST_ID = contextvars.ContextVar("request_id")
THEME = contextvars.ContextVar("theme", default="system")
OTHER = contextvars.ContextVar("other")


def test_get_fallback_precedence_and_read_only_name():
    """call default 只在没有 binding 时优先于 constructor default；set 后 binding 最优先。"""

    def scenario():
        assert REQUEST_ID.name == "request_id"
        assert REQUEST_ID.get("anonymous") == "anonymous"
        with pytest.raises(LookupError):
            REQUEST_ID.get()

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
        token = REQUEST_ID.set("req-42")

        with pytest.raises(ValueError, match="different ContextVar"):
            OTHER.reset(token)
        REQUEST_ID.reset(token)
        with pytest.raises(RuntimeError, match="has already been used once"):
            REQUEST_ID.reset(token)

    contextvars.Context().run(scenario)


def test_python_310_token_does_not_implement_context_manager_protocol():
    """``with var.set(...)`` 是更高版本功能；3.10 必须 try/finally + reset。"""

    def scenario():
        token = REQUEST_ID.set("req-7")
        try:
            with pytest.raises(TypeError, match="context manager"):
                with token:
                    pass
        finally:
            REQUEST_ID.reset(token)

    contextvars.Context().run(scenario)
