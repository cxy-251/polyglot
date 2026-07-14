"""269｜asyncio coroutine/awaitable、顶层 ``run`` 与零延迟让权。

调用 async def 只创建 coroutine object，不会自动执行。await 在当前 Task 中驱动它，
create_task 才把它并发调度。asyncio.run 为顶层入口创建并最终关闭新 event loop，还会清理
未显式关闭的 async generator；运行中的同线程 event loop 内不能再次调用它。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio-coroutine-object-not-scheduled
# polyglot-covers: python.asyncio-awaitable-coroutine
# polyglot-covers: python.asyncio.iscoroutine
# polyglot-covers: python.asyncio.iscoroutinefunction
# polyglot-covers: python.asyncio.run
# polyglot-covers: python.asyncio.run-return-value
# polyglot-covers: python.asyncio.run-new-loop-closed
# polyglot-covers: python.asyncio.run-debug
# polyglot-covers: python.asyncio.run-nested-loop-error
# polyglot-covers: python.asyncio.run-shutdown-async-generators
# polyglot-covers: python.asyncio.sleep
# polyglot-covers: python.asyncio.sleep-result
# polyglot-covers: python.asyncio.sleep-zero-yield

import asyncio
import inspect

import pytest


def test_calling_async_function_only_constructs_a_coroutine_object():
    calls = []

    async def compute():
        calls.append("ran")
        return 42

    coroutine = compute()
    try:
        assert calls == []
        assert asyncio.iscoroutinefunction(compute) is True
        assert asyncio.iscoroutine(coroutine) is True
        assert inspect.isawaitable(coroutine) is True
    finally:
        # 未 await 的 native coroutine 必须显式 close，否则 GC 会报告 RuntimeWarning。
        coroutine.close()


def test_run_returns_result_uses_debug_mode_and_closes_its_new_loop():
    async def main():
        loop = asyncio.get_running_loop()
        yielded = await asyncio.sleep(0, result="after-yield")
        return loop, loop.get_debug(), yielded

    loop, debug, yielded = asyncio.run(main(), debug=True)

    assert debug is True
    assert yielded == "after-yield"
    assert loop.is_closed() is True


def test_run_cannot_be_nested_in_an_already_running_loop():
    async def inner():
        return "inner"

    async def outer():
        coroutine = inner()
        try:
            with pytest.raises(RuntimeError, match="cannot be called from a running event loop"):
                asyncio.run(coroutine)
        finally:
            coroutine.close()

    asyncio.run(outer())


def test_run_finalizes_an_async_generator_left_open_by_main():
    finalized = []

    async def values():
        try:
            yield "first"
            yield "second"
        finally:
            finalized.append("closed")

    async def main():
        generator = values()
        assert await generator.__anext__() == "first"
        # 不调用 aclose；asyncio.run 的 shutdown_asyncgens 阶段负责执行 finally。

    asyncio.run(main())

    assert finalized == ["closed"]
