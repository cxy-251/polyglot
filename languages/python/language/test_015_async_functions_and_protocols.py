"""015｜coroutine、异步迭代/生成器与异步上下文协议的可执行示例。

调用 ``async def`` 只创建 coroutine；事件循环推进它时函数体才执行。
``await`` 使用 ``__await__``，``async for`` 使用 ``__aiter__`` / ``__anext__``
并由 ``StopAsyncIteration`` 终止，``async with`` 则使用 ``__aenter__`` /
``__aexit__``。异步生成器同时支持 ``asend``、``athrow`` 和 ``aclose``。

测试保持普通 pytest 函数，由标准库 ``asyncio.run`` 驱动，不要求 pytest 的
异步插件。内容基于 Python 3.10 Coroutine、Async for/with 和 Asynchronous
generator 协议。
"""

# polyglot-covers: python.syntax.async-def python.expression.await
# polyglot-covers: python.builtin.aiter python.builtin.anext
# polyglot-covers: python.protocol.__await__ python.protocol.__aiter__
# polyglot-covers: python.protocol.__anext__ python.exception.StopAsyncIteration
# polyglot-covers: python.statement.async-for python.statement.async-for-else
# polyglot-covers: python.statement.async-with
# polyglot-covers: python.protocol.__aenter__ python.protocol.__aexit__
# polyglot-covers: python.expression.async-generator
# polyglot-covers: python.expression.async-generator-expression
# polyglot-covers: python.async-generator.asend python.async-generator.athrow
# polyglot-covers: python.async-generator.aclose

import asyncio

import pytest


def test_calling_async_function_is_lazy_until_coroutine_runs():
    """调用 coroutine function 不执行函数体，``asyncio.run`` 才推进它。"""

    events = []

    async def compute(value):
        events.append(("started", value))
        await asyncio.sleep(0)
        events.append(("resumed", value))
        return value * 2

    coroutine = compute(21)

    assert events == []
    assert asyncio.run(coroutine) == 42
    assert events == [("started", 21), ("resumed", 21)]

    # 常见坑：只写 compute(21) 会得到 coroutine object，而不是 42；如果随后
    # 既不 await 也不调度它，函数体和清理逻辑都不会运行。


def test_coroutine_exception_propagates_to_the_awaiter():
    """async 函数异常通过 await 边界传播，与普通调用链一致。"""

    async def fail():
        await asyncio.sleep(0)
        raise ValueError("invalid async result")

    with pytest.raises(ValueError, match="invalid async result"):
        asyncio.run(fail())


def test_completed_coroutine_object_cannot_be_awaited_twice():
    """coroutine object 是一次性执行状态，不是可重复调用的函数。"""

    async def answer():
        return 42

    async def scenario():
        coroutine = answer()
        first = await coroutine

        with pytest.raises(RuntimeError, match="cannot reuse already awaited coroutine"):
            await coroutine

        return first

    assert asyncio.run(scenario()) == 42

    # 需要重做操作时应再次调用 answer() 创建新 coroutine，不能缓存并复用已经
    # 完成的 coroutine object。


class ImmediateAwaitable:
    def __init__(self, value):
        self.value = value
        self.events = []

    def __await__(self):
        self.events.append("__await__")
        if False:
            # 含 yield 让该方法成为 generator，从而返回 iterator；分支不执行。
            yield None
        return self.value


def test_await_delegates_to_an_iterator_returned_by_await_method():
    """自定义 awaitable 的 ``__await__`` 必须返回 iterator，并以 return 给值。"""

    value = ImmediateAwaitable("ready")

    async def receive():
        return await value

    assert asyncio.run(receive()) == "ready"
    assert value.events == ["__await__"]


def test_await_method_returning_a_plain_value_violates_the_protocol():
    """``__await__`` 不能直接 return 最终普通值；调用结果自身必须是 iterator。"""

    class BadAwaitable:
        def __await__(self):
            return 42

    async def receive():
        return await BadAwaitable()

    with pytest.raises(TypeError, match="__await__.*iterator"):
        asyncio.run(receive())


class AsyncRangeIterator:
    def __init__(self, start, stop):
        self.current = start
        self.stop = stop

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.current >= self.stop:
            raise StopAsyncIteration
        value = self.current
        self.current += 1
        await asyncio.sleep(0)
        return value


class AsyncRange:
    """每次异步迭代都创建独立 iterator 的 async iterable。"""

    def __init__(self, start, stop):
        self.start = start
        self.stop = stop

    def __aiter__(self):
        return AsyncRangeIterator(self.start, self.stop)


def test_async_iterable_creates_iterators_and_anext_awaits_each_item():
    """``aiter`` 取得 async iterator，``anext`` 返回要 await 的下一项。"""

    async def scenario():
        values = AsyncRange(1, 4)
        first = aiter(values)
        second = aiter(values)

        assert first is not second
        assert aiter(first) is first
        assert await anext(first) == 1
        assert await anext(first) == 2
        assert await anext(second) == 1

        remaining = []
        async for value in first:
            remaining.append(value)
        return remaining

    assert asyncio.run(scenario()) == [3]


def test_anext_default_handles_stop_async_iteration():
    """Python 3.10 的 ``anext(iterator, default)`` 可把异步耗尽变成默认值。"""

    async def scenario():
        iterator = AsyncRangeIterator(0, 1)
        assert await anext(iterator) == 0
        assert await anext(iterator, "finished") == "finished"

        with pytest.raises(StopAsyncIteration):
            await anext(iterator)

    asyncio.run(scenario())


def test_async_for_else_depends_on_break_just_like_synchronous_for():
    """async for 的 else 只在正常耗尽、没有 break 时执行。"""

    async def search(target):
        events = []
        async for value in AsyncRange(1, 4):
            if value == target:
                events.append(("found", value))
                break
        else:
            events.append("not-found")
        return events

    assert asyncio.run(search(2)) == [("found", 2)]
    assert asyncio.run(search(9)) == ["not-found"]


def test_async_for_rejects_a_plain_synchronous_iterable():
    """同步 iterable 不会被 async for 自动包装。"""

    async def consume():
        async for value in [1, 2, 3]:
            return value

    with pytest.raises(TypeError):
        asyncio.run(consume())


def test_python_310_aiter_must_return_async_iterator_not_awaitable():
    """Python 3.10 的 ``__aiter__`` 必须直接返回具有 ``__anext__`` 的对象。"""

    class AwaitableButNotAsyncIterator:
        def __await__(self):
            if False:
                yield None
            return self

    class IncorrectAsyncIterable:
        def __aiter__(self):
            return AwaitableButNotAsyncIterator()

    async def consume():
        async for value in IncorrectAsyncIterable():
            return value

    with pytest.raises(TypeError, match="does not implement __anext__"):
        asyncio.run(consume())

    # 早期 Python 3.5 曾短暂允许 __aiter__ 返回 awaitable；3.10 基线要求直接
    # 返回 async iterator，迁移旧示例时不能保留 async def __aiter__ 写法。


def test_anext_method_itself_must_return_an_awaitable():
    """``__anext__`` 可用普通 def 实现，但每次结果仍必须可 await。"""

    class BadAsyncIterator:
        def __aiter__(self):
            return self

        def __anext__(self):
            return 1

    async def consume():
        async for value in BadAsyncIterator():
            return value

    with pytest.raises(TypeError, match="invalid object from __anext__"):
        asyncio.run(consume())


class AsyncRecordingContext:
    def __init__(self, name, events, suppress=False):
        self.name = name
        self.events = events
        self.suppress = suppress
        self.exit_arguments = None

    async def __aenter__(self):
        self.events.append(("enter", self.name))
        await asyncio.sleep(0)
        return f"resource:{self.name}"

    async def __aexit__(self, exception_type, exception, traceback):
        self.events.append(("exit", self.name))
        self.exit_arguments = (exception_type, exception, traceback)
        await asyncio.sleep(0)
        return self.suppress


def test_async_with_awaits_enter_binds_resource_and_awaits_exit():
    """async with 与同步协议结构相同，但 enter/exit 的结果都要 await。"""

    async def scenario():
        events = []
        manager = AsyncRecordingContext("database", events)

        async with manager as resource:
            events.append(("body", resource))

        assert manager.exit_arguments == (None, None, None)
        return events

    assert asyncio.run(scenario()) == [
        ("enter", "database"),
        ("body", "resource:database"),
        ("exit", "database"),
    ]


def test_async_exit_receives_and_can_selectively_suppress_exception():
    """异步 exit 的真值抑制语义与同步 ``__exit__`` 一致。"""

    async def scenario():
        events = []
        manager = AsyncRecordingContext("transaction", events, suppress=True)

        async with manager:
            raise ValueError("rolled back")

        events.append("continued")
        assert manager.exit_arguments[0] is ValueError
        return events

    assert asyncio.run(scenario()) == [
        ("enter", "transaction"),
        ("exit", "transaction"),
        "continued",
    ]


def test_multiple_async_managers_exit_in_reverse_order():
    """多个 async manager 从左到右进入、从右到左退出。"""

    async def scenario():
        events = []
        first = AsyncRecordingContext("first", events)
        second = AsyncRecordingContext("second", events)

        async with first, second:
            events.append("body")

        return events

    assert asyncio.run(scenario()) == [
        ("enter", "first"),
        ("enter", "second"),
        "body",
        ("exit", "second"),
        ("exit", "first"),
    ]


def test_async_with_rejects_sync_only_context_manager():
    """普通 ``__enter__`` / ``__exit__`` 不会自动满足异步上下文协议。"""

    class SyncOnly:
        def __enter__(self):
            return self

        def __exit__(self, exception_type, exception, traceback):
            return False

    async def scenario():
        async with SyncOnly():
            pass

    # 3.10 在查找缺失的异步协议入口时直接报告 AttributeError；后续版本把
    # 这类协议不匹配统一成了 TypeError。
    with pytest.raises(AttributeError, match="__aenter__"):
        asyncio.run(scenario())


def test_async_generator_is_lazy_and_yields_items_on_demand():
    """含 ``yield`` 的 async def 创建 async generator，调用时仍不执行函数体。"""

    events = []

    async def stages():
        events.append("started")
        yield "one"
        await asyncio.sleep(0)
        events.append("resumed")
        yield "two"
        events.append("finished")

    async def scenario():
        generator = stages()
        assert events == []
        assert generator.__aiter__() is generator
        assert await generator.__anext__() == "one"
        assert events == ["started"]

        remaining = [value async for value in generator]
        assert events == ["started", "resumed", "finished"]
        return remaining

    assert asyncio.run(scenario()) == ["two"]


def test_async_generator_expression_is_lazy_and_uses_async_for():
    """异步生成器表达式按需消费 async iterable。"""

    async def scenario():
        values = (value * 10 async for value in AsyncRange(1, 4))
        first = await anext(values)
        remaining = [value async for value in values]
        return first, remaining

    assert asyncio.run(scenario()) == (10, [20, 30])


def test_async_generator_asend_supplies_suspended_yield_value():
    """``asend`` 是异步生成器版 send，调用结果本身需要 await。"""

    async def receiver():
        received = yield "ready"
        yield f"received:{received}"

    async def scenario():
        generator = receiver()
        assert await anext(generator) == "ready"
        assert await generator.asend("payload") == "received:payload"

        with pytest.raises(StopAsyncIteration):
            await anext(generator)

    asyncio.run(scenario())


def test_async_generator_athrow_injects_exception_at_yield():
    """``athrow`` 可让异步生成器在暂停点捕获并处理异常。"""

    async def resilient():
        try:
            yield "ready"
        except ValueError as error:
            yield f"handled:{error}"

    async def scenario():
        generator = resilient()
        assert await anext(generator) == "ready"
        assert await generator.athrow(ValueError("bad")) == "handled:bad"

        with pytest.raises(StopAsyncIteration):
            await anext(generator)

    asyncio.run(scenario())


def test_async_generator_aclose_runs_generator_exit_cleanup():
    """``aclose`` 注入 ``GeneratorExit`` 并 await 清理完成。"""

    events = []

    async def managed_stream():
        try:
            events.append("opened")
            yield "item"
        except GeneratorExit:
            events.append("generator-exit")
            raise
        finally:
            await asyncio.sleep(0)
            events.append("closed")

    async def scenario():
        generator = managed_stream()
        assert await anext(generator) == "item"
        await generator.aclose()

        with pytest.raises(StopAsyncIteration):
            await anext(generator)

    asyncio.run(scenario())
    assert events == ["opened", "generator-exit", "closed"]

    # 管理外部资源的 async generator 应被完整消费或显式 aclose。依赖垃圾回收
    # 的最终化时机，会让连接和锁的释放变得不可预测。


def test_async_generator_cannot_return_a_value():
    """async generator 可用空 ``return`` 结束，但语法禁止携带返回值。"""

    source = """
async def broken():
    yield 1
    return 2
"""

    with pytest.raises(SyntaxError, match="return.*value.*async generator"):
        compile(source, "<async-generator-return>", "exec")
