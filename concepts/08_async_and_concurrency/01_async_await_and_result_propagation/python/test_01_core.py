"""异步等待与结果传播。

共同问题：异步函数调用何时开始执行；await 如何取得结果；失败如何传播；
多个结果如何组合。
"""

# polyglot-family: async_and_concurrency
# polyglot-concept: async_await_and_result_propagation
# polyglot-related: languages/python/language/test_015_async_functions_and_protocols.py

import asyncio

import pytest


def test_async_function_call_creates_lazy_coroutine():
    events = []

    async def work():
        events.append("run")
        return 42

    coroutine = work()
    assert events == []
    assert asyncio.run(coroutine) == 42
    assert events == ["run"]


def test_await_returns_value_and_propagates_exception():
    async def fail():
        raise ValueError("failed")

    async def observe():
        with pytest.raises(ValueError, match="failed"):
            await fail()

    asyncio.run(observe())


def test_gather_preserves_input_result_order():
    async def value(number):
        await asyncio.sleep(0)
        return number

    async def collect():
        return await asyncio.gather(value(2), value(1))

    assert asyncio.run(collect()) == [2, 1]


def test_coroutine_object_cannot_be_awaited_twice_after_completion():
    async def value():
        return 1

    coroutine = value()
    assert asyncio.run(coroutine) == 1

    with pytest.raises(RuntimeError, match="cannot reuse"):
        asyncio.run(coroutine)
