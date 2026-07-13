# Current Task

ID: `python.core.assignment-displays-and-comprehensions`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 普通/解包/带注解/赋值表达式、容器 display 与 comprehension 测试套，讲清右侧求值一次、目标从左到右写入、starred 收集类型、display 覆盖规则和 comprehension 的求值/作用域。

## Covers

- 普通赋值、链式赋值共享同一对象且右侧只求值一次；
- tuple/list 嵌套解包、starred target 总是收集为 list；
- 交换变量与解包数量不匹配异常；
- 多目标赋值按从左到右写入，后续 target 可观察先前 target 的变化；
- 带注解赋值与 ``__annotations__``，仅注解不创建属性值；
- list/tuple/set/dict display 的 ``*`` / ``**`` 解包；
- dict display 重复键后者覆盖前者，以及键先于值求值；
- list/set/dict comprehension 的嵌套循环与 filter 顺序；
- comprehension 的隐式作用域和外部 iterable 求值边界；
- assignment expression ``:=`` 返回并绑定值；
- ``:=`` 与比较/布尔运算的优先级、必须加括号的语法位置；
- comprehension 中 ``:=`` 绑定到外围作用域；
- ``:=`` 只能绑定单个名称，不能直接绑定属性、下标或解包 target；
- comprehension 中禁止用 ``:=`` 重绑定迭代变量。

## Common Pitfalls To Explain

- 以为链式赋值会复制 list/dict；
- 以为 starred target 保留原 iterable 类型；
- 忽略重叠 target 的左到右赋值顺序；
- 把 dict ``**`` 合并误认为会报告重复键；
- 在 comprehension 中混入复杂副作用导致求值顺序难读；
- 把 ``:=`` 当成普通赋值语句的任意 target 版本；
- 忽略 comprehension 内海象绑定会泄漏到外围作用域。

## Target File

`languages/python/core/test_017_assignment_displays_and_comprehensions.py`

## Official Sources

- https://docs.python.org/3.10/reference/simple_stmts.html#assignment-statements
- https://docs.python.org/3.10/reference/simple_stmts.html#annotated-assignment-statements
- https://docs.python.org/3.10/reference/expressions.html#assignment-expressions
- https://docs.python.org/3.10/reference/expressions.html#list-displays
- https://docs.python.org/3.10/reference/expressions.html#dictionary-displays
- https://docs.python.org/3.10/reference/expressions.html#displays-for-lists-sets-and-dictionaries

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释求值/写入顺序、作用域和语法限制；
- 案例保持正常、具体、可复用，不做穷举式边界矩阵；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--016 共十六个 Python 核心测试套已完成首轮编写；最新的 016 覆盖 match/case 的 literal/capture/value/OR/AS/guard/sequence/mapping/class patterns 与编译期约束。全部文件按照用户要求尚未运行。下一步直接编写 017 赋值、display 与 comprehension；不要先运行 pytest。
