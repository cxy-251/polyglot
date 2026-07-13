# Current Task

ID: `python.core.async-functions-and-protocols`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 ``async`` / ``await``、异步迭代器、异步生成器与异步上下文管理器测试套，在不引入 pytest 插件的前提下用标准库 ``asyncio.run()`` 驱动案例，连接全部核心异步特殊方法。

## Covers

- 调用 ``async def`` 返回 coroutine，函数体到 await/运行时才开始；
- coroutine 的返回值、异常传播和不能重复 await；
- ``await`` 与 ``__await__()`` 协议，以及必须返回 iterator；
- ``async for``、``__aiter__()``、``__anext__()``、``StopAsyncIteration``；
- async iterator 单次状态与 async iterable 创建独立 iterator；
- ``async for`` 的 ``break`` / ``else``；
- ``async with``、``__aenter__()``、``__aexit__()``、异常传播与抑制；
- 多个 async context manager 的进入/退出顺序；
- async generator 的惰性执行与 ``__anext__()``；
- ``asend()``、``athrow()``、``aclose()`` 与清理；
- async generator 禁止带值 ``return`` 的语法边界；
- 同步 iterable/context manager 与异步语法协议不可混用。

## Common Pitfalls To Explain

- 调用 coroutine 函数后忘记 await；
- 重复 await 已完成 coroutine；
- 让 ``__await__`` 返回普通值而不是 iterator；
- 在 Python 3.10 把 ``__aiter__`` 写成返回 awaitable，而不是直接返回 async iterator；
- 用 ``StopIteration`` 结束 async iterator，而不是 ``StopAsyncIteration``；
- 忘记 ``aclose`` 异步生成器所管理的资源；
- 以为普通 ``with`` 对象自动支持 ``async with``。

## Target File

`languages/python/core/test_015_async_functions_and_protocols.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#coroutine-function-definition
- https://docs.python.org/3.10/reference/expressions.html#await-expression
- https://docs.python.org/3.10/reference/compound_stmts.html#the-async-for-statement
- https://docs.python.org/3.10/reference/compound_stmts.html#the-async-with-statement
- https://docs.python.org/3.10/reference/datamodel.html#coroutine-objects
- https://docs.python.org/3.10/reference/expressions.html#asynchronous-generator-iterator-methods
- https://docs.python.org/3.10/library/asyncio-runner.html#asyncio.run

## Authoring Requirements

- 使用 pytest 风格的同步测试函数，在内部以 ``asyncio.run()`` 驱动 async 场景，不添加 pytest 插件；
- 使用必要而详细的中文注释解释惰性执行、协议终止异常和清理语义；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--014 共十四个 Python 核心测试套已完成首轮编写；最新的 014 覆盖 repr/str/ascii/format/f-string/bytes/hash、严格返回类型以及 eq/hash 稳定性。全部文件按照用户要求尚未运行。下一步直接编写 015 异步函数与协议；不要先运行 pytest。
