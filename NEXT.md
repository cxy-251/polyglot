# Current Task

ID: `python.core.names-scopes-and-closures`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 名字绑定、作用域与闭包测试套，系统展示 local / enclosing / global / builtins 查找、赋值对局部作用域的静态影响、``global`` / ``nonlocal``、闭包 cell 和各类临时作用域。

## Covers

- 赋值、解包、for/with/except/import 等语句产生名字绑定；
- LEGB 名字查找与内置名称遮蔽；
- 函数体内只要出现赋值，该名称默认在整个代码块被判定为 local；
- ``UnboundLocalError`` 与“读取后再赋值”陷阱；
- ``global`` 修改模块级绑定，``nonlocal`` 修改最近的 enclosing 函数绑定；
- ``nonlocal`` 不会跳到 global，且目标必须已存在于 enclosing scope；
- 闭包保存 cell 而不是简单复制值，并可通过 nonlocal 维护状态；
- 默认参数捕获定义时值与闭包晚绑定的差异；
- comprehension / generator expression 的隐式作用域；
- class body 命名空间不是方法函数的 enclosing lexical scope；
- ``del`` 删除名字绑定，以及删除后重新查找/报错；
- ``locals()`` / ``globals()`` 作为命名空间视图的正常查阅边界。

## Common Pitfalls To Explain

- 以为局部赋值只从执行到该行之后才影响名字解析；
- 忘记 ``global`` / ``nonlocal`` 声明必须位于同一代码块并先于相关使用；
- 用局部变量名遮蔽 ``list``、``str`` 等内置对象；
- 以为修改 ``locals()`` 返回 dict 就能可靠改变优化后的函数局部变量；
- 认为 class body 中的普通名称可被方法像闭包变量一样直接读取；
- 混淆闭包晚绑定与默认参数定义时求值。

## Target File

`languages/python/core/test_012_names_scopes_and_closures.py`

## Official Sources

- https://docs.python.org/3.10/reference/executionmodel.html#naming-and-binding
- https://docs.python.org/3.10/reference/simple_stmts.html#the-global-statement
- https://docs.python.org/3.10/reference/simple_stmts.html#the-nonlocal-statement
- https://docs.python.org/3.10/reference/expressions.html#displays-for-lists-sets-and-dictionaries
- https://docs.python.org/3.10/library/functions.html#locals
- https://docs.python.org/3.10/library/functions.html#globals

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释静态作用域判定、cell 与遮蔽陷阱；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--011 共十一个 Python 核心测试套已完成首轮编写；最新的 011 覆盖 class 执行、构造两阶段、不可变子类、方法绑定、C3 MRO、协作多继承、subclass hook 和名称改写。全部文件按照用户要求尚未运行。下一步直接编写 012 名字、作用域与闭包；不要先运行 pytest。
