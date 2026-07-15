"""049｜生成器、可等待对象与协程 ABC 的协议分派和安全生命周期。

``collections.abc`` 中的异步相关 ABC 既能约束直接子类，也能识别部分结构
协议；但 ABC 判定只看方法是否存在，不执行方法验证返回值。
``inspect.isawaitable`` 的检测范围更适合作为“能否用于 await”的能力判断，
因为它还识别没有 ``__await__`` 方法的 generator-based coroutine。

本文件的 asyncio 工作流都立即完成，不使用 sleep 或外部 I/O；创建的 native
coroutine 都会被 event loop 消费或显式 close。当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.collections.abc.Generator python.generator.abc-primitives
# polyglot-covers: python.generator.next-send-none python.generator.close-mixin
# polyglot-covers: python.generator.close-generator-exit python.generator.close-stop-iteration
# polyglot-covers: python.generator.close-ignored-exit python.generator.close-cleanup-error
# polyglot-covers: python.generator.function-object python.generator.builtin-registration
# polyglot-covers: python.generator.next python.generator.send python.generator.throw
# polyglot-covers: python.generator.close python.generator.finally-cleanup
# polyglot-covers: python.generator.initial-send python.generator.structural-recognition
# polyglot-covers: python.generator.structural-semantics python.collections.abc.Awaitable
# polyglot-covers: python.awaitable.abstract-method python.awaitable.await-iterator
# polyglot-covers: python.awaitable.immediate-workflow python.awaitable.invalid-iterator
# polyglot-covers: python.collections.abc.Coroutine python.coroutine.function-object
# polyglot-covers: python.coroutine.native-registration python.coroutine.isawaitable
# polyglot-covers: python.coroutine.single-consumption python.coroutine.explicit-close
# polyglot-covers: python.coroutine.abc-primitives python.coroutine.close-mixin
# polyglot-covers: python.coroutine.close-generator-exit python.coroutine.close-stop-iteration
# polyglot-covers: python.coroutine.close-ignored-exit python.types.coroutine
# polyglot-covers: python.coroutine.generator-based python.inspect.isawaitable
# polyglot-covers: python.coroutine.generic-alias




import asyncio
import inspect
from collections.abc import Awaitable
from collections.abc import Coroutine
from collections.abc import Generator
from collections.abc import Iterator
from types import GenericAlias
from types import coroutine
import pytest
from collections.abc import AsyncGenerator
from collections.abc import AsyncIterable
from collections.abc import AsyncIterator

class MixinGenerator(Generator):
    """记录 Generator 默认 ``__next__``/``close`` 转发路径的最小直接子类。"""

    def __init__(self, close_mode="generator-exit"):
        self.close_mode = close_mode
        self.calls = []

    def send(self, value):
        self.calls.append(("send", value))
        return ("sent", value)

    def throw(self, exception_type, value=None, traceback=None):
        self.calls.append(("throw", exception_type, value, traceback))

        if exception_type is GeneratorExit:
            if self.close_mode == "generator-exit":
                raise GeneratorExit
            if self.close_mode == "stop-iteration":
                raise StopIteration
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


class ImmediateAwaitable(Awaitable):
    """``__await__`` 返回立即结束的 generator iterator，不依赖 event-loop I/O。"""

    def __init__(self, result):
        self.result = result
        self.await_calls = 0

    def __await__(self):
        self.await_calls += 1
        if False:
            # 含 yield 让本方法成为 generator function；分支不会真的挂起。
            yield None
        return self.result


class MixinCoroutine(Coroutine):
    """展示 Coroutine abstract primitives 与默认 close 的最小对象。"""

    def __init__(self, result=None, close_mode="generator-exit"):
        self.result = result
        self.close_mode = close_mode
        self.calls = []

    def __await__(self):
        self.calls.append(("await",))
        if False:
            yield None
        return self.result

    def send(self, value):
        self.calls.append(("send", value))
        raise StopIteration(self.result)

    def throw(self, exception_type, value=None, traceback=None):
        self.calls.append(("throw", exception_type, value, traceback))

        if exception_type is GeneratorExit:
            if self.close_mode == "generator-exit":
                raise GeneratorExit
            if self.close_mode == "stop-iteration":
                raise StopIteration
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


async def await_value(value):
    """让 asyncio.run 消费任意 awaitable，不要求输入本身是 native coroutine。"""

    return await value


def test_generator_direct_subclass_only_requires_send_and_throw_primitives():
    """Generator 已提供 __iter__/__next__/close；直接子类只需补 send 与 throw。"""

    class IncompleteGenerator(Generator):
        pass

    assert IncompleteGenerator.__abstractmethods__ == {"send", "throw"}
    with pytest.raises(TypeError, match="abstract method"):
        IncompleteGenerator()


def test_generator_next_mixin_delegates_to_send_none():
    """Generator.__next__ 是公开 mixin：next(value) 精确转发为 value.send(None)。"""

    value = MixinGenerator()

    assert next(value) == ("sent", None)
    assert value.calls == [("send", None)]


@pytest.mark.parametrize("mode", ["generator-exit", "stop-iteration"])
def test_generator_close_mixin_accepts_generator_exit_or_stop_iteration(mode):
    """close 通过 throw(GeneratorExit) 驱动；两种终止信号都表示正常关闭。"""

    value = MixinGenerator(close_mode=mode)

    assert value.close() is None
    assert value.calls == [("throw", GeneratorExit, None, None)]


def test_generator_close_mixin_rejects_ignored_generator_exit():
    """throw 吞掉 GeneratorExit 并返回值，等价于 generator 在 close 中继续 yield。"""

    value = MixinGenerator(close_mode="ignore")

    with pytest.raises(RuntimeError, match="generator ignored GeneratorExit"):
        value.close()
    assert value.calls == [("throw", GeneratorExit, None, None)]


def test_generator_close_mixin_propagates_unrelated_cleanup_error():
    """只有两个终止异常表示正常关闭；清理逻辑的其他错误不能被隐藏。"""

    value = MixinGenerator(close_mode="error")

    with pytest.raises(ValueError, match="cleanup failed"):
        value.close()


def test_generator_function_and_called_generator_object_are_different_values():
    """def 中含 yield 只创建 generator function；调用后才创建可迭代对象。"""

    def numbers():
        yield 1

    value = numbers()

    assert inspect.isgeneratorfunction(numbers)
    assert not inspect.isgenerator(numbers)
    assert not isinstance(numbers, Generator)
    assert inspect.isgenerator(value)
    assert isinstance(value, Generator)
    assert isinstance(value, Iterator)
    value.close()


def test_builtin_generator_next_send_throw_close_and_finally_work_together():
    """真实 generator 可接收值、注入异常并在 close 时可靠进入 finally。"""

    cleanup_events = []

    def echo():
        try:
            received = yield "ready"
            while True:
                try:
                    received = yield f"received:{received}"
                except ValueError as error:
                    received = yield f"caught:{error}"
        finally:
            cleanup_events.append("closed")

    value = echo()

    assert next(value) == "ready"
    assert value.send("hello") == "received:hello"
    assert value.throw(ValueError("bad input")) == "caught:bad input"
    assert value.close() is None
    assert cleanup_events == ["closed"]
    with pytest.raises(StopIteration):
        next(value)


def test_just_started_generator_only_accepts_none_via_send():
    """首次恢复还没到 yield expression，不能注入值；send(None) 等价于 next。"""

    def worker():
        received = yield "ready"
        return received

    value = worker()

    with pytest.raises(TypeError, match="just-started generator"):
        value.send("too early")
    assert value.send(None) == "ready"
    value.close()


def test_real_generator_close_raises_if_generator_yields_after_generator_exit():
    """捕获 GeneratorExit 后继续 yield 会使 close 抛错；之后仍应再次关闭。"""

    def ignores_close():
        try:
            yield "ready"
        except GeneratorExit:
            yield "incorrect"

    value = ignores_close()
    assert next(value) == "ready"

    with pytest.raises(RuntimeError, match="generator ignored GeneratorExit"):
        value.close()

    # 第一次 close 停在错误的 yield；第二次注入 GeneratorExit 后完成关闭。
    assert value.close() is None


def test_real_generator_close_propagates_exception_raised_by_cleanup():
    """finally 的业务异常会覆盖关闭路径并传给调用方，generator 已关闭。"""

    def broken_cleanup():
        try:
            yield "resource"
        finally:
            raise RuntimeError("cleanup failed")

    value = broken_cleanup()
    assert next(value) == "resource"

    with pytest.raises(RuntimeError, match="cleanup failed"):
        value.close()
    assert inspect.getgeneratorstate(value) == inspect.GEN_CLOSED


def test_generator_structural_recognition_requires_the_complete_method_set():
    """Generator 结构 hook 扫描 iter/next/send/throw/close，少一个就不匹配。"""

    class CompleteShape:
        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

        def send(self, value):
            raise StopIteration(value)

        def throw(self, exception_type, value=None, traceback=None):
            raise exception_type

        def close(self):
            return None

    class MissingClose(CompleteShape):
        close = None

    assert isinstance(CompleteShape(), Generator)
    assert not isinstance(MissingClose(), Generator)


def test_generator_structural_check_does_not_validate_runtime_semantics():
    """方法名齐全即可通过 ABC；错误的 __iter__ 在真正调用 iter 时才暴露。"""

    class BrokenShape:
        def __iter__(self):
            return []

        def __next__(self):
            return "never stops"

        def send(self, value):
            return value

        def throw(self, exception_type, value=None, traceback=None):
            return None

        def close(self):
            return None

    value = BrokenShape()

    assert isinstance(value, Generator)
    with pytest.raises(TypeError, match="non-iterator"):
        iter(value)


def test_awaitable_direct_subclass_requires_await_method():
    """Awaitable 的唯一 abstract primitive 是 __await__；ABC 不替它提供执行算法。"""

    class IncompleteAwaitable(Awaitable):
        pass

    assert IncompleteAwaitable.__abstractmethods__ == {"__await__"}
    with pytest.raises(TypeError, match="abstract method"):
        IncompleteAwaitable()


def test_immediate_custom_awaitable_returns_value_without_sleep_or_io():
    """await 会迭代 __await__ 返回的 iterator，并取得它的 StopIteration.value。"""

    value = ImmediateAwaitable({"status": "ready"})

    assert isinstance(value, Awaitable)
    assert inspect.isawaitable(value)
    assert asyncio.run(await_value(value)) == {"status": "ready"}
    assert value.await_calls == 1


def test_awaitable_structural_check_does_not_validate_await_iterator():
    """仅存在 __await__ 就能通过检查；返回 list 会在真正 await 时失败。"""

    class InvalidAwaitable:
        def __await__(self):
            return []

    value = InvalidAwaitable()

    assert isinstance(value, Awaitable)
    assert inspect.isawaitable(value)
    with pytest.raises(TypeError, match="non-iterator"):
        asyncio.run(await_value(value))


def test_async_function_is_not_awaitable_until_it_is_called():
    """async def 创建 coroutine function；调用结果才是 Coroutine/Awaitable object。"""

    async def multiply(left, right):
        return left * right

    value = multiply(6, 7)

    assert inspect.iscoroutinefunction(multiply)
    assert not inspect.isawaitable(multiply)
    assert not isinstance(multiply, Awaitable)
    assert inspect.iscoroutine(value)
    assert inspect.isawaitable(value)
    assert isinstance(value, Coroutine)
    assert isinstance(value, Awaitable)
    assert asyncio.run(value) == 42


def test_native_coroutine_cannot_be_awaited_again_after_completion():
    """coroutine object 是一次性状态机；重复计算必须再次调用 async function。"""

    async def load_value():
        return "loaded"

    async def consume_once_then_retry():
        value = load_value()
        assert await value == "loaded"
        with pytest.raises(RuntimeError, match="cannot reuse already awaited coroutine"):
            await value

    assert asyncio.run(consume_once_then_retry()) is None


def test_unawaited_native_coroutine_can_be_explicitly_closed():
    """若不 await 已创建的对象，应显式 close，避免未等待协程警告。"""

    async def unused_work():
        return "unused"

    value = unused_work()

    assert inspect.getcoroutinestate(value) == inspect.CORO_CREATED
    assert value.close() is None
    assert inspect.getcoroutinestate(value) == inspect.CORO_CLOSED


def test_coroutine_direct_subclass_requires_await_send_and_throw():
    """Coroutine 继承 Awaitable，并新增 send/throw；close 则由 ABC 的 mixin 实现。"""

    class IncompleteCoroutine(Coroutine):
        pass

    assert IncompleteCoroutine.__abstractmethods__ == {
        "__await__",
        "send",
        "throw",
    }
    with pytest.raises(TypeError, match="abstract method"):
        IncompleteCoroutine()


def test_custom_coroutine_can_be_awaited_and_is_also_awaitable():
    """直接子类的 __await__ 决定 await 工作流；send/throw 用于手动驱动。"""

    value = MixinCoroutine(result="custom result")

    assert isinstance(value, Coroutine)
    assert isinstance(value, Awaitable)
    assert inspect.isawaitable(value)
    assert asyncio.run(await_value(value)) == "custom result"
    assert value.calls == [("await",)]


@pytest.mark.parametrize("mode", ["generator-exit", "stop-iteration"])
def test_coroutine_close_mixin_accepts_generator_exit_or_stop_iteration(mode):
    """Coroutine.close 与 Generator.close 采用相同约定：向 throw 注入 GeneratorExit。"""

    value = MixinCoroutine(close_mode=mode)

    assert value.close() is None
    assert value.calls == [("throw", GeneratorExit, None, None)]


def test_coroutine_close_mixin_rejects_ignored_generator_exit():
    """自定义 Coroutine 若在关闭时继续返回值，mixin 会指出协议错误。"""

    value = MixinCoroutine(close_mode="ignore")

    with pytest.raises(RuntimeError, match="coroutine ignored GeneratorExit"):
        value.close()


def test_types_coroutine_generator_is_awaitable_without_awaitable_abc():
    """generator-based coroutine 可能无 __await__；isawaitable 比 isinstance 更完整。"""

    @coroutine
    def legacy_operation():
        if False:
            yield None
        return "legacy result"

    value = legacy_operation()

    assert inspect.isgenerator(value)
    assert isinstance(value, Generator)
    assert not hasattr(value, "__await__")
    assert not isinstance(value, Awaitable)
    assert not isinstance(value, Coroutine)
    assert inspect.isawaitable(value)
    assert asyncio.run(await_value(value)) == "legacy result"


def test_plain_generator_is_not_awaitable_without_types_coroutine_flag():
    """普通 generator 即使形状相同也不能 await；types.coroutine 的 flag 很关键。"""

    def ordinary_operation():
        if False:
            yield None
        return "ordinary result"

    value = ordinary_operation()

    assert isinstance(value, Generator)
    assert not inspect.isawaitable(value)
    assert not isinstance(value, Awaitable)
    value.close()


def test_generator_awaitable_and_coroutine_support_runtime_generic_aliases():
    """3.9+ ABC 可用 [] 保存类型参数；isinstance 仍只能使用裸 ABC。"""

    generator_alias = Generator[str, int, None]
    awaitable_alias = Awaitable[bytes]
    coroutine_alias = Coroutine[str, int, float]

    assert isinstance(generator_alias, GenericAlias)
    assert generator_alias.__origin__ is Generator
    assert generator_alias.__args__ == (str, int, None)
    assert awaitable_alias.__origin__ is Awaitable
    assert awaitable_alias.__args__ == (bytes,)
    assert coroutine_alias.__origin__ is Coroutine
    assert coroutine_alias.__args__ == (str, int, float)

    with pytest.raises(TypeError, match="parameterized generic"):
        isinstance(MixinGenerator(), generator_alias)


# 异步 iterable、iterator 与 generator 的协议和安全关闭示例。
#
# 异步迭代把同步协议中的 ``iter``/``next`` 拆成 ``__aiter__`` 和返回 awaitable 的
# ``__anext__``。Python 3.10 的 ``aiter``/``anext`` 让这条隐式分派可以直接观察；
# ``AsyncGenerator`` 又在 iterator 基础上增加发送、异常注入和显式异步关闭。
#
# 这里的所有 awaitable 都会立即完成；native async generator 会被耗尽或显式
# ``aclose``。当前文件尚未经过 pytest 验证。

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
        # 第一次 aclose 已消费错误 yield；3.10 再次关闭时以
        # StopAsyncIteration 表示对象终于结束，而不是返回普通值。
        with pytest.raises(StopAsyncIteration):
            await value.aclose()
        with pytest.raises(StopAsyncIteration):
            await anext(value)
        assert value.ag_frame is None

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
