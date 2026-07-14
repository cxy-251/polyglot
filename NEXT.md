# Current Task

ID: `python.stdlib.collections-abc-mutable-mapping-mixins`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.abc.MutableMapping` 测试套：用记录 primitive 调用的
最小 dict-backed mapping 展示 `pop`、`popitem`、`clear`、`update` 与 `setdefault`
mixin 的精确组合路径、输入分支、返回值和非原子失败边界。

## Covers

- `MutableMapping` 在 Mapping 三项 primitive 之外要求 `__setitem__` 与 `__delitem__`；
- `pop(key)` 先 lookup 再 delete，返回 value；缺失且无 default 时保留 `KeyError`；
- `pop(key, default)` 对缺失 key 返回 default，包括显式传入 `None`，且不执行 delete；
- `popitem()` 使用 `next(iter(self))` 取得某个 key，再 lookup/delete；
- 自定义 insertion-ordered 实现会弹出首个 key，但 ABC 不保证顺序；
- built-in dict 覆盖 popitem 并使用 LIFO，不能把它反推为 mixin 语义；
- 空 mapping 的 `popitem()` 抛 `KeyError`；
- `clear()` 反复 popitem，直至以空 mapping 的 `KeyError` 结束；
- `update(other)` 对真正 `Mapping` 按 key iteration + lookup 写入；
- 非 Mapping 但有 `keys()` 的 mapping-like 对象走单独分支；
- 无 `keys()` 的 iterable 必须产生 `(key, value)` pair；
- keyword arguments 最后写入，因此覆盖前面来源的同名 key；
- update/setdefault 通过 `self[key] = value`，会触发具体 `__setitem__` hook；
- `setdefault` 对已存在 key 只 lookup，不写入；缺失时写 default 并返回；
- lookup 返回假值仍属于已存在，不会触发 default；
- iterable update 或校验 hook 中途失败时，已完成的早期写入不会自动回滚；
- malformed pair 的 `ValueError` / 不可迭代输入 `TypeError` 与已写入状态；
- mutation mixin 的返回值遵循 dict：update/clear/setdefault 的相应约定；
- 直接修改具体 storage 仍可绕过 `__setitem__` 领域约束；
- dict 是已注册 MutableMapping，但其 C 方法可覆盖 ABC 默认分派与顺序。

## Common Pitfalls To Explain

- 认为 MutableMapping mixin 提供事务性 update；
- 混淆 `pop(key, None)` 与省略 default 的异常语义；
- 把 ABC popitem 当 built-in dict 的 LIFO；
- mapping-like 对象有 `keys()` 时，误以为 update 会把它当 pair iterable；
- 认为 keyword 参数先应用，不会覆盖 positional source；
- 自定义 `__getitem__` 对缺失 key 返回 fallback，导致 setdefault 无法判断应否插入；
- 只在 `__setitem__` 校验，却允许调用方直接修改公开底层存储。

## Target File

`languages/python/stdlib/data_types/test_054_collections_abc_mutable_mappings.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.abc.html
- https://github.com/python/cpython/blob/3.10/Lib/_collections_abc.py
- https://docs.python.org/3.10/library/stdtypes.html#mapping-types-dict

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 自定义 mapping 使用 insertion-ordered dict 存储并记录 get/set/del/iter 调用；
- 对 popitem 只把“首个 key”称为该测试实现的结果，不宣称 ABC 有顺序保证；
- update 三种 input branch 各给一个有语义案例，不扩展成畸形 pair 矩阵；
- 中途失败案例明确断言已发生的写入，避免误导为原子操作；
- Generator/Awaitable/Coroutine 与 async ABC 留给下一套；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--052 已完成此前范围首轮编写；053 read-only `Mapping` 与 views 已在
`data_types/` 完成首轮静态编写，共 19 个测试，覆盖查询 mixin、异常边界、live view、
key/item 集合语义、value 重复、反向能力、dict view 和 mapping proxy。全部 Python
文件仍未运行。下一步直接编写 054 MutableMapping mixin；不要先运行 pytest。
