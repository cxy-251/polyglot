# Current Task

ID: `python.stdlib.stringprep`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `stringprep` 测试套，覆盖 RFC 3454 的映射、禁止字符与双向分类表，并明确该模块是基于 Unicode 3.2 的低层 table toolkit，而不是可直接用于现代用户名/域名的完整验证器。

## Covers

- `stringprep` 与 `unicodedata.ucd_3_2_0` 的固定 Unicode 3.2 数据边界；
- A.1 `in_table_a1()` 对 Unicode 3.2 未分配 code point 的判断；
- B.1 `in_table_b1()` 的“mapped to nothing”字符；
- B.2 `map_table_b2()` 与 B.3 `map_table_b3()` 的 case mapping，以及 B.2 额外 NFKC 稳定化步骤；
- C.1.1 `in_table_c11()` ASCII space 与 C.1.2 `in_table_c12()` non-ASCII space；
- C.2.1 `in_table_c21()` ASCII control 与 C.2.2 `in_table_c22()` non-ASCII control；
- C.3 `in_table_c3()` private-use、C.4 `in_table_c4()` non-character；
- C.5 `in_table_c5()` surrogate code point；
- C.6 `in_table_c6()` inappropriate for plain text；
- C.7 `in_table_c7()` inappropriate for canonical representation；
- C.8 `in_table_c8()` change display properties/deprecated；
- C.9 `in_table_c9()` tagging characters；
- D.1 `in_table_d1()` RandALCat 与 D.2 `in_table_d2()` LCat；
- table predicate 的单字符输入契约与返回 bool；
- 一个小型 profile pipeline：逐字符映射、NFKC、prohibited 检查和 bidi 规则；
- profile 必须自行决定采用哪些 tables、处理顺序、错误模型与 Unicode 版本。

## Common Pitfalls To Explain

- 把 `stringprep` 当成一个接收整串并返回已验证结果的高层函数；
- 忘记它锁定 Unicode 3.2，拿现代 Unicode 分配状态直接解释 A.1；
- 只做 B.2/B.3 case mapping，漏掉 profile 要求的 normalization/prohibited/bidi 阶段；
- 把所有 C.* 表无条件合并，却没有遵循目标 profile 的 RFC；
- 认为 private-use、non-character、surrogate 都会由普通 `str` 自动拒绝；
- 只检查是否含 RandALCat，却不验证首尾和 LCat 混用规则；
- 用过时 Stringprep 自行替代 IDNA 2008、PRECIS 或具体协议的现行规范；
- 对 predicate 传入多字符字符串并期待逐字符扫描。

## Target File

`languages/python/stdlib/test_039_stringprep.py`

## Official Sources

- https://docs.python.org/3.10/library/stringprep.html
- https://www.rfc-editor.org/rfc/rfc3454

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 中文注释区分 table primitive 与完整 profile，并标明示例 code point 所属表；
- profile 示例必须保持小型、明确声明是教学实现，不冒充 Nameprep/SASLprep；
- surrogate 仅作为 Python 字符值做分类，不编码/写入文件或终端；
- 数据全部内嵌，不访问网络、locale 或外部文件；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--038 已完成文件/目录访问、正则和主要文本处理内容。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 039 stringprep；不要先运行 pytest。
