# Current Task

ID: `python.stdlib.collections-chainmap-namedtuple`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.ChainMap` 与 `namedtuple()` 测试套：展示不复制数据的多层配置/作用域视图，以及兼具 tuple 协议、字段名称和轻量不可变记录的生成类；覆盖引用传播、写入层、迭代顺序、3.10 `new_child` kwargs 与 namedtuple introspection/defaults/rename/subclass 边界。

## Covers

- `ChainMap(*maps)` 保存公开 `maps` list 并按从前到后优先级查找；
- 不传 mapping 时自动创建一个空 dict；
- 底层 mapping 按引用纳入，外部修改立即反映，ChainMap 不是 flatten copy；
- lookup/membership 检查所有层，赋值/update/setdefault 只写第一层；
- `del` / `pop` 只操作第一层，即使 key 存在于父层也不会深删；
- iteration/key/item 顺序按最后一层到第一层做 dict-update 式合并，与 lookup 方向不同；
- `new_child()` 添加局部 scope，不修改父 chain；
- `new_child(m)` 使用显式前置 mapping；
- Python 3.10 `new_child(**kwargs)` 初始化新 scope，及同时传 m/kwargs 的更新语义；
- `parents` 跳过第一层，`maps` 可显式重排/替换搜索链；
- `dict(chain)` flatten snapshot 与继续引用的 ChainMap view 差别；
- `|` / `|=` mapping merge 的层和值边界；
- 命令行 > environment > defaults 的实际配置优先级工作流；
- 最小 `DeepChainMap` subclass 将写/删路由到首次包含 key 的深层 mapping，并说明这不是默认行为；
- `namedtuple(typename, field_names)` 接受空白/逗号字符串或 iterable；
- 生成类是 tuple subclass，支持索引、迭代、unpack、比较、hash，实例无 per-instance `__dict__`；
- 字段 attribute、可读 repr 和不可变赋值边界；
- `_make()` 从 iterable 构造，长度不匹配失败；
- `_asdict()` 在 Python 3.10 返回保序普通 dict；
- `_replace()` 返回新实例且拒绝未知 field；
- `_fields` 用于 introspection/组合新 record；
- `defaults` 只从最右字段开始，`_field_defaults` 暴露映射；
- `rename=True` 将 keyword、重复、下划线开头等非法字段替换为位置名；默认 `rename=False` 抛 `ValueError`；
- `module=` 控制生成类的 `__module__`，以及 pickle 仍要求模块中有与 typename 匹配的绑定；
- 通过 `__slots__ = ()` subclass 添加计算属性/自定义 docstring，不引入实例 dict。

## Common Pitfalls To Explain

- 把 ChainMap 当数据副本，忽略底层 dict 后续修改会透出；
- 认为赋值/删除会修改找到 key 的那一层；默认永远只写/删第一层；
- 混淆 lookup 从前到后与 iteration 从后到前的顺序；
- 将 `dict(chain)` snapshot 后仍期待它随底层 mapping 更新；
- 直接修改 `maps` 后忘记优先级也随之改变；
- 把 namedtuple 当可变对象，尝试属性赋值；
- 认为 `_replace()` 原地修改；
- 把 defaults 当从左侧字段开始；
- 在 3.10 仍假设 `_asdict()` 返回 OrderedDict；
- 生成 namedtuple 后未绑定到与 typename 一致的模块级名字，却期待 pickle 能按类名恢复；
- subclass namedtuple 时忘记 `__slots__ = ()`，意外增加实例存储。

## Target File

`languages/python/stdlib/data_types/test_048_chainmap_namedtuple.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.html#chainmap-objects
- https://docs.python.org/3.10/library/collections.html#collections.namedtuple

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- ChainMap 使用配置层/嵌套 scope 的有语义案例；
- DeepChainMap subclass 只实现当前教学所需 `__setitem__` / `__delitem__`；
- namedtuple 生成类名称清楚，辅助方法按官方下划线命名使用；
- pickle 只解释/验证可稳定隔离的类绑定，不依赖测试模块的偶然导入名；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--046 已完成此前范围首轮编写；047 `deque` / `OrderedDict` 已在 `data_types/` 完成首轮静态编写，包含 bounded/window/round-robin 与显式顺序/LRU 工作流。全部 Python 文件仍未运行。下一步直接编写 048 `ChainMap` / `namedtuple`；不要先运行 pytest。
