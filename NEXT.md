# Current Task

ID: `python.stdlib.collections-user-wrappers`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.UserDict`、`UserList` 与 `UserString` 测试套：展示三种
标准包装器如何通过公开 `data` 属性复用内置容器协议，并作为比直接继承 `dict`、
`list`、`str` 更容易控制的自定义容器基类。

## Covers

- `UserDict(initialdata)` 将输入内容复制到独立普通 dict，不保留输入 mapping 引用；
- `UserDict.data`、映射协议、缺失 key、copy/update/fromkeys 与相等性；
- 通过 `__missing__`、`__setitem__` 创建规范化或校验型 mapping subclass；
- 说明通过 `.data` 直接写入会绕过 subclass 的公开 mutation hook；
- `UserList(iterable)` 将任意 iterable 内容复制到普通 list，并公开 `.data`；
- indexing/slicing、iteration、membership、append/extend/insert/pop/remove/reverse/sort；
- `+`、`*`、slice 等产生新 sequence 时保留实际 subclass 的构造器约定；
- 通过 `__setitem__` / `insert` / constructor 创建只接受特定值的 UserList subclass；
- subclass 构造器必须支持零参数或单 sequence 参数；
- 否则，返回新序列的继承操作可能失败；
- `UserString(seq)` 使用 `str(seq)` 初始化普通字符串 `.data`；
- string 的 indexing/slicing、comparison/hash、concatenation/repetition、常用转换和查询方法；
- UserString 本身包装不可变 str，但 `.data` 属性仍可重新绑定；
- 通过 subclass 增加规范化、校验或领域行为，并观察哪些运算保留 wrapper/subclass；
- 对比 wrapper 与直接继承内置类型时，内部真实存储和 override 路径的差异。

## Common Pitfalls To Explain

- 认为 UserDict/UserList 保留传入容器引用，外部 mutation 会自动同步；
- 误把 `.data` 当只读属性，或忘记直接修改它可能绕过自定义校验；
- subclass 只重写一个入口，却假设所有 inherited compound operation 都一定经过该入口；
- 给 UserList subclass 设计必需的额外构造参数，导致 slice/加法创建新实例失败；
- 把 UserString 的包装对象当真正 `str` subclass；
- 认为 UserString 完全不可改变，而忽略 `.data` 可被重新绑定；
- 未检查运算或方法的实际返回类型，错误期待所有结果都保留自定义 subclass。

## Target File

`languages/python/stdlib/data_types/test_049_userdict_userlist_userstring.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.html#userdict-objects
- https://docs.python.org/3.10/library/collections.html#userlist-objects
- https://docs.python.org/3.10/library/collections.html#userstring-objects
- https://github.com/python/cpython/blob/3.10/Lib/collections/__init__.py

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 每种 wrapper 至少包含一个有实际含义的 subclass，但不构造边缘情况矩阵；
- 对复制、alias、mutation hook 和返回类型使用精确断言；
- 需要解释内置类型继承差异时，使用最小对照片段，不扩展成完整 builtins 重测；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--047 已完成此前范围首轮编写；048 `ChainMap` / `namedtuple` 已在 `data_types/`
完成首轮静态编写，涵盖多层 view、作用域写入、配置优先级、tuple 协议、defaults、
rename、pickle 与无实例 dict 的 subclass。全部 Python 文件仍未运行。下一步直接编写
049 三种用户容器包装器；不要先运行 pytest。
