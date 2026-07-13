# Current Task

ID: `python.core.context-manager-protocols`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 同步上下文管理器协议测试套，把 ``with`` 展开为 ``__enter__()`` / ``__exit__()`` 调用，展示资源获取、异常传播/抑制、多管理器嵌套和清理失败时的异常关系。

## Covers

- ``with expression as target`` 的求值、enter 返回值绑定和 exit 时机；
- 正常退出时 ``__exit__(None, None, None)``；
- 异常退出时传入异常类型、实例和 traceback；
- ``__exit__`` 返回真值抑制异常、返回假值继续传播；
- ``__enter__`` 失败时不调用同一管理器的 ``__exit__``；
- ``as`` 目标绑定失败仍属于已进入的 with suite，并触发 ``__exit__``；
- 多个上下文管理器等价于嵌套 with：从左到右进入、从右到左退出；
- 后一个 ``__enter__`` 失败时已进入的前序管理器仍会退出；
- return / break 等非局部跳转仍执行 ``__exit__``；
- ``__exit__`` 自身抛出异常时替换原异常并保留上下文；
- ``__enter__`` 可以返回资源代理，而不必返回管理器自身。

## Common Pitfalls To Explain

- 误以为 ``as`` 绑定的一定是 context manager 对象本身；
- 在 ``__exit__`` 中无条件返回真值，意外吞掉所有异常；
- 在 ``__enter__`` 内完成一半资源获取后失败，却没有自行回滚；
- 忽略多个管理器的逆序退出和部分进入状态；
- 在清理阶段抛出新异常，遮蔽原始业务异常。

## Target File

`languages/python/core/test_010_context_manager_protocols.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#the-with-statement
- https://docs.python.org/3.10/reference/datamodel.html#with-statement-context-managers
- https://docs.python.org/3.10/library/stdtypes.html#context-manager-types

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释 enter/exit 顺序、异常三元组和抑制语义；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--009 共九个 Python 核心测试套已完成首轮编写；最新的 009 覆盖异常匹配、try/else/finally、宽 try 陷阱、自定义异常、traceback 重抛差异、异常链和 finally 覆盖控制流。全部文件按照用户要求尚未运行。下一步直接编写 010 同步上下文管理器协议；不要先运行 pytest。
