"""278｜Python 3.10 legacy generator-based coroutine 与迁移边界。

asyncio.coroutine 把使用 ``yield from`` 的 generator 标记成旧式 coroutine，使其可被
await/ensure_future；asyncio 的 introspection 会识别它，而 inspect 的 native-coroutine
判断不同。该 API 自 3.8 弃用并在 3.11 移除，新代码必须使用 async def/await。

这些案例面向 Python 3.10 当前补丁系列；当前文件尚未经过 pytest 验证。
"""

# polyglot-covers: python.asyncio.coroutine-decorator
# polyglot-covers: python.asyncio.generator-based-coroutine
# polyglot-covers: python.asyncio.generator-coroutine-yield-from
# polyglot-covers: python.asyncio.iscoroutine-generator-compatibility
# polyglot-covers: python.asyncio.iscoroutinefunction-generator-compatibility
# polyglot-covers: python.asyncio.ensure_future-generator-coroutine
# polyglot-covers: python.asyncio.generator-coroutines-deprecated-in-3.10
# polyglot-covers: python.asyncio.generator-coroutines-removed-in-3.11

import asyncio
import inspect


@asyncio.coroutine
def _legacy_compute(value):
    yielded = yield from asyncio.sleep(0, result=value * 2)
    return yielded


def test_asyncio_introspection_recognizes_legacy_generator_coroutine():
    coroutine = _legacy_compute(21)
    try:
        assert asyncio.iscoroutinefunction(_legacy_compute) is True
        assert inspect.iscoroutinefunction(_legacy_compute) is False
        assert asyncio.iscoroutine(coroutine) is True
        assert inspect.iscoroutine(coroutine) is False
        assert inspect.isawaitable(coroutine) is True
    finally:
        coroutine.close()


def test_legacy_coroutine_can_be_awaited_and_scheduled_with_ensure_future():
    async def scenario():
        direct = await _legacy_compute(10)
        scheduled = asyncio.ensure_future(_legacy_compute(21))
        assert isinstance(scheduled, asyncio.Task)
        return direct, await scheduled

    assert asyncio.run(scenario()) == (20, 42)
