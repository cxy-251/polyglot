"""055｜生成器、可等待对象与协程 ABC 的协议分派和安全生命周期。

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
