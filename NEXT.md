# Current Task

ID: `python.core.exception-handling-and-chaining`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 异常处理与异常链测试套，系统展示 ``try`` / ``except`` / ``else`` / ``finally``、``raise``、自定义异常和显式/隐式异常上下文，并讲清控制流被 finally 改写的风险。

## Covers

- 异常类型匹配、子类关系与 except 子句顺序；
- 捕获多个异常类型，以及只捕获能够处理的异常；
- ``else`` 仅在 try 正常完成时执行；
- ``finally`` 在正常返回、异常与循环控制流中都执行；
- ``raise``、裸 ``raise`` 和保存原 traceback 的重新抛出；
- 异常实例的 ``args``、自定义字段和自定义异常层次；
- 隐式 ``__context__``、显式 ``raise ... from ...`` 的 ``__cause__``；
- ``raise ... from None`` 隐藏展示链但保留诊断上下文；
- except 目标变量在子句结束后被清除；
- ``return`` / ``break`` / ``continue`` 与 finally 的交互；
- finally 中 return 或新异常覆盖原控制流的常见风险。

## Common Pitfalls To Explain

- 把宽泛 ``except Exception`` 放在更具体处理之前；
- 使用裸 ``except`` 吞掉 ``KeyboardInterrupt`` / ``SystemExit`` 等退出信号；
- 在 try 中包入过多代码，让 except 捕获到非预期位置的同类异常；
- 用 ``raise error`` 代替裸 ``raise``，改变 traceback 的重新抛出位置；
- 在 finally 中 return，从而吞掉原异常或覆盖原返回值；
- 误以为 ``from None`` 会删除内部 ``__context__``。

## Target File

`languages/python/core/test_009_exception_handling_and_chaining.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#the-try-statement
- https://docs.python.org/3.10/reference/simple_stmts.html#the-raise-statement
- https://docs.python.org/3.10/reference/simple_stmts.html#the-break-statement
- https://docs.python.org/3.10/reference/datamodel.html#exceptions
- https://docs.python.org/3.10/library/exceptions.html

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释异常匹配、链和控制流覆盖；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--008 共八个 Python 核心测试套已完成首轮编写；最新的 008 覆盖 iterable/iterator、for、iter 两参数形式、序列 fallback、reversed、生成器控制方法和 yield from。全部文件按照用户要求尚未运行。下一步直接编写 009 异常处理与异常链；不要先运行 pytest。
