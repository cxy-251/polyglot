# Current Task

ID: `python.builtins.float-and-complex-types`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `float` 与 `complex` 内置类型测试套，展示构造、字面量、特殊值、精确表示工具、混合数值运算和复数限制；重点解释二进制浮点不是十进制精确数，以及 NaN 不能按普通相等关系处理。

## Covers

- 浮点字面量、科学计数法、下划线分组和 `float()` 文本构造；
- int/float 混合运算的类型提升，以及 `/` 总是返回 float；
- 二进制浮点表示导致的十进制舍入现象；
- `as_integer_ratio()`、`hex()` / `float.fromhex()`、`is_integer()`；
- 正负零的相等/hash、符号保留与除法边界；
- `inf` / `-inf` / `nan` 的构造、传播、比较和真假值；
- `math.isfinite()` / `isinf()` / `isnan()` / `isclose()` 的正常判断工作流；
- complex 字面量、`complex()` 构造、`real` / `imag` / `conjugate()`；
- 实数与复数混合运算、负数平方根的复数写法；
- complex 不支持大小排序，也不能直接转为 float/int；
- float/complex 的不可变性与 hash/equality 一致性。

## Common Pitfalls To Explain

- 用 `0.1 + 0.2 == 0.3` 判断测量值或计算结果；
- 用 `== float("nan")` 检测 NaN；
- 把 `math.isclose()` 当作精确财务运算，或忽略它的相对/绝对容差；
- 认为 `-0.0` 与 `0.0` 的所有外部表现都相同；
- 期待 `(-1) ** 0.5` 自动返回 float，或对 complex 使用 `<` / `>`；
- 误以为 `float.hex()` 是十六进制文本的常规用户展示格式。

## Target File

`languages/python/builtins/test_020_float_and_complex_types.py`

## Official Sources

- https://docs.python.org/3.10/library/stdtypes.html#numeric-types-int-float-complex
- https://docs.python.org/3.10/library/stdtypes.html#additional-methods-on-float
- https://docs.python.org/3.10/library/functions.html#float
- https://docs.python.org/3.10/library/functions.html#complex
- https://docs.python.org/3.10/library/math.html#floating-point-arithmetic
- https://docs.python.org/3.10/tutorial/floatingpoint.html
- https://docs.python.org/3.10/reference/lexical_analysis.html#floating-point-literals
- https://docs.python.org/3.10/reference/lexical_analysis.html#imaginary-literals

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 使用必要而详细的中文注释解释近似值、特殊值和复数语义；
- 与 002/003/004 已覆盖的通用比较和运算协议避免机械重复；
- 使用 `math` 标准库展示判断方法，不引入第三方数值库；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 已从 `core/` 迁入 `language/`；Python 编号现在跨 `language/`、`builtins/`、`stdlib/` 全局连续。019 bool/int 已完成首轮编写并迁入 `builtins/`。全部 Python 文件仍按照用户要求尚未运行。下一步直接编写 020 float/complex；不要先运行 pytest。
