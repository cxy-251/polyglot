"""289｜手工 event loop 的获取、run/stop、关闭与 batch boundary。

应用入口优先 asyncio.run；framework 才常手工 new/set/run/close。get_running_loop 只在 coroutine
或 callback 内有效。run_until_complete 会把 coroutine 包成 Task。run_forever 遇 stop 时完成
当前 callback batch，但 batch 内新排入的 callback 留到下一次 run。close 不可逆但可重复调用。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.get_running_loop
# polyglot-covers: python.asyncio.get-running-loop-outside-error
# polyglot-covers: python.asyncio.get_event_loop
# polyglot-covers: python.asyncio.set_event_loop
# polyglot-covers: python.asyncio.new_event_loop
# polyglot-covers: python.asyncio.loop.run_until_complete
# polyglot-covers: python.asyncio.run-until-complete-wraps-coroutine
# polyglot-covers: python.asyncio.loop.run_forever
# polyglot-covers: python.asyncio.loop.stop
# polyglot-covers: python.asyncio.loop.is_running
# polyglot-covers: python.asyncio.loop.is_closed
# polyglot-covers: python.asyncio.loop.close
# polyglot-covers: python.asyncio.loop-close-idempotent-irreversible
# polyglot-covers: python.asyncio.run-forever-current-batch-boundary

import asyncio

import pytest


def test_new_set_and_run_until_complete_bind_the_running_loop():
    with pytest.raises(RuntimeError, match="no running event loop"):
        asyncio.get_running_loop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def main():
        assert asyncio.get_running_loop() is loop
        assert asyncio.get_event_loop() is loop
        assert loop.is_running() is True
        return asyncio.current_task()

    try:
        task = loop.run_until_complete(main())
        assert isinstance(task, asyncio.Task)
        assert loop.is_running() is False
        assert loop.is_closed() is False
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    assert loop.is_closed() is True


def test_stop_finishes_current_callback_batch_and_defers_new_callbacks():
    loop = asyncio.new_event_loop()
    calls = []

    def first_callback():
        calls.append("first")
        loop.call_soon(calls.append, "next batch")
        loop.stop()

    try:
        loop.call_soon(first_callback)
        loop.run_forever()
        assert calls == ["first"]

        loop.call_soon(loop.stop)
        loop.run_forever()
        assert calls == ["first", "next batch"]
    finally:
        loop.close()


def test_close_discards_pending_callbacks_and_is_idempotent_but_irreversible():
    loop = asyncio.new_event_loop()
    calls = []
    loop.call_soon(calls.append, "must not run")

    loop.close()
    assert calls == []
    assert loop.is_closed() is True
    assert loop.close() is None

    with pytest.raises(RuntimeError, match="Event loop is closed"):
        loop.call_soon(calls.append, "too late")
