# Current Task

ID: `python.core.structural-pattern-matching`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 ``match`` / ``case`` 结构化模式匹配测试套，覆盖 literal、capture、wildcard、OR、AS、sequence、mapping、class pattern 和 guard，并讲清模式匹配与普通相等判断/解包赋值的差异。

## Covers

- subject expression 只求值一次、case 从上到下选择且不 fall through；
- literal pattern、singleton ``None`` / ``True`` / ``False`` 与数值相等语义；
- capture pattern 总是成功并绑定名字、wildcard ``_`` 不绑定；
- value pattern 必须使用 dotted name，裸名称会成为 capture；
- OR pattern、AS pattern 与各分支必须绑定相同名称；
- guard 在 pattern 成功后求值，guard 异常正常传播；
- sequence pattern、star capture、括号分组与单元素序列差异；
- str/bytes/bytearray 不参与 sequence pattern；
- mapping pattern 允许额外键、``**rest`` 捕获剩余项；
- class pattern、keyword attributes、``__match_args__`` 位置映射；
- 内置类型 class pattern 的单个“self”位置形式；
- 属性提取错误、错误 ``__match_args__`` 和过多位置子模式的失败方式；
- 模式绑定的作用域与未匹配路径。

## Common Pitfalls To Explain

- 把裸常量名写进 case，实际创建了 capture pattern 并遮蔽后续 case；
- 忘记 ``bool`` 是 ``int`` 子类，数值 literal pattern 可先匹配 True/False；
- 以为 sequence pattern 会拆字符串；
- 以为 mapping pattern 要求键集合完全相等；
- 为 class pattern 修改 ``__match_args__`` 顺序后破坏调用者；
- 在 guard 中执行有副作用或可能抛异常的复杂逻辑；
- 依赖失败 pattern 的部分名字绑定状态。

## Target File

`languages/python/core/test_016_structural_pattern_matching.py`

## Official Sources

- https://docs.python.org/3.10/reference/compound_stmts.html#the-match-statement
- https://docs.python.org/3.10/reference/compound_stmts.html#patterns
- https://peps.python.org/pep-0634/
- https://peps.python.org/pep-0636/

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释匹配顺序、绑定语义和编译期约束；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--015 共十五个 Python 核心测试套已完成首轮编写；最新的 015 使用 asyncio.run 覆盖 coroutine/await、aiter/anext、async for/with、异步生成器表达式和 asend/athrow/aclose，无第三方异步插件。全部文件按照用户要求尚未运行。下一步直接编写 016 结构化模式匹配；不要先运行 pytest。
