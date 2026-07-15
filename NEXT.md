# Current Task

ID: `python.stdlib.collections-abc-async-iteration`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `AsyncIterable`、`AsyncIterator` 与 `AsyncGenerator` 测试套：
展示异步迭代协议、`aiter()`/`anext()`、自定义异步 iterator、native async
generator 的发送/异常/关闭生命周期，以及三个 ABC 的 mixin 与结构识别边界。

## Covers

- `AsyncIterable` direct subclass 必须实现 `__aiter__()`；
- `AsyncIterator` 继承 `AsyncIterable`，只需实现 `__anext__()`，默认
  `__aiter__()` 返回 self；
- 可重复 async iterable 每次创建独立 iterator，iterator 本身是一次性状态；
- Python 3.10 `aiter(value)` 只接受一个参数，结果必须实现 `__anext__()`；
- `anext(iterator)` 返回 awaitable，耗尽时抛 `StopAsyncIteration`；
- `anext(iterator, default)` 在耗尽时返回 default，并保留合法的 false value；
- `async for` 等价协议路径与正常 exhaustion；
- `__anext__()` 必须返回 awaitable，并以 `StopAsyncIteration` 表示耗尽；
- `__aiter__()` 返回 awaitable 而非 async iterator 是 Python 3.7+ 协议错误；
- `AsyncIterable`/`AsyncIterator` 的结构识别只扫描方法名，不验证运行语义；
- async generator function 与调用后生成的 async generator object 不同；
- native async generator 已注册为 `AsyncGenerator`、`AsyncIterator`、
  `AsyncIterable`；
- async generator 的 `anext`、`asend`、`athrow`、`aclose` 与 finally cleanup；
- 刚启动的 async generator 只能 `asend(None)`；
- `AsyncGenerator` direct subclass 要实现 `asend()` 与 `athrow()`；
- AsyncGenerator mixin 的 `__anext__()` 委托 `asend(None)`；
- AsyncGenerator mixin `aclose()` 通过 `athrow(GeneratorExit)`，接受
  GeneratorExit/StopAsyncIteration；
- async generator 在关闭时吞掉 GeneratorExit 并继续 yield 会抛 RuntimeError；
- native async generator 提前停止消费后必须显式 `aclose()`；
- `AsyncIterable`、`AsyncIterator`、`AsyncGenerator` 的 GenericAlias 元数据。

## Common Pitfalls To Explain

- 把 async iterable 与 async iterator 混为一谈，意外复用已耗尽状态；
- 把 Python 3.5 的旧式 awaitable `__aiter__` 写法用于 Python 3.10；
- 从 `__anext__` 返回普通值，或用 StopIteration 代替 StopAsyncIteration；
- 认为 `async for` 的 break 一定立即关闭任意 async iterator；
- 只创建 `asend()`/`athrow()`/`aclose()` awaitable 却不 await；
- 提前停止 native async generator 后不显式关闭，导致 finally 清理时机不确定；
- 在案例中加入 sleep 或 I/O；本套所有异步步骤都立即完成。

## Target File

`languages/python/stdlib/data_types/test_049_collections_abc_generators_coroutines_and_async_iteration.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.abc.html
- https://github.com/python/cpython/blob/3.10/Lib/_collections_abc.py
- https://docs.python.org/3.10/library/functions.html#aiter
- https://docs.python.org/3.10/library/functions.html#anext
- https://docs.python.org/3.10/reference/datamodel.html#asynchronous-iterators
- https://docs.python.org/3.10/reference/expressions.html#asynchronous-generator-iterator-methods
- https://docs.python.org/3.10/library/inspect.html#inspect.isasyncgen

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 语言能力和标准库；
- 异步工作流由立即完成的 `asyncio.run()` 消费，不使用 sleep、网络、线程；
- 每个 native async generator 及其方法返回的 awaitable 都必须完整消费或关闭；
- 手写 AsyncIterator/AsyncGenerator 只保留当前协议需要的最小状态；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--054 已完成此前范围首轮编写；055 Generator/Awaitable/Coroutine 已完成首轮
静态编写，共 25 个测试函数，覆盖同步 generator 生命周期、自定义 awaitable、
native coroutine、ABC mixin 与 generator-based coroutine。全部 Python 文件仍未运行。
下一步直接编写 056 async iteration；不要先运行 pytest。
