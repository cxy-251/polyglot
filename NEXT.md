# Current Task

ID: `python.builtins.binary-sequences`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `bytes`、`bytearray` 与 `memoryview` 二进制序列测试套，展示三者在构造、索引、切片、编解码、十六进制转换、可变性和零拷贝视图方面的共同点与关键差异。

## Covers

- bytes 字面量、ASCII 源码限制和十六进制/转义字节；
- `bytes()` 从长度、整数 iterable、buffer 和文本+encoding 构造；
- 索引返回 int、切片返回同类二进制序列，以及与 str 索引的区别；
- bytes 的不可变性，bytearray 的索引/切片写入和改变长度操作；
- `decode()` 与 str `encode()` 往返、errors 策略和 BOM/协议编码边界；
- `hex()` / `fromhex()`、分隔符参数和可读的二进制诊断；
- 二进制 `find()` / `index()` / `count()` / `split()` / `partition()` / `join()`；
- bytes/bytearray 的 ASCII 导向大小写和字符分类方法限制；
- bytes `%` 格式化作为面向二进制协议的入口；
- `memoryview()` 暴露底层 buffer、切片共享、只读/可写区别；
- memoryview 的 `format` / `itemsize` / `ndim` / `shape` / `strides` / `nbytes`；
- `cast()` 的形状/格式约束、`tobytes()` / `tolist()`、`readonly`；
- `release()` / 上下文管理器，以及视图存活时 bytearray 不能改变大小；
- 相等比较与 hashability 的可变/只读边界。

## Common Pitfalls To Explain

- 误以为 `bytes(5)` 得到文本 `b"5"`，而实际得到五个零字节；
- 忘记 bytes 索引返回 0--255 的 int，而非长度 1 的 bytes；
- 用 str 方法语义理解 bytes 的 ASCII-only 大小写/分类操作；
- 在协议边界隐式混用 str 与 bytes，或错误猜测编码；
- 把 memoryview 切片当独立副本，意外改写原 bytearray；
- 持有导出视图时调整 bytearray 长度，触发 BufferError；
- 认为 memoryview 永远可写、连续或可 hash。

## Target File

`languages/python/builtins/test_022_binary_sequences.py`

## Official Sources

- https://docs.python.org/3.10/library/stdtypes.html#binary-sequence-types-bytes-bytearray-memoryview
- https://docs.python.org/3.10/library/stdtypes.html#bytes-objects
- https://docs.python.org/3.10/library/stdtypes.html#bytearray-objects
- https://docs.python.org/3.10/library/stdtypes.html#bytes-and-bytearray-operations
- https://docs.python.org/3.10/library/stdtypes.html#printf-style-bytes-formatting
- https://docs.python.org/3.10/library/stdtypes.html#memory-views
- https://docs.python.org/3.10/library/functions.html#bytes
- https://docs.python.org/3.10/library/functions.html#bytearray
- https://docs.python.org/3.10/library/functions.html#memoryview

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释重点解释文本/字节边界、复制/共享和可变性；
- 使用 bytearray 等内存数据，不访问真实设备、网络或持久文件；
- 与 005 的通用订阅协议、021 的 str 编解码避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--021 位于 `builtins/`，编号在整个 Python 树全局连续。021 str 已完成首轮编写，尚未运行。下一步直接编写 022 bytes/bytearray/memoryview；不要先运行 pytest。
