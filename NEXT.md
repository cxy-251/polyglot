# Current Task

ID: `python.stdlib.string-textwrap-unicodedata`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `string`、`textwrap` 与 `unicodedata` 文本处理测试套，串联 ASCII 常量与模板、段落整形以及 Unicode 属性/正规化，形成从文本生成到显示前整理的可查阅工作流。

## Covers

- `string.ascii_letters` / `ascii_lowercase` / `ascii_uppercase` / `digits` / `hexdigits` / `octdigits` / `punctuation` / `printable` / `whitespace` 的集合关系与 ASCII 边界；
- `string.capwords()` 的默认空白归一化，以及显式 `sep` 时保留空字段的差异；
- `string.Template` 的 `$name` / `${name}` / `$$`、`substitute()` / `safe_substitute()` 与缺失/非法 placeholder；
- 通过 `Template` 子类定制 `delimiter`，说明类级 pattern 在创建子类时生成；
- `string.Formatter.parse()` / `get_field()` / `convert_field()` / `format_field()`，以及小型自定义 Formatter 的受控扩展；
- `textwrap.wrap()` / `fill()` 与 width、`initial_indent` / `subsequent_indent`；
- tab 展开、空白替换/丢弃、长单词和连字符的换行选项；
- `max_lines` / `placeholder` 截断和 `TextWrapper` 实例复用；
- `dedent()` 对共同缩进、空白行、tab 与空格不等价的处理；
- `indent()` 的 predicate，以及 `shorten()` 在截断前先折叠空白的规则；
- `unicodedata.lookup()` / `name()` 及无名称字符的 default；
- `decimal()` / `digit()` / `numeric()` 的返回类型和字符域差异；
- `category()` / `bidirectional()` / `combining()` / `east_asian_width()` / `mirrored()` / `decomposition()`；
- NFC / NFD / NFKC / NFKD、canonical equivalence、compatibility normalization 与 `is_normalized()`；
- 终端显示宽度、grapheme cluster 与 Python 字符串长度/`textwrap` width 不是同一概念。

## Common Pitfalls To Explain

- 把 `string.ascii_letters` 等常量误认为 Unicode 字母/数字集合；
- 用 `Template.safe_substitute()` 后没有检查残留 placeholder，静默掩盖缺失数据；
- 把 Template 当成可信表达式求值器，或把其替换能力等同于 `str.format()`；
- 认为 `textwrap` 的 width 等于终端列宽，忽略全角字符、组合字符和 emoji；
- 认为 `dedent()` 会把 tab 与同宽空格视作相同缩进；
- 在 `shorten()` 上设置 `replace_whitespace` / `drop_whitespace`，却期待改变其预折叠行为；
- 直接比较视觉相同但正规化形式不同的 Unicode 字符串；
- 无条件使用 NFKC/NFKD，意外抹去上标、圈字等兼容性区别；
- 假设每个 Unicode 字符都有 name、双向类别或 decomposition 文本。

## Target File

`languages/python/stdlib/test_037_string_textwrap_unicodedata.py`

## Official Sources

- https://docs.python.org/3.10/library/string.html
- https://docs.python.org/3.10/library/textwrap.html
- https://docs.python.org/3.10/library/unicodedata.html

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 中文注释说明 ASCII/Unicode 边界、模板失败模式、换行宽度模型和正规化取舍；
- 自定义 Template/Formatter 只演示协议扩展，不构造通用模板语言；
- Unicode 示例使用固定 code point，并在断言附近写出选择该字符的原因；
- 测试数据固定，不读取外部文件、不依赖 locale 或终端；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--036 已完成文件/目录访问与正则表达式首轮编写。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 037 文本处理；不要先运行 pytest。
