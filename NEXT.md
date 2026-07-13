# Current Task

ID: `python.builtins.mapping-dict`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `dict` 映射类型测试套，展示构造、键契约、顺序、动态视图、读取/写入/删除方法、合并和浅拷贝，并讲清楚共享默认值与迭代期间修改等真实陷阱。

## Covers

- 字面量、dict comprehension、关键字/键值 iterable/另一个 mapping 构造；
- 重复键与后写值覆盖、插入顺序不因覆盖已有键而改变；
- hashable key 契约，以及数值相等键的碰撞；
- `d[key]`、`get()`、`setdefault()`、`__missing__()` 的差异；
- 索引写入、`update()`、`|` / `|=` 的左右覆盖和返回/原地语义；
- `keys()` / `values()` / `items()` 动态视图与 keys/items 集合运算；
- 正向/反向迭代遵循插入顺序；
- `pop()` / `popitem()` / `del` / `clear()` 的返回值和异常；
- `copy()` 与 `dict(existing)` 的浅拷贝边界；
- `dict.fromkeys()` 对同一个可变默认对象的复用；
- `setdefault()` 默认表达式的预先求值和常用分组模式；
- 迭代期间改变大小导致 RuntimeError，以及基于快照/推导式的安全改写；
- dict equality 与顺序无关，但 `list(d)` / `repr` 等观察顺序有关。

## Common Pitfalls To Explain

- 使用 list/dict/set 作为键；
- 忘记 `True`、`1`、`1.0` 作为键会碰撞；
- 用 `get(key)` 无法区分缺失与显式存储 None；
- 用 `dict.fromkeys(keys, [])` 创建每键独立列表；
- 认为 `setdefault(key, expensive())` 只在缺失时才计算默认值；
- 认为覆盖已有键会把键移动到字典末尾；
- 遍历 dict 时直接增删键；
- 把浅拷贝当作嵌套结构隔离；
- 忽略 `left | right` 中右侧同名键获胜。

## Target File

`languages/python/builtins/test_024_mapping_dict.py`

## Official Sources

- https://docs.python.org/3.10/library/stdtypes.html#mapping-types-dict
- https://docs.python.org/3.10/library/stdtypes.html#dictionary-view-objects
- https://docs.python.org/3.10/library/stdtypes.html#dict
- https://docs.python.org/3.10/library/functions.html#dict
- https://docs.python.org/3.10/reference/datamodel.html#object.__hash__
- https://docs.python.org/3.10/reference/datamodel.html#object.__missing__
- https://peps.python.org/pep-0584/

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释解释键的 equality/hash 契约、动态视图和共享引用；
- 按实际配置合并、分组和索引工作流组织案例；
- 与 002/014 的 equality/hash 协议、017 的 dict display/comprehension 避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--023 位于 `builtins/`，编号在整个 Python 树全局连续。023 list/tuple/range 已完成首轮编写，尚未运行。下一步直接编写 024 dict；不要先运行 pytest。
