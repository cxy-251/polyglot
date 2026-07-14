# Current Task

ID: `python.stdlib.collections-counter-defaultdict`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `collections.Counter` 与 `defaultdict` 测试套：用计数、多集合运算、分组和按需初始化工作流讲清它们对 dict 协议的专门化，并覆盖 Python 3.10 新增的 `Counter.total()` 与 rich comparisons、missing-key 副作用及有符号/非整数 count 边界。

## Covers

- `Counter` 从 iterable、mapping、keyword 和空对象构造；
- 缺失 key 返回 count 0 且普通读取不把 key 插入 mapping；
- count 显式设为 0 仍保留 key，只有 `del` 才移除；
- insertion order 与 `most_common()` 同 count 时的首次出现顺序；
- `elements()` 按正整数 count 重复元素，忽略 0/负数；
- `update()` 对 iterable 逐元素计数、对 mapping 累加 count，不采用 dict 的替换语义；
- `subtract()` 保留零和负 count；
- Python 3.10 `total()` 计算所有正、零、负 count 的代数和；
- `+` / `-` / `&` / `|` 的多集合加法、正差、最小值交集、最大值并集，并过滤非正结果；
- unary `+counter` 清除零/负项，unary `-counter` 反转负项为正多集合；
- Python 3.10 `==` / `<` / `<=` / `>` / `>=` 把缺失 count 当 0；
- Counter 数学结果按左 operand 首次出现、再按右 operand 新 key 的顺序；
- count 可以是 float/Fraction 等支持所需运算的数值，但 `elements()` 要求整数 count；
- `Counter.fromkeys()` 明确未实现；
- `defaultdict(default_factory)` 的 `default_factory` 属性和 `__missing__()`；
- `__getitem__` 缺失时调用无参 factory、插入并返回结果；
- `get()`、membership、`setdefault()` 等路径不通过同一 `__missing__` 自动工厂语义；
- `defaultdict(list)` 分组、`defaultdict(set)` 去重分组、`defaultdict(int)` 计数；
- 常量 factory 用闭包返回同一 immutable 默认值；
- factory 为 `None` 时缺失 key 抛 `KeyError`；
- factory 抛出的异常原样传播且不插入 key；
- 运行时替换 `default_factory` 对后续缺失 key 生效；
- copy / repr / dict 转换及 merge operator 的类型和值边界。

## Common Pitfalls To Explain

- 认为 `counter[missing]` 会像 defaultdict 一样插入 key；
- 把 `Counter.update()` 当 `dict.update()`，实际是累加而非覆盖；
- 设置 count=0 后以为 key 已删除；
- 认为 Counter 减法/交并会保留负值；multiset 运算只输出正 count；
- 忘记 `subtract()` 与原地手工减法可以保留负 count；
- 用非整数 count 调 `elements()`；
- 假设 most_common 相同 count 的顺序任意，忽略 insertion order；
- 认为 defaultdict 的 `get()`、`in` 或遍历会触发 factory；
- 把带参数函数直接作为 default_factory；factory 被无参调用；
- factory 产生 mutable 默认值时错误地返回同一个共享对象；
- 只读一次缺失 key 就无意修改 defaultdict；
- 转换成普通 dict 后仍期待 default_factory 行为存在。

## Target File

`languages/python/stdlib/data_types/test_046_counter_defaultdict.py`

## Official Sources

- https://docs.python.org/3.10/library/collections.html#counter-objects
- https://docs.python.org/3.10/library/collections.html#defaultdict-objects

## Authoring Requirements

- 使用 pytest 普通测试函数，只使用 Python 3.10 标准库；
- 计数案例使用有语义的库存/事件/分组数据，不写无解释的操作矩阵；
- 明确区分保留 signed counts 的变更 API 与只输出 positive counts 的 multiset API；
- factory 副作用用最小 call log 证明，只断言文档保证的调用次数；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--044 已完成此前范围首轮编写；045 `calendar` 已在 `data_types/` 完成首轮静态编写，模块级 first weekday 由 fixture 恢复，locale 示例只在子进程。全部 Python 文件仍未运行。下一步直接编写 046 `Counter` / `defaultdict`；`collections` 其余类型会继续拆成后续文件，不要先运行 pytest。
