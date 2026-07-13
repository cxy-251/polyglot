# Current Task

ID: `python.builtins.dynamic-code-and-namespaces`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `compile`、`eval`、`exec`、`globals`、`locals` 动态代码与命名空间测试套，展示源码→code object→求值/执行的正常工作流、globals/locals 查找与写回规则、内置名称注入和安全边界。

## Covers

- `compile(source, filename, mode)` 的 `eval` / `exec` / `single` 模式差异；
- str、bytes 和 AST 输入，以及 code object 的可复用性/filename 元数据；
- `flags` / `dont_inherit` / `optimize` 中有教学价值的显式编译选项；
- `eval()` 只接受表达式并返回值，不能直接执行赋值语句；
- `exec()` 执行 suite、返回 None 并把定义写入命名空间；
- eval/exec 接收源码或预编译 code object；
- globals/locals 单独传入时的名字读取、写入和函数 global 绑定；
- 只传 globals 时同一 dict 同时作为 global/local；
- 缺少 `__builtins__` 时的自动插入，以及显式 builtins mapping；
- `globals()` 返回模块全局 dict，`locals()` 在函数作用域只用于读取；
- 单独 globals/locals 的 exec 接近 class body 语义，函数看不到 locals 中的顶层赋值；
- SyntaxError filename/lineno 与空字节等输入错误；
- `ast.literal_eval()` 作为只解析字面量的较窄替代，但不是通用不可信资源防护。

## Common Pitfalls To Explain

- 对不可信输入调用 eval/exec；
- 认为删掉 `__builtins__` 就构成可靠安全沙箱；
- 用 `eval("x = 1")` 执行 statement；
- 为每条数据反复 compile 同一表达式；
- 传不同 globals/locals 后，期待 exec 定义的函数读取 locals 顶层变量；
- 修改函数 `locals()` mapping 并期待真实 fast locals 可靠改变；
- 使用没有意义的 filename，使回溯难以定位动态代码来源。

## Target File

`languages/python/builtins/test_028_dynamic_code_and_namespaces.py`

## Official Sources

- https://docs.python.org/3.10/library/functions.html#compile
- https://docs.python.org/3.10/library/functions.html#eval
- https://docs.python.org/3.10/library/functions.html#exec
- https://docs.python.org/3.10/library/functions.html#globals
- https://docs.python.org/3.10/library/functions.html#locals
- https://docs.python.org/3.10/library/ast.html#ast.literal_eval
- https://docs.python.org/3.10/reference/executionmodel.html
- https://docs.python.org/3.10/reference/simple_stmts.html#the-exec-statement

## Authoring Requirements

- 使用 pytest 风格的普通测试函数；
- 中文注释明确动态代码的命名空间和安全边界；
- 只执行测试文件内固定的小型源码字符串，不读取网络或用户输入；
- 与 009 的 SyntaxError、012 的作用域、018 的 import 避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--027 位于 `builtins/`，编号在整个 Python 树全局连续。027 内省与属性内置函数已完成首轮编写，尚未运行。下一步直接编写 028 动态代码与命名空间；不要先运行 pytest。
