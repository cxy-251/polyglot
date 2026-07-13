# Current Task

ID: `python.stdlib.re`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `re` 正则表达式测试套，覆盖 pattern 编译、匹配入口、分组/回溯引用、flags、替换/拆分、bytes 模式和常见性能/转义陷阱。

## Covers

- raw string 与 Python 字符串转义/正则转义的双层语法；
- `compile()`、Pattern 属性、模块函数与缓存/`purge()`；
- `search()` / `match()` / `fullmatch()` 的起点和整串差异；
- `findall()` 返回形状受捕获组数量影响，`finditer()` 返回 Match；
- `split()` 保留捕获分隔符、maxsplit 和空匹配边界；
- `sub()` / `subn()`、count、replacement backreference 和 callable replacement；
- `escape()` 只用于字面 pattern，不应用于 replacement；
- Match `group()` / `groups()` / `groupdict()` / `start()` / `end()` / `span()`；
- named group、numbered/named backreference、non-capturing group；
- greedy/lazy quantifier、alternation 左到右、anchors；
- character classes、Unicode/ASCII `\w` / `\d` / `\s`；
- IGNORECASE / MULTILINE / DOTALL / VERBOSE / ASCII flags；
- lookahead/lookbehind（固定长度限制）和边界；
- str pattern/subject 与 bytes pattern/subject 类型必须一致；
- `re.error` 的 msg/pattern/pos/lineno/colno；
- 零长度匹配推进规则和灾难性回溯风险。

## Common Pitfalls To Explain

- 忘记 raw string，反斜杠先被 Python 字符串吃掉；
- 用 match 代替 fullmatch 做完整输入校验；
- 在 findall 增加捕获括号后返回形状意外改变；
- replacement 中 `\1` 与 `\g<1>`/八进制歧义；
- 默认 `.` 不跨换行，`^/$` 与 MULTILINE 语义混淆；
- 认为 IGNORECASE 只处理 ASCII；
- 混用 str 与 bytes；
- 用 `re.escape()` 处理 replacement；
- 无界嵌套量词造成灾难性回溯；
- 把正则用于需要解析器的递归/结构化语言。

## Target File

`languages/python/stdlib/test_036_regular_expressions.py`

## Official Sources

- https://docs.python.org/3.10/library/re.html
- https://docs.python.org/3.10/howto/regex.html

## Authoring Requirements

- 使用 pytest 普通测试函数，不引入第三方 regex 包；
- 中文注释解释双层转义、匹配入口、捕获返回形状和回溯风险；
- 性能陷阱只用小输入说明结构，不写可能长时间阻塞的压力案例；
- 测试数据固定且不读取外部文件；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--035 已完成文件和目录访问类别首轮编写。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 036 re；不要先运行 pytest。
