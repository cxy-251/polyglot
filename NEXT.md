# Current Task

ID: `python.core.binary-operator-dispatch`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 二元与原地运算符分派测试套，讲清普通方法、反向方法和原地方法之间的调用顺序，并把内置数值与序列行为连接到数据模型协议。

## Covers

- `+`、`-`、`*`、`@`、`/`、`//`、`%`、`divmod()`、`pow()` / `**`
- `<<`、`>>`、`&`、`^`、`|`
- `__add__()` 等普通二元特殊方法
- `__radd__()` 等反向特殊方法与右侧子类优先级
- `__iadd__()` 等原地特殊方法以及缺失时的 fallback
- 返回 `NotImplemented` 与直接抛出异常的职责区别
- 数值运算、序列拼接和序列重复共用运算符但具有不同契约

## Common Pitfalls To Explain

- 把 ``__radd__`` 误解成每次交换参数后都会调用；
- 不支持另一种类型时直接抛出 ``TypeError``，从而阻止反向方法接手；
- 误以为 ``+=`` 必定原地修改对象，忽略不可变对象会重新绑定；
- 自定义 ``__iadd__`` 修改一部分状态后返回 ``NotImplemented``；
- 混淆 ``/`` 与 ``//``，以及负数 floor division 的方向。

## Target File

`languages/python/core/test_binary_operator_dispatch.py`

## Official Sources

- https://docs.python.org/3.10/reference/expressions.html#binary-arithmetic-operations
- https://docs.python.org/3.10/reference/datamodel.html#emulating-numeric-types
- https://docs.python.org/3.10/library/operator.html

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释分派顺序和坑；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

`languages/python/core/test_truth_value_testing.py` 和 `test_comparison_semantics.py` 已完成首轮编写，但按照用户要求尚未运行。下一步直接编写本任务的二元运算符分派测试套；不要先运行 pytest。
