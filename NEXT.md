# Current Task

ID: `python.core.functions-calls-and-argument-binding`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 函数定义、调用与参数绑定测试套，连接 ``def`` / ``lambda``、位置参数、关键字参数、解包语法和 ``__call__`` 协议，并讲清默认值与调用求值时机。

## Covers

- ``def`` 创建函数对象、函数返回值与隐式 ``None``；
- 位置参数、普通参数、仅限位置参数 ``/``、仅限关键字参数 ``*``；
- 默认参数在定义时求值，以及可变默认值陷阱；
- ``*args`` 收集为 tuple、``**kwargs`` 收集为 dict；
- 调用时 ``*iterable`` 与 ``**mapping`` 解包；
- 参数绑定中的重复值、缺失值、多余值和非字符串关键字错误；
- 参数表达式从左到右求值，绑定失败也不会回滚已有副作用；
- 函数注解只保存元数据，不自动执行运行时类型检查；
- ``lambda`` 的表达式边界与闭包晚绑定陷阱；
- 自定义对象的 ``__call__()``，以及 ``callable()`` 的协议判断。

## Common Pitfalls To Explain

- 把默认参数当成每次调用都会重新计算；
- 用可变默认 list/dict 保存临时状态；
- 混淆调用端 ``*`` / ``**`` 解包与定义端参数收集；
- 认为注解会阻止错误类型实参；
- 在循环中创建 lambda 时忽略自由变量的晚绑定；
- 以为参数绑定失败意味着参数表达式没有执行。

## Target File

`languages/python/core/test_functions_calls_and_argument_binding.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#function-definitions
- https://docs.python.org/3.10/reference/expressions.html#calls
- https://docs.python.org/3.10/reference/expressions.html#lambda
- https://docs.python.org/3.10/reference/datamodel.html#object.__call__
- https://docs.python.org/3.10/library/functions.html#callable

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释绑定顺序、求值时机和常见坑；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

真假值、比较、二元运算、一元与数值转换、订阅与切片共五个测试套已完成首轮编写，但按照用户要求尚未运行。下一步直接编写函数调用与参数绑定测试套；不要先运行 pytest。
