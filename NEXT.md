# Current Task

ID: `python.stdlib.collections-abc-mapping-views`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.abc.Mapping`、`MappingView`、`KeysView`、`ItemsView` 与
`ValuesView` 测试套：用最小只读映射展示三项 primitive 生成的查询 API、live view、
set-like keys/items 语义，以及异常、比较与反向迭代的真实边界。

## Covers

- `Mapping` 直接继承要求 `__getitem__`、`__iter__`、`__len__`；
- mapping `__iter__` 应产生 key，而不是 value 或 item；
- `get(key, default)` 通过 `self[key]`，仅捕获 `KeyError`；
- `in` mixin 同样调用 `self[key]` 并仅以 `KeyError` 判断 key 缺失；
- 返回 `None` 等假值的已存在 key 仍属于 mapping；
- `keys()`、`items()`、`values()` 默认创建保存 mapping 引用的 live views；
- 底层映射更新后，已有 view 的长度、membership 与 iteration 立即反映变化；
- `KeysView` 是 Set，支持比较与集合代数，运算结果由 `_from_iterable()` 生成普通 set；
- `ItemsView` 是 Set，membership 按 `(key, value)` 检查并优先使用 value identity；
- item value 不可哈希时，membership/iteration 仍可工作；
- 但某些 set 运算结果无法哈希 pair；
- `ValuesView` 是 Collection 而不是 Set，可包含重复值且不提供集合代数；
- view iteration 顺序跟随具体 mapping，不由 ABC 另行排序；
- `Mapping.__eq__` 仅与另一 Mapping 比较，通过 items 内容忽略 iteration order；
- 默认 Mapping 显式将 `__reversed__` 设为 `None`；具体实现需自行提供反向 key iteration；
- `MappingView` 的长度与 repr 基础行为；
- built-in dict views 与 ABC 的注册关系，以及 `types.MappingProxyType` 的只读 Mapping 关系；
- Python 3.9+ `Mapping[str, int]` / `KeysView[str]` GenericAlias 基础元数据。

## Common Pitfalls To Explain

- 自定义 Mapping 的 `__iter__` 返回 value，导致 dict()、views 和 mixin 全部错位；
- 用 value truthiness 判断 key 是否存在；
- 认为 get/contains 会吞掉 `TypeError`、网络错误等所有 lookup 异常；
- 把 view 当创建时的 list snapshot，忽略它持有底层 mapping 引用；
- 认为 values view 会去重或支持 `&` / `|`；
- 对包含不可哈希 value 的 ItemsView 无条件执行会物化 set 的代数运算；
- 因 built-in dict 支持 `reversed()`，误以为 Mapping mixin 也自动提供；
- 参数化 Mapping alias 不可传入 `isinstance()`；050 已说明，本文件只做元数据对照。

## Target File

`languages/python/stdlib/data_types/test_053_collections_abc_mappings.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.abc.html
- https://github.com/python/cpython/blob/3.10/Lib/_collections_abc.py
- https://docs.python.org/3.10/library/stdtypes.html#dictionary-view-objects
- https://docs.python.org/3.10/library/types.html#types.MappingProxyType

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 只读 mapping 用稳定 insertion order 的内存存储，让 view 断言可读；
- 对 live view 先创建 view 再修改具体存储，明确证明不是 snapshot；
- set-like view 只选常用运算，不复制 052 的完整 Set mixin 矩阵；
- MutableMapping 写入 mixin 与异步 ABC 留给后续独立测试套；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--051 已完成此前范围首轮编写；052 `Set` / `MutableSet` 已在 `data_types/` 完成
首轮静态编写，共 23 个测试，覆盖不可哈希元素、集合代数、`_from_iterable`、
可选 hash、add/discard 分派和四种原地运算。全部 Python 文件仍未运行。下一步
直接编写 053 read-only Mapping 与 views；不要先运行 pytest。
