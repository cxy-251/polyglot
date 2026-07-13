# Current Task

ID: `python.core.iteration-and-generator-protocols`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 迭代器与生成器协议测试套，把 ``for``、``iter()``、``next()``、生成器函数/表达式和 ``yield from`` 连接到 ``__iter__``、``__next__``、``StopIteration`` 及生成器控制方法。

## Covers

- iterable 与 iterator 的区别，以及容器每次创建独立 iterator；
- ``iter()``、``next()``、``__iter__()``、``__next__()``、``StopIteration``；
- ``for`` 循环的协议展开、``break`` 与 ``else``；
- ``iter(callable, sentinel)`` 两参数形式；
- 缺少 ``__iter__`` 时向 ``__getitem__`` 的历史序列 fallback；
- ``reversed()`` 与 ``__reversed__()`` / 序列 fallback；
- 包含 ``yield`` 的函数返回 generator，并按需暂停与恢复；
- generator expression 的惰性求值和作用域；
- ``send()``、``throw()``、``close()`` 与 ``GeneratorExit``；
- ``yield from`` 委托、子生成器 return 值和双向数据传递；
- 生成器内部直接抛 ``StopIteration`` 转换为 ``RuntimeError`` 的规则。

## Common Pitfalls To Explain

- 把 iterable 当成可反复使用的 iterator；
- 自定义 iterator 的 ``__iter__`` 不返回自身；
- 忘记耗尽的 iterator 不会自动重置；
- 认为调用生成器函数会立即执行函数体；
- 第一次 ``send`` 非 ``None`` 值给尚未启动的 generator；
- 用 ``StopIteration`` 作为生成器函数体内的普通退出方式。

## Target File

`languages/python/core/test_008_iteration_and_generator_protocols.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#the-for-statement
- https://docs.python.org/3.10/reference/expressions.html#generator-iterator-methods
- https://docs.python.org/3.10/reference/expressions.html#yield-expressions
- https://docs.python.org/3.10/reference/datamodel.html#object.__iter__
- https://docs.python.org/3.10/library/functions.html#iter
- https://docs.python.org/3.10/library/functions.html#reversed

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释惰性执行、状态变化和协议 fallback；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

编号规范已写入 README 与 AGENTS，现有 Python 文件已按推荐阅读顺序编号为 001--007。真假值、比较、运算符、转换、订阅、函数调用、属性与描述符共七个测试套已完成首轮编写，但按照用户要求尚未运行。下一步直接编写 008 迭代器与生成器测试套；不要先运行 pytest。
