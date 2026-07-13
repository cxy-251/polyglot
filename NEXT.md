# Current Task

ID: `python.core.subscription-and-slicing-protocols`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 订阅、切片和容器写入协议测试套，把 ``obj[key]``、切片语法、索引赋值与删除连接到 ``__getitem__``、``__setitem__``、``__delitem__`` 和相关映射协议。

## Covers

- 序列索引、负索引、普通切片与扩展切片；
- ``slice`` 对象的 ``start`` / ``stop`` / ``step`` 与 ``slice.indices()``；
- ``__getitem__()``、``__setitem__()``、``__delitem__()``；
- 自定义序列自行处理负索引、切片和越界异常的责任；
- 多维订阅把逗号分隔项组合为 tuple key；
- 映射键与序列整数索引的不同语义；
- dict 子类的 ``__missing__()`` 只由 ``dict.__getitem__()`` 调用；
- 类订阅中的 ``__class_getitem__()``，以及元类 ``__getitem__()`` 的优先级；
- 不可变容器与可变容器在订阅赋值、删除上的边界。

## Common Pitfalls To Explain

- 以为解释器会在调用自定义 ``__getitem__`` 前自动规范化负索引；
- 把收到的 ``slice`` 当成已经补齐边界的 range；
- 扩展切片赋值时忽略步长不为 1 的长度约束；
- 以为 ``dict.get()``、``in`` 或迭代也会调用 ``__missing__``；
- 混淆实例订阅、类订阅与元类订阅的分派入口。

## Target File

`languages/python/core/test_subscription_and_slicing_protocols.py`

## Official Sources

- https://docs.python.org/3.10/reference/expressions.html#subscriptions
- https://docs.python.org/3.10/reference/expressions.html#slicings
- https://docs.python.org/3.10/reference/datamodel.html#object.__getitem__
- https://docs.python.org/3.10/reference/datamodel.html#object.__class_getitem__
- https://docs.python.org/3.10/library/functions.html#slice
- https://docs.python.org/3.10/library/stdtypes.html#mapping-types-dict

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释分派、参数形态和常见坑；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

真假值、比较、二元运算符以及一元运算与数值转换协议共四个测试套已完成首轮编写，但按照用户要求尚未运行。下一步直接编写订阅与切片协议测试套；不要先运行 pytest。
