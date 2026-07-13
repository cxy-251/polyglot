# Current Task

ID: `python.builtins.io-and-interactive-functions`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `open`、`print`、`input`、`breakpoint`、`help` 测试套，展示文本/二进制文件边界、模式与资源管理、标准流交互和可测试的调试/帮助钩子。

## Covers

- `open()` 接受 path-like，默认读取模式与显式 text/binary mode；
- `r` / `w` / `a` / `x` 及 `+` 的读取、截断、追加、独占创建语义；
- `encoding` / `errors` / `newline` 的文本边界和换行转换；
- context manager 关闭、`closed` 状态和关闭后操作异常；
- `read()` / `readline()` / 迭代、`write()` 返回值；
- binary file 的 `seek()` / `tell()` / `truncate()`；
- text stream 只接收 str、binary stream 只接收 bytes-like；
- `print(*objects, sep, end, file, flush)`、返回 None 和 `str()` 转换；
- `input(prompt)` 对 stdout/stdin 的行为、只移除行终止符、EOFError；
- input 总是返回 str，数值解析必须显式转换；
- `breakpoint(*args, **kwargs)` 委托 `sys.breakpointhook` 并返回其结果；
- `help()` 委托 pydoc 帮助系统，以及在自动化测试中替换交互钩子。

## Common Pitfalls To Explain

- 依赖平台默认 encoding 或 newline；
- 混用 str/bytes 文件对象；
- 用 `w` 打开已有文件却没意识到会立即截断；
- 忘记 context manager/close，或在关闭后继续读写；
- 认为 append 模式会在当前 seek 位置写入；
- 认为 input 会去掉两端空格或自动解析 Python/数字；
- 在自动化测试/生产路径直接进入默认 debugger 或交互 help；
- 把 print 当结构化日志/持久协议而未控制格式和编码。

## Target File

`languages/python/builtins/test_029_io_and_interactive_functions.py`

## Official Sources

- https://docs.python.org/3.10/library/functions.html#open
- https://docs.python.org/3.10/library/functions.html#print
- https://docs.python.org/3.10/library/functions.html#input
- https://docs.python.org/3.10/library/functions.html#breakpoint
- https://docs.python.org/3.10/library/functions.html#help
- https://docs.python.org/3.10/library/io.html#text-i-o
- https://docs.python.org/3.10/library/io.html#binary-i-o

## Authoring Requirements

- 使用 pytest 和 `tmp_path` / `monkeypatch`，不读写真实用户目录；
- 中文注释解释 mode、编码、换行、流和资源生命周期；
- breakpoint/help 必须替换钩子，绝不进入真实调试器或交互帮助；
- 与未来 pathlib/io 标准库工作流文件避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--028 位于 `builtins/`，编号在整个 Python 树全局连续。028 动态代码与命名空间已完成首轮编写，尚未运行。下一步直接编写 029 I/O 与交互内置函数；不要先运行 pytest。
