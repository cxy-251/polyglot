# Current Task

ID: `python.stdlib.collections-abc-interface-detection`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.abc` 接口识别与基础协议测试套：展示直接继承、虚拟
注册、结构化 `__subclasshook__` 三种 ABC 判定路径，以及简单容器协议、迭代 fallback
和 GenericAlias 的真实边界。复杂的 Sequence/Set/Mapping mixin 与异步 ABC 留给后续
独立主题。

## Covers

- 直接继承 ABC 时必须实现 abstract methods，否则 class 可定义但不能实例化；
- 实现必需方法后，继承关系同时支持 `issubclass()` 与 `isinstance()`；
- `ABC.register()` 建立 virtual subclass，不改变目标类 MRO，也不注入 mixin 方法；
- register 可作为 decorator，并返回原 class；
- virtual subclass 仍由作者负责完整接口语义，注册本身不验证实现质量；
- `Container`、`Hashable`、`Sized`、`Callable`、`Iterable` 等简单 ABC 的结构化识别；
- 将协议方法显式设为 `None` 会阻止简单 ABC 的 `__subclasshook__` 识别；
- `Collection` 同时要求 `__contains__`、`__iter__`、`__len__`；
- `Iterator` 要求 `__next__`，并从 ABC 获得返回自身的 `__iter__` mixin；
- `Reversible` 对显式 `__reversed__` 的识别，以及 `reversed()` 的 sequence fallback；
- 旧式 `__getitem__` sequence 可以被 `iter()` 消费，却不一定是 `Iterable` instance；
- 因此判断对象能否迭代的可靠操作是尝试 `iter(obj)`，不能只依赖 `isinstance`；
- `Hashable` 识别 `__hash__ = None` 的不可哈希类型，并区分会在调用时抛错的坏实现；
- 复杂接口不会仅因同名方法存在就自动成为 `Sequence` 或 `Mapping`；
- Python 3.9+ ABC 支持 `Iterable[int]` 等 GenericAlias，用于注解但不用于参数化
  `isinstance()`；
- 常见内置类型与 `Container` / `Collection` / `Sequence` / `Mapping` 的关系作最小对照。

## Common Pitfalls To Explain

- 认为只要继承 ABC 就能实例化，忽略仍未实现的 abstract methods；
- 把 virtual registration 当运行时适配器，期待它自动补齐方法；
- 认为 ABC 检查会执行并验证方法语义；它通常只判断继承、注册或方法存在；
- 用 `isinstance(value, Iterable)` 代替真正的 `iter(value)` 能力测试；
- 因为 `reversed(obj)` 成功，就断言 obj 一定是 `Reversible`；
- 自定义 `__hash__` 仅在调用时失败，却误以为 `Hashable` 能提前发现；
- 将 `Iterable[int]` 之类参数化别名传入 `isinstance()`。

## Target File

`languages/python/stdlib/data_types/test_050_collections_abc_interfaces.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.abc.html
- https://github.com/python/cpython/blob/3.10/Lib/_collections_abc.py
- https://docs.python.org/3.10/library/abc.html
- https://docs.python.org/3.10/reference/datamodel.html#object.__iter__

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 自定义协议类型只实现当前断言所需方法，并用有意义的小型容器数据；
- 不在本文件展开 Sequence/MutableSequence、Set/MutableSet、Mapping/MutableMapping 的
  全套 mixin；它们将在下一套集中展示；
- 不在本文件展开 Awaitable/Coroutine/AsyncIterator/AsyncGenerator；
- 对 ABC 判定与操作实际成功分别断言，明确两者并不总是等价；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--048 已完成此前范围首轮编写；049 `UserDict` / `UserList` / `UserString` 已在
`data_types/` 完成首轮静态编写，共 25 个测试，覆盖复制、协议、mutation hook、
返回类型、subclass 构造器约定与 `.data` 绕过路径。全部 Python 文件仍未运行。
下一步直接编写 050 `collections.abc` 接口识别与简单协议；不要先运行 pytest。
