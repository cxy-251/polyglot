# Current Task

ID: `python.stdlib.struct`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `struct` 测试套，用可读的二进制记录案例讲清格式字符串、字节序、原生/标准大小与对齐、定长字段、buffer 原地读写和重复解析；同时明确哪些格式适合跨平台协议，哪些只适合当前机器内存布局。

## Covers

- `pack()` / `unpack()` 的 bytes 输出与 tuple 结果，以及 `calcsize()`；
- 格式前缀 `@`、`=`、`<`、`>`、`!` 对字节序、字段大小和自动对齐的不同影响；
- 无前缀时默认使用原生 `@`，不能把结果当作稳定跨平台格式；
- 格式中的空白、重复计数和相邻字段；
- 有符号/无符号整数代码与越界时的 `struct.error`；
- 非整数对象通过 `__index__()` 提供整数值，以及普通浮点数不能冒充整数；
- `?` 使用真假值打包布尔字段；
- `c`、`s`、`p`、`x` 分别表示单字节字符、定长字节串、Pascal 字符串和填充字节；
- `s` 前的计数是一个字段的字节长度，而数字代码和 `c` 前的计数表示重复字段；
- `e`、`f`、`d` 浮点格式和近似比较，不对不可精确表示的小数写精确相等断言；
- 原生专用的 `n`、`N`、`P`，以及它们不能用于标准字节序格式；
- `pack_into()` 写入可写 buffer 的指定 offset；
- `unpack_from()` 从更大 buffer 的指定 offset 读取，不要求整个 buffer 长度恰好等于记录；
- `iter_unpack()` 连续解析固定长度记录，输入长度必须是记录大小的整数倍；
- `Struct` 预编译格式的 `format`、`size`、`pack`、`unpack`、`pack_into`、`unpack_from` 和 `iter_unpack`；
- buffer 太小、`unpack()` 有多余/不足字节、参数数量或类型错误时的失败边界。

## Common Pitfalls To Explain

- 用默认 `@` 生成磁盘或网络格式，忽略平台字节序、C 类型大小和对齐差异；
- 把 `=` 误解成“小端”或“原生对齐”；它使用原生字节序，但使用标准大小且不自动对齐；
- 误把 `4s` 当作四个独立值，或误把 `4c` 当作一个四字节字段；
- 给 `s` / `c` 传 `str` 而不是 bytes-like 值；
- 忘记定长 `s` 会截断过长输入并用 NUL 填充过短输入，解包后需要按协议自行去填充；
- 认为 `?` 只接受 `True` / `False`，忽略它按真假值转换；
- 对二进制浮点值使用精确相等断言；
- 用 `unpack()` 读取带 header/trailer 的较大 buffer，而不是 `unpack_from()`；
- 假设 `iter_unpack()` 会容忍末尾半条记录；
- 认为 `struct` 自带消息边界、校验、版本控制或字符串编码。

## Target File

`languages/python/stdlib/binary_data/test_041_struct_binary_layouts.py`

## Official Sources

- https://docs.python.org/3.10/library/struct.html

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 使用小型、带字段含义的记录格式，不把案例写成无语义的数字矩阵；
- 平台相关断言用 `sys.byteorder`、`calcsize()` 或原生格式自身推导，不硬编码当前主机布局；
- 跨平台协议示例显式选择 `<`、`>` 或 `!`；
- 错误案例精确展示失败原因，但不穷举每个格式代码的每个边界；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--035 已归入 `file_and_directory_access/`，036--040 已归入 `text_processing/`。040 `readline` / `rlcompleter` 已完成首轮静态编写，全部 Python 文件仍未运行。下一步创建 `binary_data/` 并直接编写 041 `struct`；不要先运行 pytest。
