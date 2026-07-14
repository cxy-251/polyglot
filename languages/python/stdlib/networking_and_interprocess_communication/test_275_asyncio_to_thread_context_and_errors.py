"""275｜``asyncio.to_thread`` 延迟提交、参数、Context propagation 与异常。

to_thread 返回 coroutine；直到 await 才把 callable 提交到 default thread pool。它复制当前
contextvars.Context，使 request-local binding 对 worker 可见，但 worker 的重新绑定不回写
caller。CPython GIL 下它主要隔离阻塞 I/O，不应被误当作纯 Python CPU parallelism。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.to_thread
# polyglot-covers: python.asyncio.to-thread-lazy-coroutine
# polyglot-covers: python.asyncio.to-thread-args-kwargs
# polyglot-covers: python.asyncio.to-thread-return-value
# polyglot-covers: python.asyncio.to-thread-different-os-thread
# polyglot-covers: python.asyncio.to-thread-contextvars-propagation
# polyglot-covers: python.asyncio.to-thread-context-mutation-isolated
# polyglot-covers: python.asyncio.to-thread-exception-propagation
# polyglot-covers: python.asyncio.to-thread-gil-io-bound-guidance

import asyncio
import contextvars
import threading

import pytest


REQUEST_ID = contextvars.ContextVar("asyncio_to_thread_request_id")


def test_to_thread_is_lazy_passes_arguments_and_propagates_context_copy():
    calls = []

    def worker(value, *, multiplier):
        calls.append("called")
        inherited = REQUEST_ID.get()
        REQUEST_ID.set("worker-only")
        return value * multiplier, inherited, threading.get_ident()

    async def scenario():
        REQUEST_ID.set("request-42")
        caller_ident = threading.get_ident()
        awaitable = asyncio.to_thread(worker, 6, multiplier=7)
        assert calls == []

        result, inherited, worker_ident = await awaitable
        return result, inherited, worker_ident, caller_ident, REQUEST_ID.get()

    outcome = contextvars.Context().run(lambda: asyncio.run(scenario()))

    result, inherited, worker_ident, caller_ident, caller_context = outcome
    assert calls == ["called"]
    assert result == 42
    assert inherited == "request-42"
    assert worker_ident != caller_ident
    assert caller_context == "request-42"


def test_to_thread_reraises_worker_exception_at_await_boundary():
    def fail(message):
        raise LookupError(message)

    async def scenario():
        with pytest.raises(LookupError, match="worker failed"):
            await asyncio.to_thread(fail, "worker failed")

    asyncio.run(scenario())
