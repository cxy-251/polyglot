# Current Task

ID: `python.builtins.general-sequence-types`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `list`、`tuple` 与 `range` 通用序列测试套，展示共同序列操作以及可变列表、不可变记录和惰性等差数列之间的关键差异。

## Covers

- `list()` / `tuple()` / `range()` 构造与字面量、空值和生成 iterable；
- 通用索引、切片、成员判断、连接、重复、`index()` / `count()`；
- 序列的字典序比较及首个不同元素决定结果；
- list 索引/切片写入、扩展切片等长约束和删除；
- `append()` / `extend()` / `insert()` 的输入形状差异；
- `remove()` / `pop()` / `clear()`、不存在元素异常；
- `reverse()`、`copy()` 与浅拷贝边界；
- `sort()` 的 key、reverse、稳定性，以及原地方法返回 None；
- 嵌套 list 乘法造成的别名共享；
- tuple packing/unpacking、单元素逗号、不可变容器内的可变对象；
- list 不可 hash、tuple 的 hashability 取决于元素；
- range 的 start/stop/step、负步长、空 range 和 step=0；
- range 的惰性、索引/切片仍返回 range、成员判断；
- 不同参数但元素相同的 range 相等/hash，以及超大 range 的 `len()` 边界。

## Common Pitfalls To Explain

- 混淆 `append(iterable)` 与 `extend(iterable)`；
- 期待 `list.sort()` / `reverse()` 返回排好序的列表；
- 使用 `[[0] * width] * height` 得到共享行；
- 认为 list.copy() 会递归复制嵌套对象；
- 认为 tuple 里有 list 时整个对象仍可 hash；
- 把括号当作 tuple 的决定因素，忘记单元素 tuple 的逗号；
- 为了检查成员把 range 先转成 list；
- 认为 range 参数不同就一定不相等，或认为任意大 range 的 len 都能表示。

## Target File

`languages/python/builtins/test_023_general_sequence_types.py`

## Official Sources

- https://docs.python.org/3.10/library/stdtypes.html#sequence-types-list-tuple-range
- https://docs.python.org/3.10/library/stdtypes.html#common-sequence-operations
- https://docs.python.org/3.10/library/stdtypes.html#mutable-sequence-types
- https://docs.python.org/3.10/library/stdtypes.html#lists
- https://docs.python.org/3.10/library/stdtypes.html#tuples
- https://docs.python.org/3.10/library/stdtypes.html#ranges
- https://docs.python.org/3.10/library/functions.html#list
- https://docs.python.org/3.10/library/functions.html#tuple
- https://docs.python.org/3.10/library/functions.html#range
- https://docs.python.org/3.10/library/functions.html#sorted

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释解释原地/新对象、浅拷贝/共享和惰性范围；
- 不做无意义的每个边界组合矩阵，使用可复用的数据处理例子；
- 与 005 的订阅协议、017 的赋值/解包和后续 built-in function 文件避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--022 位于 `builtins/`，编号在整个 Python 树全局连续。022 bytes/bytearray/memoryview 已完成首轮编写，尚未运行。下一步直接编写 023 list/tuple/range；不要先运行 pytest。
