"""291｜asyncio Future eventual-result state、重复 await 与 callback scheduling。

Future 是 callback API 到 async/await 的低层桥。pending 时同步 result/exception 不等待而抛
InvalidStateError；set_result/set_exception 完成单次赋值。Future 可重复 await 同一结果。
done callback 总由 loop.call_soon 排队，即使登记时已 done，也不会在调用栈内同步重入。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.Future
# polyglot-covers: python.asyncio.loop.create_future
# polyglot-covers: python.asyncio.Future.get_loop
# polyglot-covers: python.asyncio.Future.done
# polyglot-covers: python.asyncio.Future.result
# polyglot-covers: python.asyncio.Future.exception
# polyglot-covers: python.asyncio.Future.set_result
# polyglot-covers: python.asyncio.Future.set_exception
# polyglot-covers: python.asyncio.Future-multiple-awaits
# polyglot-covers: python.asyncio.Future-single-assignment
# polyglot-covers: python.asyncio.Future.add_done_callback
# polyglot-covers: python.asyncio.Future.remove_done_callback
# polyglot-covers: python.asyncio.Future-callback-call-soon
# polyglot-covers: python.asyncio.Future-callback-context
# polyglot-covers: python.asyncio.Future.cancel
# polyglot-covers: python.asyncio.Future.cancelled
# polyglot-covers: python.asyncio.Future-cancel-message

import asyncio
import contextvars

import pytest


CALLBACK_CONTEXT = contextvars.ContextVar("future_callback_context", default="missing")


async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_future_result_is_single_assignment_reusable_awaitable():
    async def scenario():
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        assert asyncio.isfuture(future) is True
        assert future.get_loop() is loop
        assert future.done() is False
        with pytest.raises(asyncio.InvalidStateError):
            future.result()
        with pytest.raises(asyncio.InvalidStateError):
            future.exception()

        loop.call_soon(future.set_result, 42)
        assert await future == 42
        assert await future == 42
        assert future.result() == 42
        assert future.exception() is None
        with pytest.raises(asyncio.InvalidStateError):
            future.set_result(43)
        with pytest.raises(asyncio.InvalidStateError):
            future.set_exception(LookupError())

    asyncio.run(scenario())

def test_exception_future_reraises_same_object_from_result():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        error = LookupError("missing")
        future.set_exception(error)

        assert future.exception() is error
        with pytest.raises(LookupError, match="missing") as raised:
            await future
        assert raised.value is error

    asyncio.run(scenario())


def test_callbacks_are_scheduled_and_can_select_or_remove_context():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        calls = []

        def callback(completed):
            calls.append((completed.result(), CALLBACK_CONTEXT.get()))

        removed_context = contextvars.copy_context()
        removed_context.run(CALLBACK_CONTEXT.set, "removed")
        future.add_done_callback(callback, context=removed_context)
        assert future.remove_done_callback(callback) == 1

        callback_context = contextvars.copy_context()
        callback_context.run(CALLBACK_CONTEXT.set, "selected")
        future.set_result("done")
        future.add_done_callback(callback, context=callback_context)
        assert calls == []

        await _next_loop_turn()
        assert calls == [("done", "selected")]

    asyncio.run(scenario())


def test_cancel_is_terminal_and_preserves_message_for_result_and_exception():
    async def scenario():
        future = asyncio.get_running_loop().create_future()
        assert future.cancel("not needed") is True
        assert future.cancelled() is True
        assert future.done() is True
        assert future.cancel() is False

        with pytest.raises(asyncio.CancelledError) as result_error:
            future.result()
        assert result_error.value.args == ("not needed",)
        with pytest.raises(asyncio.CancelledError):
            future.exception()

    asyncio.run(scenario())
