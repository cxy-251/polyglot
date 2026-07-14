# Current Task

ID: `python.stdlib.collections-abc-generators-coroutines`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.abc.Generator`、`Awaitable` 与 `Coroutine` 测试套：展示
同步 generator、native coroutine、自定义 awaitable 与 generator-based coroutine 的
ABC 关系、mixin 分派、`inspect.isawaitable()` 检测差异和安全生命周期。

## Covers

- `Generator` 继承 Iterator，direct subclass 要实现 `send()` 与 `throw()`；
- Generator mixin 的 `__next__()` 等价于 `send(None)`；
- Generator mixin 的 `close()` 通过 `throw(GeneratorExit)`，接受 GeneratorExit/StopIteration；
- generator 忽略 GeneratorExit 并继续产生值时，close 抛 `RuntimeError`；
- 普通 generator object 已注册为 `Generator` 与 `Iterator`；
- generator 的 `next`、`send`、`throw`、`close` 正常协作与 finally cleanup；
- 简单结构识别要求 `__iter__`、`__next__`、`send`、`throw`、`close` 全部存在；
- 仅方法名存在仍不验证运行语义；
- `Awaitable` direct subclass 要实现返回 iterator 的 `__await__()`；
- 自定义 immediate awaitable 可在无 sleep/I/O 的 `asyncio.run()` 工作流中返回结果；
- native coroutine object 同时是 `Coroutine` 与 `Awaitable`，并能被 `inspect.isawaitable` 检测；
- coroutine function 本身不是 awaitable，只有调用后创建的 coroutine object 才是；
- `Coroutine` direct subclass 要实现 `__await__()`、`send()` 与 `throw()`，close 由 mixin 提供；
- Coroutine mixin close 的 GeneratorExit/StopIteration/ignored-exit 三条边界；
- `types.coroutine()` 装饰的 generator-based coroutine 在 CPython 可被 await；
- generator-based coroutine 可能没有 `__await__`，因此不是 Awaitable/Coroutine ABC instance；
- `inspect.isawaitable()` 能识别上述 generator-based coroutine，是通用能力探测入口；
- 未 await 的 native coroutine 必须 await 或显式 close，案例不产生 ResourceWarning；
- Python 3.9+ Generator/Awaitable/Coroutine GenericAlias 元数据。

## Common Pitfalls To Explain

- 把 generator function 与调用后生成的 generator object 混为一谈；
- 认为实现 `send()` 就足以成为 Generator，忽略完整结构协议；
- close 时吞掉 GeneratorExit 后继续 yield；
- 调用 async function 后既不 await 也不 close；
- 仅用 `isinstance(value, Awaitable)` 判断所有可 await 对象，漏掉 generator-based coroutine；
- 手动驱动 coroutine 后又交给 event loop 重复消费；每个案例使用独立对象；
- 在测试中使用 sleep 或外部 I/O；本套只用立即完成的本地协程。

## Target File

`languages/python/stdlib/data_types/test_055_collections_abc_generators_coroutines.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.abc.html
- https://github.com/python/cpython/blob/3.10/Lib/_collections_abc.py
- https://docs.python.org/3.10/library/inspect.html#inspect.isawaitable
- https://docs.python.org/3.10/library/types.html#types.coroutine
- https://docs.python.org/3.10/reference/expressions.html#generator-iterator-methods
- https://docs.python.org/3.10/reference/datamodel.html#awaitable-objects

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- asyncio 案例必须立即完成，不使用 sleep、网络、线程或外部状态；
- 每个 native coroutine 要么由 asyncio.run 完整消费，要么在同一测试显式 close；
- 手写 Generator/Coroutine 只实现展示 mixin 所需的最小状态机；
- AsyncIterable/AsyncIterator/AsyncGenerator 留给下一测试套；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--053 已完成此前范围首轮编写；054 `MutableMapping` 已在 `data_types/` 完成首轮
静态编写，共 18 个测试，覆盖 pop/popitem/clear、update 三种来源、keyword precedence、
非原子失败、setdefault 与 storage bypass。全部 Python 文件仍未运行。下一步直接
编写 055 Generator/Awaitable/Coroutine；不要先运行 pytest。
