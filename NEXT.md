# Current Task

ID: `python.builtins.iteration-and-aggregation-functions`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 迭代、组合、筛选、排序与聚合类内置函数测试套，把 `iter` / `next`、`enumerate`、`zip`、`map`、`filter`、`reversed`、`sorted`、`all` / `any`、`min` / `max`、`sum` 的实际工作流和惰性边界集中展示。

## Covers

- `iter(iterable)`、`next(iterator[, default])` 与 iterator 自身返回；
- `iter(callable, sentinel)` 的无参数调用和按相等值终止；
- `enumerate(iterable, start)` 的惰性索引配对；
- `zip()` 的最短输入终止、零/一输入、`strict=True` 长度校验（Python 3.10）；
- `map()` 的多 iterable 最短终止和单次惰性消费；
- `filter(function, iterable)` 与 `filter(None, iterable)` 真假筛选；
- `reversed()` 对序列和 `__reversed__`，以及返回 iterator；
- `sorted()` 接受任意 iterable、key/reverse/稳定性且不改输入；
- `all()` / `any()` 的空 iterable 结果与短路；
- `min()` / `max()` 的 iterable/多参数形式、key、default 限制和稳定首项；
- `sum()` 的 start 参数、数字聚合和拒绝 str/bytes；
- iterator 惰性、耗尽和不要复用一次性结果的共同边界。

## Common Pitfalls To Explain

- 对同一个 map/filter/zip 对象迭代两次，第二次为空；
- 默认 zip 静默截断较长输入，未在需要时使用 `strict=True`；
- 把 `filter(None, values)` 当作只删除 None，实际会删除所有假值；
- 认为 `sorted()` 原地修改，或认为 `reversed()` 返回 list；
- 忘记 `all([]) is True`、`any([]) is False`；
- 对空 iterable 调 min/max 未提供 default；
- 认为 min/max key 相同项会任意选择，忽略稳定首项语义；
- 用 sum 拼接字符串/字节或嵌套列表，产生错误或低效代码。

## Target File

`languages/python/builtins/test_026_iteration_and_aggregation_functions.py`

## Official Sources

- https://docs.python.org/3.10/library/functions.html#iter
- https://docs.python.org/3.10/library/functions.html#next
- https://docs.python.org/3.10/library/functions.html#enumerate
- https://docs.python.org/3.10/library/functions.html#zip
- https://docs.python.org/3.10/library/functions.html#map
- https://docs.python.org/3.10/library/functions.html#filter
- https://docs.python.org/3.10/library/functions.html#reversed
- https://docs.python.org/3.10/library/functions.html#sorted
- https://docs.python.org/3.10/library/functions.html#all
- https://docs.python.org/3.10/library/functions.html#any
- https://docs.python.org/3.10/library/functions.html#min
- https://docs.python.org/3.10/library/functions.html#max
- https://docs.python.org/3.10/library/functions.html#sum

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释解释惰性、短路、稳定性和不同长度输入；
- 用小型数据流水线而不是一函数一条孤立断言；
- 与 008 的迭代协议、015 的异步协议、023 的 list.sort 避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--025 位于 `builtins/`，编号在整个 Python 树全局连续。025 set/frozenset 已完成首轮编写，尚未运行。下一步直接编写 026 迭代与聚合内置函数；不要先运行 pytest。
