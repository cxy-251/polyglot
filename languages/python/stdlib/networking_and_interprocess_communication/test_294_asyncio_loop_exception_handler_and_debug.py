"""294｜event loop exception context、custom handler delegation 与 debug flag。

callback 抛出的异常不能在 await site 直接捕获，loop 会把 message/exception/handle 等信息
放入 extensible context dict 交给 exception handler。custom handler 可处理或显式委托
default_exception_handler。set_exception_handler(None) 恢复默认；debug flag 可运行时切换。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.loop.set_exception_handler
# polyglot-covers: python.asyncio.loop.get_exception_handler
# polyglot-covers: python.asyncio.loop.call_exception_handler
# polyglot-covers: python.asyncio.loop.default_exception_handler
# polyglot-covers: python.asyncio.exception-handler-loop-context-signature
# polyglot-covers: python.asyncio.exception-handler-context-message
# polyglot-covers: python.asyncio.exception-handler-context-exception
# polyglot-covers: python.asyncio.exception-handler-context-handle
# polyglot-covers: python.asyncio.exception-handler-extensible-context
# polyglot-covers: python.asyncio.loop.get_debug
# polyglot-covers: python.asyncio.loop.set_debug

import asyncio


async def _next_loop_turn():
    loop = asyncio.get_running_loop()
    marker = loop.create_future()
    loop.call_soon(marker.set_result, None)
    await marker


def test_explicit_exception_context_reaches_custom_handler_unchanged():
    async def scenario():
        loop = asyncio.get_running_loop()
        received = []

        def handler(received_loop, context):
            received.append((received_loop, context))

        loop.set_exception_handler(handler)
        assert loop.get_exception_handler() is handler
        context = {
            "message": "educational failure",
            "exception": LookupError("missing"),
            "custom-key": 42,
        }
        loop.call_exception_handler(context)

        assert received == [(loop, context)]
        loop.set_exception_handler(None)
        assert loop.get_exception_handler() is None

    asyncio.run(scenario())

def test_callback_exception_supplies_exception_and_handle_to_handler():
    async def scenario():
        loop = asyncio.get_running_loop()
        contexts = []
        loop.set_exception_handler(lambda _, context: contexts.append(context))

        def fail():
            raise ValueError("callback failed")

        handle = loop.call_soon(fail)
        await _next_loop_turn()

        assert len(contexts) == 1
        assert "Exception in callback" in contexts[0]["message"]
        assert isinstance(contexts[0]["exception"], ValueError)
        assert contexts[0]["handle"] is handle

    asyncio.run(scenario())


def test_loop_debug_flag_can_be_toggled_explicitly():
    async def scenario():
        loop = asyncio.get_running_loop()
        original = loop.get_debug()
        loop.set_debug(not original)
        assert loop.get_debug() is (not original)
        loop.set_debug(original)
        assert loop.get_debug() is original

    asyncio.run(scenario())
