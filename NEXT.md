# Current Task

ID: `python.builtins.text-sequence-str`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `str` 文本序列测试套，集中展示 Unicode 字符串字面量、不可变序列行为、查找/拆分/拼接/清理/替换、大小写与字符分类、编码边界，以及真实文本处理中最常见的语义陷阱。

## Covers

- 单/双/三引号、转义、raw string、相邻字面量拼接；
- Unicode code point、`ord()` / `chr()`、`len()` 与用户感知字符数的区别；
- 索引、切片、步长、成员判断和不可变性；
- `find()` / `index()` / `count()` / `startswith()` / `endswith()`；
- `split()`、无参数空白折叠、显式分隔符、`rsplit()`、`splitlines()`；
- `partition()` / `rpartition()` 总是返回三元组；
- `join()` 的调用方向、只接受 str 元素以及空/单元素行为；
- `strip()` / `lstrip()` / `rstrip()` 的字符集合语义；
- `removeprefix()` / `removesuffix()` 与误用 strip 的区别；
- `replace()`、`translate()` / `str.maketrans()`；
- `lower()` / `upper()` / `casefold()`、`swapcase()` / `title()` / `capitalize()`；
- `isalpha()` / `isdecimal()` / `isdigit()` / `isnumeric()` / `isspace()` / `isidentifier()`；
- 对齐与填充：`center()` / `ljust()` / `rjust()` / `zfill()`；
- `encode()` 的编码和 errors 策略，以及 bytes/str 边界；
- `%`、`str.format()`、`format_map()` 只做 str 类型入口，格式迷你语言细节与 014 交叉引用。

## Common Pitfalls To Explain

- 把 Python `len(str)` 当作屏幕字符宽度、字节数或 grapheme cluster 数；
- raw string 末尾写单个反斜杠；
- 用 `strip("prefix")` 删除固定前后缀；
- 混淆 `split()` 与 `split(" ")` 的空字段和空白折叠规则；
- 写成 `items.join(",")`，或让 join 隐式转换非 str 元素；
- 用 `lower()` 做不区分大小写的 Unicode 比较，而未考虑 `casefold()`；
- 把 `isdigit()` 等字符分类方法当作可直接交给 `int()` 的完整语法验证；
- 在 str 与 bytes 之间隐式混用，或用默认编码掩盖协议边界。

## Target File

`languages/python/builtins/test_021_text_sequence_str.py`

## Official Sources

- https://docs.python.org/3.10/library/stdtypes.html#text-sequence-type-str
- https://docs.python.org/3.10/library/stdtypes.html#string-methods
- https://docs.python.org/3.10/library/functions.html#str
- https://docs.python.org/3.10/library/functions.html#ord
- https://docs.python.org/3.10/library/functions.html#chr
- https://docs.python.org/3.10/reference/lexical_analysis.html#string-and-bytes-literals
- https://docs.python.org/3.10/howto/unicode.html

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释解释 Unicode、分隔/清理规则和 str/bytes 边界；
- 不把所有方法机械拆成一方法一测试；按实际文本工作流组织案例；
- 与 005 的通用序列订阅、014 的 `__format__` 协议避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--020 位于 `builtins/`，编号在整个 Python 树全局连续。020 float/complex 已完成首轮编写，尚未运行。下一步直接编写 021 str；不要先运行 pytest。
