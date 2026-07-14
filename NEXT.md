# Current Task

ID: `python.stdlib.collections-abc-set-mixins`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.abc.Set` 与 `MutableSet` 测试套：用可容纳不可哈希元素的
最小 list-backed set 展示集合比较、代数运算、结果构造、可选 hash 和原地 mutation
mixin；讲清 ABC 提供算法但不决定存储结构、元素约束或构造器签名。

## Covers

- `Set` 直接继承要求 `__contains__`、`__iter__`、`__len__`；
- 默认 `<=` / `<` / `==` / `!=` / `>` / `>=` 的集合包含语义；
- 比较操作要求另一侧是 `Set`，不能把任意 iterable 当集合比较；
- `&`、`|`、`-`、`^` 及反向运算可接受一般 iterable，并返回具体 subclass；
- `isdisjoint()` 的正常工作流与发现首个交集后的短路；
- list-backed set 可保存不可哈希元素，同时保持去重、membership 与代数语义；
- 默认 `_from_iterable()` 假定 `Class(iterable)` 构造器；
- 具有额外构造参数的 subclass 必须 override `_from_iterable()`；
- Set mixin 不定义 `__hash__`，普通自定义 set 默认不可哈希；
- 不可变 subclass 可用 `__hash__ = Set._hash`，并与相等 `frozenset` 保持 hash 一致；
- 参与 `_hash()` 的元素自身仍必须可哈希；
- `MutableSet` 额外要求 `add()` 与 `discard()`；
- `discard` 对缺失值静默，`remove` 对缺失值抛 `KeyError`；
- `pop` 取 iteration 的首个值并 discard，空集合抛 `KeyError`；
- `clear` 反复 pop 直到空集合；
- `|=` / `&=` / `^=` / `-=` 原地修改并返回原对象；
- `values ^= values` 与 `values -= values` 的 self-alias 特殊路径会清空集合；
- mutation mixin 通过 add/discard primitive 维护具体实现定义的不变量。

## Common Pitfalls To Explain

- 把 Set ABC 当成使用 hash table 的保证；
- 认为集合运算结果一定是内置 set，而不是 `_from_iterable()` 创建的具体 class；
- 自定义构造器要求额外参数，却忘记覆盖 `_from_iterable()`；
- 因为 Set 提供 `_hash()` 就以为实例天然可哈希；
- 认为 `discard` 与 `remove` 对缺失值行为相同；
- 原地运算时忽略 `other is self`，边迭代边修改自身；
- 用无序容器的 pop 结果做固定值假设；测试只断言它来自原集合且已被删除。

## Target File

`languages/python/stdlib/data_types/test_052_collections_abc_sets.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.abc.html
- https://github.com/python/cpython/blob/3.10/Lib/_collections_abc.py
- https://docs.python.org/3.10/library/stdtypes.html#set-types-set-frozenset

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- list-backed set 构造时保留首次出现顺序，仅用于让测试结果稳定；
- 不宣称 Set ABC 有序；
- 自定义 primitive 可记录 add/discard 调用，展示 mixin 分派而非穷举内部调用次数；
- 用实际不可哈希元素证明接口不要求 hash table；
- Mapping/MutableMapping、mapping views 与异步 ABC 留给后续独立测试套；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--050 已完成此前范围首轮编写；051 `Sequence` / `MutableSequence` / `ByteString`
已在 `data_types/` 完成首轮静态编写，共 24 个测试，覆盖 primitive、mixin 分派、
IndexError 终止、切片责任、复杂度、mutation 组合与 byte sequence 注册关系。全部
Python 文件仍未运行。下一步直接编写 052 set mixin；不要先运行 pytest。
