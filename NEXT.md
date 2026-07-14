# Current Task

ID: `python.stdlib.collections-abc-sequence-mixins`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.abc.Sequence`、`MutableSequence` 与 `ByteString` 测试套：
用最小自定义容器展示 abstract primitive 如何生成完整 sequence API、mixin 的真实
分派路径，以及 slicing、负索引、构造器和算法复杂度仍由实现者承担的边界。

## Covers

- `Sequence` 直接继承要求 `__getitem__` 与 `__len__`，缺少任一方法不能实例化；
- mixin 自动提供 `__contains__`、`__iter__`、`__reversed__`、`index()`、`count()`；
- primitive `__getitem__` 必须以 `IndexError` 表示结束，否则 iteration mixin 不会终止；
- negative index 与 slice 语义不会由 ABC 自动补齐，必须在 `__getitem__` 中实现；
- `index(value, start, stop)`、`count(value)` 和 equality 调用的正常工作流；
- mixin `__iter__` / `__reversed__` / `index` 会重复调用 `__getitem__`；
- 若 primitive access 是线性时间，默认 mixin 可能退化为平方复杂度；
- 自定义 `__iter__` 可以绕开昂贵随机访问，但不改变 Sequence 的其他语义；
- `MutableSequence` 额外要求 `__setitem__`、`__delitem__` 与 `insert()`；
- append/extend/`+=`、pop/remove/reverse 等 mixin 如何委托 primitive mutation hooks；
- scalar 与 slice 的赋值/删除都进入同一个 `__setitem__` / `__delitem__`，实现者负责区分；
- `insert` 对负数和越界位置的 list-like 归一化由具体实现决定；
- 失败 mutation 的异常类型和原容器不变性；
- mixin mutation 方法的返回值遵循 list 约定，`+=` 返回原对象；
- `ByteString` 是只读 byte sequence ABC；bytes/bytearray 的注册关系与元素为 int 的语义；
- 仅实现 Sequence primitives 的任意对象不会自动结构化成为 Sequence/ByteString。

## Common Pitfalls To Explain

- 认为继承 Sequence 就自动获得 slicing 或负索引处理；
- `__getitem__` 越界返回 sentinel 而非抛 `IndexError`，导致默认迭代无限继续；
- 用链表等线性索引存储却直接接受默认 iteration/index mixin 的复杂度；
- MutableSequence 只实现单元素 mutation，忘记 slice 会传入 `slice` 对象；
- 误以为 mixin 会自动校验元素类型或维护领域不变量；
- 认为 virtual/structural Sequence 判定会注入 mixin；该内容已在 050 说明，051 只处理
  真实继承；
- 把 ByteString 当作“元素为 bytes”的序列，忽略 bytes 索引结果是整数。

## Target File

`languages/python/stdlib/data_types/test_051_collections_abc_sequences.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.abc.html
- https://github.com/python/cpython/blob/3.10/Lib/_collections_abc.py
- https://docs.python.org/3.10/reference/datamodel.html#emulating-container-types
- https://docs.python.org/3.10/library/stdtypes.html#common-sequence-operations

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 自定义只读和可变 sequence 使用小型内存数据，不依赖 049 的 UserList；
- primitive hook 可记录调用，用断言展示 mixin 分派，但不要制造调用次数穷举矩阵；
- 明确展示 slicing/negative index 是具体容器责任，不把故意残缺实现称为推荐模板；
- Set/MutableSet、Mapping/MutableMapping 与异步 ABC 留给后续独立测试套；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--049 已完成此前范围首轮编写；050 `collections.abc` 接口识别与简单协议已在
`data_types/` 完成首轮静态编写，共 17 个测试，覆盖直接继承、虚拟注册、
结构识别、Iterable/Iterator/Reversible/Hashable fallback 与 GenericAlias 边界。全部 Python
文件仍未运行。下一步直接编写 051 sequence mixin；不要先运行 pytest。
