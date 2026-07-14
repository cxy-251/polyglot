"""056｜异步 iterable、iterator 与 generator 的协议和安全关闭示例。

异步迭代把同步协议中的 ``iter``/``next`` 拆成 ``__aiter__`` 和返回 awaitable 的
``__anext__``。Python 3.10 的 ``aiter``/``anext`` 让这条隐式分派可以直接观察；
``AsyncGenerator`` 又在 iterator 基础上增加发送、异常注入和显式异步关闭。

这里的所有 awaitable 都会立即完成；native async generator 会被耗尽或显式
``aclose``。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.collections.abc.AsyncIterable python.async-iterable.primitive
# polyglot-covers: python.collections.abc.AsyncIterator python.async-iterator.primitive
# polyglot-covers: python.async-iterator.aiter-self python.async-iterator.one-shot
# polyglot-covers: python.async-iterable.reiterable python.builtin.aiter
# polyglot-covers: python.builtin.aiter-one-argument python.builtin.anext
# polyglot-covers: python.builtin.anext-default python.async-iterator.false-values
# polyglot-covers: python.async-for.protocol python.async-iterator.stop-async-iteration
# polyglot-covers: python.async-iterator.awaitable-result python.async-iterator.bad-result
# polyglot-covers: python.async-iterator.stop-iteration-pitfall python.aiter.python37-change
# polyglot-covers: python.async-abc.structural-recognition python.async-abc.semantic-boundary
# polyglot-covers: python.collections.abc.AsyncGenerator python.async-generator.function-object
# polyglot-covers: python.async-generator.builtin-registration python.async-generator.anext
# polyglot-covers: python.async-generator.asend python.async-generator.athrow
# polyglot-covers: python.async-generator.aclose python.async-generator.finally-cleanup
# polyglot-covers: python.async-generator.initial-asend python.async-generator.lazy-awaitable
# polyglot-covers: python.async-generator.abc-primitives python.async-generator.anext-mixin
# polyglot-covers: python.async-generator.aclose-mixin python.async-generator.close-normal
# polyglot-covers: python.async-generator.close-ignored-exit python.async-generator.cleanup-error
# polyglot-covers: python.async-generator.break-explicit-close python.async-abc.generic-alias

import asyncio
import inspect
from collections.abc import AsyncGenerator
from collections.abc import AsyncIterable
from collections.abc import AsyncIterator
from types import GenericAlias

import pytest


class SequenceAsyncIterator(AsyncIterator):
    """用内存 tuple 实现一次性异步 iterator，并记录 __anext__ 调用次数。"""

    def __init__(self, values):
        self._values = iter(tuple(values))
        self.anext_calls = 0

    async def __anext__(self):
        self.anext_calls += 1
        try:
            return next(self._values)
        except StopIteration:
            # StopIteration 不能穿出 coroutine；异步迭代的终止哨兵是独立异常。
            raise StopAsyncIteration from None


class ReplayableAsyncIterable(AsyncIterable):
    """每次 __aiter__ 都创建新 iterator，因此同一数据源可以从头重播。"""

    def __init__(self, values):
        self.values = tuple(values)
        self.created_iterators = []

    def __aiter__(self):
        iterator = SequenceAsyncIterator(self.values)
        self.created_iterators.append(iterator)
        return iterator


class MixinAsyncGenerator(AsyncGenerator):
    """记录 AsyncGenerator 默认 __anext__/aclose 分派的最小直接子类。"""

    def __init__(self, close_mode="generator-exit"):
        self.close_mode = close_mode
        self.calls = []

    async def asend(self, value):
        self.calls.append(("asend", value))
        return ("sent", value)

    async def athrow(self, exception_type, value=None, traceback=None):
        self.calls.append(("athrow", exception_type, value, traceback))

        if exception_type is GeneratorExit:
            if self.close_mode == "generator-exit":
                raise GeneratorExit
            if self.close_mode == "stop-async-iteration":
                raise StopAsyncIteration
            if self.close_mode == "ignore":
                return "still-running"
            raise ValueError("cleanup failed")

        if isinstance(exception_type, BaseException):
            raise exception_type
        if value is None:
            raise exception_type
        if isinstance(value, BaseException):
            raise value
        raise exception_type(value)


async def collect_async(iterable):
    """通过 async for 收集内存 iterable，作为多个测试的协议观察入口。"""

    return [item async for item in iterable]


def test_async_iterable_direct_subclass_requires_aiter():
    """AsyncIterable 的唯一 abstract primitive 是同步调用的 __aiter__。"""

    class IncompleteAsyncIterable(AsyncIterable):
        pass

    assert IncompleteAsyncIterable.__abstractmethods__ == {"__aiter__"}
    with pytest.raises(TypeError, match="abstract method"):
        IncompleteAsyncIterable()


def test_async_iterator_only_requires_anext_and_inherits_aiter_self_mixin():
    """AsyncIterator 已提供返回 self 的 __aiter__；直接子类只需实现 __anext__。"""

    class IncompleteAsyncIterator(AsyncIterator):
        pass

    iterator = SequenceAsyncIterator([1])

    assert IncompleteAsyncIterator.__abstractmethods__ == {"__anext__"}
    with pytest.raises(TypeError, match="abstract method"):
        IncompleteAsyncIterator()
    assert iterator.__aiter__() is iterator
    assert aiter(iterator) is iterator
    assert isinstance(iterator, AsyncIterator)
    assert isinstance(iterator, AsyncIterable)


def test_replayable_async_iterable_creates_independent_iterators():
    """iterable 可以重复开始；每个 async for 获得独立 iterator 和游标。"""

    source = ReplayableAsyncIterable(["a", "b"])

    async def consume_twice():
        return await collect_async(source), await collect_async(source)

    first, second = asyncio.run(consume_twice())

    assert first == ["a", "b"]
    assert second == ["a", "b"]
    assert len(source.created_iterators) == 2
    assert source.created_iterators[0] is not source.created_iterators[1]


def test_async_iterator_is_one_shot_after_exhaustion():
    """iterator 把游标保存在自身；耗尽后再次 async for 不会自动回到开头。"""

    iterator = SequenceAsyncIterator([1, 2])

    async def consume_twice():
        return await collect_async(iterator), await collect_async(iterator)

    first, second = asyncio.run(consume_twice())

    assert first == [1, 2]
    assert second == []
    # 两个元素、首次终止、第二轮终止，共调用四次 __anext__。
    assert iterator.anext_calls == 4


def test_aiter_calls_aiter_and_has_no_two_argument_variant():
    """aiter(source) 直接取异步 iterator；它不像 iter(callable, sentinel) 有双参数形式。"""

    source = ReplayableAsyncIterable([1])

    iterator = aiter(source)

    assert iterator is source.created_iterators[0]
    with pytest.raises(TypeError):
        aiter(source, None)


def test_anext_returns_awaitable_and_raises_stop_async_iteration_when_exhausted():
    """anext 先返回 awaitable；await 后得到元素，耗尽且无 default 时抛专用异常。"""

    async def workflow():
        iterator = SequenceAsyncIterator(["item"])
        pending = anext(iterator)

        assert inspect.isawaitable(pending)
        assert await pending == "item"
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)

    assert asyncio.run(workflow()) is None


def test_anext_default_is_only_used_for_exhaustion_not_false_values():
    """0 和空字符串都是正常元素；只有 StopAsyncIteration 才切换到显式 default。"""

    marker = object()

    async def workflow():
        iterator = SequenceAsyncIterator([0, ""])
        return (
            await anext(iterator, marker),
            await anext(iterator, marker),
            await anext(iterator, marker),
        )

    first, second, exhausted = asyncio.run(workflow())

    assert first == 0
    assert second == ""
    assert exhausted is marker


def test_async_for_uses_aiter_then_repeated_anext_until_normal_exhaustion():
    """async for 会隐藏 StopAsyncIteration；循环体只看到实际产生的值。"""

    source = ReplayableAsyncIterable(["first", "second"])

    assert asyncio.run(collect_async(source)) == ["first", "second"]
    assert len(source.created_iterators) == 1
    assert source.created_iterators[0].anext_calls == 3


def test_async_iterator_structural_recognition_requires_both_methods():
    """AsyncIterable 只看 __aiter__；成为 AsyncIterator 还必须同时提供 __anext__。"""

    class IterableShape:
        def __aiter__(self):
            return self

    class IteratorShape(IterableShape):
        async def __anext__(self):
            raise StopAsyncIteration

    assert isinstance(IterableShape(), AsyncIterable)
    assert not isinstance(IterableShape(), AsyncIterator)
    assert isinstance(IteratorShape(), AsyncIterable)
    assert isinstance(IteratorShape(), AsyncIterator)


def test_structural_async_iterator_check_does_not_validate_anext_result():
    """同步 __anext__ 返回 int 仍通过 ABC；真正 anext 时才发现结果不可 await。"""

    class InvalidIterator:
        def __aiter__(self):
            return self

        def __anext__(self):
            return 1

    value = InvalidIterator()

    async def workflow():
        with pytest.raises(TypeError, match="await|__anext__"):
            await anext(value)

    assert isinstance(value, AsyncIterator)
    assert asyncio.run(workflow()) is None


def test_anext_must_use_stop_async_iteration_instead_of_stop_iteration():
    """StopIteration 不能穿出 coroutine，会转成 RuntimeError；协议要求专用终止异常。"""

    class WrongTermination:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopIteration("wrong sentinel")

    async def workflow():
        with pytest.raises(RuntimeError, match="coroutine raised StopIteration"):
            await anext(WrongTermination())

    assert asyncio.run(workflow()) is None


def test_python_37_plus_aiter_rejects_old_awaitable_return_style():
    """旧协议允许 __aiter__ 返回 awaitable；Python 3.10 要求它立即返回 async iterator。"""

    class IteratorAwaitable:
        def __await__(self):
            if False:
                yield None
            return SequenceAsyncIterator([1])

    class LegacyIterable:
        def __aiter__(self):
            return IteratorAwaitable()

    value = LegacyIterable()

    assert isinstance(value, AsyncIterable)
    with pytest.raises(TypeError, match="async iterator"):
        aiter(value)


def test_async_generator_direct_subclass_requires_asend_and_athrow():
    """AsyncGenerator 提供 aiter/anext/aclose；直接子类只需补 asend 和 athrow。"""

    class IncompleteAsyncGenerator(AsyncGenerator):
        pass

    assert IncompleteAsyncGenerator.__abstractmethods__ == {"asend", "athrow"}
    with pytest.raises(TypeError, match="abstract method"):
        IncompleteAsyncGenerator()


def test_async_generator_anext_mixin_awaits_asend_none():
    """默认 __anext__ 不是别名：它创建 coroutine，运行时 await self.asend(None)。"""

    value = MixinAsyncGenerator()

    async def workflow():
        assert await anext(value) == ("sent", None)

    assert asyncio.run(workflow()) is None
    assert value.calls == [("asend", None)]


@pytest.mark.parametrize("mode", ["generator-exit", "stop-async-iteration"])
def test_async_generator_aclose_mixin_accepts_two_normal_exit_signals(mode):
    """aclose 通过 await athrow(GeneratorExit) 清理，并接受两种正常结束信号。"""

    value = MixinAsyncGenerator(close_mode=mode)

    async def workflow():
        assert await value.aclose() is None

    assert asyncio.run(workflow()) is None
    assert value.calls == [("athrow", GeneratorExit, None, None)]


def test_async_generator_aclose_mixin_rejects_ignored_generator_exit():
    """athrow 吞掉 GeneratorExit 并返回值，表示对象违反了异步关闭协议。"""

    value = MixinAsyncGenerator(close_mode="ignore")

    async def workflow():
        with pytest.raises(RuntimeError, match="ignored GeneratorExit"):
            await value.aclose()

    assert asyncio.run(workflow()) is None


def test_async_generator_structural_recognition_requires_full_control_api():
    """结构匹配要求 aiter/anext/asend/athrow/aclose 全部存在且不为 None。"""

    class CompleteShape:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def asend(self, value):
            raise StopAsyncIteration

        async def athrow(self, exception_type, value=None, traceback=None):
            raise exception_type

        async def aclose(self):
            return None

    class MissingClose(CompleteShape):
        aclose = None

    assert isinstance(CompleteShape(), AsyncGenerator)
    assert not isinstance(MissingClose(), AsyncGenerator)


def test_async_generator_function_and_object_have_distinct_runtime_roles():
    """async def 中含 yield 创建函数；调用结果是 async iterator，却不是 awaitable。"""

    async def values():
        yield 1

    async def workflow():
        value = values()

        assert inspect.isasyncgenfunction(values)
        assert not inspect.isasyncgen(values)
        assert inspect.isasyncgen(value)
        assert not inspect.isawaitable(value)
        assert isinstance(value, AsyncGenerator)
        assert isinstance(value, AsyncIterator)
        assert isinstance(value, AsyncIterable)
        assert await anext(value) == 1
        with pytest.raises(StopAsyncIteration):
            await anext(value)

    assert asyncio.run(workflow()) is None


def test_native_async_generator_anext_asend_athrow_and_aclose_work_together():
    """真实 async generator 接收值、处理注入异常，并在 aclose 时进入 finally。"""

    cleanup_events = []

    async def echo():
        try:
            received = yield "ready"
            while True:
                try:
                    received = yield f"received:{received}"
                except ValueError as error:
                    received = yield f"caught:{error}"
        finally:
            cleanup_events.append("closed")

    async def workflow():
        value = echo()

        assert await anext(value) == "ready"
        assert await value.asend("hello") == "received:hello"
        assert await value.athrow(ValueError("bad input")) == "caught:bad input"
        assert await value.aclose() is None
        assert await value.aclose() is None
        with pytest.raises(StopAsyncIteration):
            await anext(value)

    assert asyncio.run(workflow()) is None
    assert cleanup_events == ["closed"]


def test_native_async_generator_method_call_is_lazy_and_initial_asend_needs_none():
    """调用 asend 只创建 awaitable；首次真正运行时不能把非 None 值送入 yield。"""

    events = []

    async def worker():
        events.append("started")
        received = yield "ready"
        events.append(received)

    async def workflow():
        value = worker()
        pending = value.asend("too early")

        assert inspect.isawaitable(pending)
        assert events == []
        with pytest.raises(TypeError, match="just-started async generator"):
            await pending

        first = value.asend(None)
        assert events == []
        assert await first == "ready"
        assert events == ["started"]
        await value.aclose()

    assert asyncio.run(workflow()) is None


def test_native_async_generator_aclose_rejects_yield_after_generator_exit():
    """关闭时捕获 GeneratorExit 后继续 yield 会抛 RuntimeError；对象仍需再次关闭。"""

    async def ignores_close():
        try:
            yield "ready"
        except GeneratorExit:
            yield "incorrect"

    async def workflow():
        value = ignores_close()
        assert await anext(value) == "ready"

        with pytest.raises(RuntimeError, match="ignored GeneratorExit"):
            await value.aclose()
        assert await value.aclose() is None

    assert asyncio.run(workflow()) is None


def test_native_async_generator_aclose_propagates_cleanup_error():
    """finally 的其他异常不会被 aclose 隐藏；异常传出后 generator 已结束。"""

    async def broken_cleanup():
        try:
            yield "resource"
        finally:
            raise LookupError("cleanup failed")

    async def workflow():
        value = broken_cleanup()
        assert await anext(value) == "resource"

        with pytest.raises(LookupError, match="cleanup failed"):
            await value.aclose()
        with pytest.raises(StopAsyncIteration):
            await anext(value)

    assert asyncio.run(workflow()) is None


def test_break_does_not_replace_explicit_async_generator_close():
    """提前 break 后调用方仍持有 generator；显式 aclose 才让 finally 时机确定。"""

    cleanup_events = []

    async def records():
        try:
            yield "first"
            yield "second"
        finally:
            cleanup_events.append("closed")

    async def workflow():
        value = records()
        seen = []

        async for item in value:
            seen.append(item)
            break

        assert seen == ["first"]
        assert cleanup_events == []
        assert await value.aclose() is None
        assert cleanup_events == ["closed"]

    assert asyncio.run(workflow()) is None


def test_async_iteration_abcs_support_runtime_generic_aliases():
    """三个 ABC 的 [] 结果保存参数元数据；参数化 alias 不能直接用于 isinstance。"""

    iterable_alias = AsyncIterable[int]
    iterator_alias = AsyncIterator[str]
    generator_alias = AsyncGenerator[bytes, None]

    assert isinstance(iterable_alias, GenericAlias)
    assert iterable_alias.__origin__ is AsyncIterable
    assert iterable_alias.__args__ == (int,)
    assert iterator_alias.__origin__ is AsyncIterator
    assert iterator_alias.__args__ == (str,)
    assert generator_alias.__origin__ is AsyncGenerator
    assert generator_alias.__args__ == (bytes, None)

    with pytest.raises(TypeError, match="parameterized generic"):
        isinstance(SequenceAsyncIterator([]), iterator_alias)
