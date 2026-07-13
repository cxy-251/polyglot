# Current Task

ID: `python.core.unary-and-conversion-protocols`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 一元运算和数值转换协议测试套，把 ``-``、``+``、``~``、``abs()`` 以及 int/float/complex/index/round/floor 等转换入口连接到对应特殊方法。

## Covers

- 一元 ``-``、``+``、``~`` 与 ``abs()``
- ``__neg__()``、``__pos__()``、``__invert__()``、``__abs__()``
- ``complex()``、``int()``、``float()`` 与对应转换方法
- ``__index__()`` 的无损整数语义，以及切片、``bin``、``hex``、``oct``、``operator.index``
- Python 3.10 中 ``int`` / ``float`` / ``complex`` 向 ``__index__`` 的 fallback
- ``round()``、``math.trunc()``、``math.floor()``、``math.ceil()``
- 特殊方法返回值的严格类型契约

## Common Pitfalls To Explain

- 把 ``__int__`` 当作所有“需要整数”的协议，忽略索引要求 ``__index__``；
- 从 ``__index__`` 返回 bool 或自定义 int 子类等非精确契约结果；
- 忘记 ``round(value, ndigits)`` 会把 ndigits 传给 ``__round__``；
- 假设一元 ``+`` 必定返回原对象；
- 混淆 ``~x`` 与简单变号。

## Target File

`languages/python/core/test_unary_and_conversion_protocols.py`

## Official Sources

- https://docs.python.org/3.10/reference/expressions.html#unary-arithmetic-and-bitwise-operations
- https://docs.python.org/3.10/reference/datamodel.html#emulating-numeric-types
- https://docs.python.org/3.10/library/functions.html
- https://docs.python.org/3.10/library/operator.html#operator.index
- https://docs.python.org/3.10/library/math.html#number-theoretic-functions

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释分派顺序和坑；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

真假值、比较语义和二元运算符分派三个测试套已完成首轮编写，但按照用户要求尚未运行。下一步直接编写本任务的一元与转换协议测试套；不要先运行 pytest。
