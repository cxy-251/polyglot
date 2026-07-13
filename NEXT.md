# Current Task

ID: `python.builtins.set-types`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `set` 与 `frozenset` 集合类型测试套，展示去重、成员关系、集合代数、偏序比较、可变操作和可哈希冻结集合之间的关键差异。

## Covers

- set literal、空集合必须用 `set()`、iterable 构造和 set comprehension；
- 元素必须 hashable，以及 equality/hash 导致的去重；
- 无顺序、不可索引的语义边界；
- `union()` / `intersection()` / `difference()` / `symmetric_difference()`；
- `|` / `&` / `-` / `^` 运算符与方法在参数类型上的区别；
- `issubset()` / `issuperset()` / `isdisjoint()`；
- `<` / `<=` / `>` / `>=` 表示真子集/子集偏序，不是排序大小；
- `add()` / `update()` / `intersection_update()` / `difference_update()` / `symmetric_difference_update()`；
- `remove()` / `discard()` / `pop()` / `clear()` 的异常与返回值；
- set 方法原地返回 None、`copy()` 的浅拷贝；
- frozenset 不可变且可 hash，可作为 dict key 或 set 元素；
- set/frozenset 混合二元运算的结果类型由左操作数决定；
- 迭代期间改变 set 大小导致 RuntimeError，以及快照/推导式改写。

## Common Pitfalls To Explain

- 用 `{}` 创建空集合，实际得到 dict；
- 把 list/dict/set 直接放入 set；
- 依赖 set 迭代/`pop()` 顺序；
- 用 `<` 比较集合元素数量，误把偏序当总排序；
- 忘记 `set.union(iterable)` 可接受任意 iterable，而 `set | iterable` 要求集合；
- 期待 `add()` / `update()` 返回修改后的 set；
- 遍历时直接增删元素；
- 需要“集合的集合”时忘记使用 frozenset。

## Target File

`languages/python/builtins/test_025_set_types.py`

## Official Sources

- https://docs.python.org/3.10/library/stdtypes.html#set-types-set-frozenset
- https://docs.python.org/3.10/library/functions.html#set
- https://docs.python.org/3.10/library/functions.html#frozenset
- https://docs.python.org/3.10/reference/datamodel.html#object.__hash__

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释解释偏序、hashability、无顺序和方法/运算符差异；
- 使用标签、权限、ID 去重等实际集合工作流；
- 与 002/003/014 的比较、运算符和 hash 协议避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--024 位于 `builtins/`，编号在整个 Python 树全局连续。024 dict 已完成首轮编写，尚未运行。下一步直接编写 025 set/frozenset；不要先运行 pytest。
