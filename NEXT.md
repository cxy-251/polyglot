# Current Task

ID: `python.stdlib.difflib`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `difflib` 测试套，覆盖通用序列匹配、opcode 分组、人类可读文本差异、差异恢复、bytes 代理以及相似候选检索，并解释启发式算法与机器补丁格式之间的边界。

## Covers

- `SequenceMatcher(isjunk, a, b, autojunk)` 的 hashable 元素要求和序列缓存模型；
- `set_seq1()` / `set_seq2()` / `set_seqs()` 在一对多比较中的复用方式；
- 自定义 `isjunk` 对空白等噪声元素的处理，以及 junk 仍可扩展相邻匹配的语义；
- `find_longest_match()` 的 tie-breaking、`alo` / `ahi` / `blo` / `bhi` 范围；
- `get_matching_blocks()` 的有序非重叠结果与末尾 `(len(a), len(b), 0)` sentinel；
- `get_opcodes()` 的 `replace` / `delete` / `insert` / `equal` 范围和重建目标序列；
- `get_grouped_opcodes(n)` 的上下文裁剪与多个 change group；
- `ratio()` / `quick_ratio()` / `real_quick_ratio()`，上界关系及 ratio 可能依赖参数顺序；
- `autojunk` 对长度至少 200 的高频元素启发式，以及何时显式关闭；
- `Differ.compare()` 与 `ndiff()` 的 `- ` / `+ ` / `  ` / `? ` 行内提示；
- `restore(delta, 1|2)` 从 `ndiff` 序列恢复两个输入；
- `unified_diff()` / `context_diff()` 的文件名、日期、上下文行数和 `lineterm`；
- 输入行是否自带 newline 对 diff 输出可直接写入性的影响；
- `diff_bytes()` 在未知/不一致编码下的无损 bytes 往返边界；
- `HtmlDiff.make_table()` / `make_file()` 与未转义描述字段的安全陷阱；
- `get_close_matches(word, possibilities, n, cutoff)` 的排名、数量和参数校验；
- `IS_LINE_JUNK` / `IS_CHARACTER_JUNK` 只作可选过滤器，不把其当作语义相等。

## Common Pitfalls To Explain

- 把 `SequenceMatcher` 的 gestalt 匹配结果当作最小编辑距离或机器补丁；
- 忘记元素必须 hashable，或修改原序列后误以为缓存会自动失效；
- 认为 `ratio(a, b)` 在交换参数后必然相同；
- 在长且高度重复的序列上忽略 `autojunk`，得到意外匹配块；
- 把 `quick_ratio()` / `real_quick_ratio()` 当作最终相似度而不是上界；
- 把 `? ` 行当成原文件内容，或用 Differ 输出直接喂给 patch 工具；
- 输入行没有 newline 时仍使用默认 `lineterm`，产生混合换行的 diff；
- 解码未知 bytes 后再 diff，造成不可逆替换；
- 把未经转义的 `fromdesc` / `todesc` 放进 `HtmlDiff` 页面；
- 用 `get_close_matches()` 做安全敏感、语言学或拼写纠正质量承诺。

## Target File

`languages/python/stdlib/test_038_difflib.py`

## Official Sources

- https://docs.python.org/3.10/library/difflib.html

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 中文注释解释 opcode 坐标、sentinel、ratio 上界、autojunk 和 diff newline 契约；
- 用小型固定序列重建目标，证明 opcode 的含义，不实现第二套 diff 算法；
- HtmlDiff 只检查稳定结构片段，不把完整 HTML 排版快照写入测试；
- 所有文本和 bytes 数据内嵌，不读取外部文件；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--037 已完成文件/目录访问、正则与首组文本处理内容。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 038 difflib；不要先运行 pytest。
