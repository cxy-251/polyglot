# Current Task

ID: `python.stdlib.tempfile`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `tempfile` 标准库测试套，展示自动清理的临时文件/目录、可命名临时文件、内存到磁盘的 spooled file，以及低层 `mkstemp` / `mkdtemp` 的资源所有权。

## Covers

- `TemporaryFile()` 默认 binary mode、文本模式、seek/read/write 和自动关闭；
- `NamedTemporaryFile()` 的 `.name`、delete=True 生命周期；
- delete=False 跨上下文重开与调用者手工 unlink 责任；
- `TemporaryDirectory()` 路径、嵌套内容和 context exit 递归清理；
- 显式 `cleanup()` 的幂等使用与 `ignore_cleanup_errors`（Python 3.10）；
- prefix/suffix/dir 控制，所有案例仍限制在 tmp_path；
- `SpooledTemporaryFile(max_size, mode)` 在阈值前后的统一文件接口；
- `rollover()` / `fileno()` 强制落盘，但调用者不依赖私有 `_file` 实现；
- `mkstemp()` 返回 `(fd, path)`，需要 `os.close` + `os.unlink`；
- `mkdtemp()` 返回目录路径，需要调用者递归/显式清理；
- `gettempdir()` / `gettempdirb()` / `gettempprefix()` 只做稳定类型/契约断言；
- 临时名称由安全创建 API 生成，不能用 `mktemp()` 先取名字再打开。

## Common Pitfalls To Explain

- 忘记 TemporaryFile 默认是 binary mode；
- 依赖 NamedTemporaryFile 在不同平台上的“打开时再次打开同名文件”行为；
- delete=False 后忘记清理；
- 把 `.name` 当永久路径，在 context 退出后继续使用；
- 忘记 mkstemp 返回的是已经打开的原始 fd；
- 只关闭 fd 不删除路径，或只删除路径不关闭 fd；
- 依赖 SpooledTemporaryFile 私有 `_file` 类型判断是否落盘；
- 使用存在竞态漏洞的 `mktemp()`。

## Target File

`languages/python/stdlib/test_032_tempfile_lifecycle.py`

## Official Sources

- https://docs.python.org/3.10/library/tempfile.html
- https://docs.python.org/3.10/library/tempfile.html#tempfile.TemporaryFile
- https://docs.python.org/3.10/library/tempfile.html#tempfile.NamedTemporaryFile
- https://docs.python.org/3.10/library/tempfile.html#tempfile.SpooledTemporaryFile
- https://docs.python.org/3.10/library/tempfile.html#tempfile.TemporaryDirectory
- https://docs.python.org/3.10/library/tempfile.html#tempfile.mkstemp
- https://docs.python.org/3.10/library/tempfile.html#tempfile.mkdtemp

## Authoring Requirements

- 使用 pytest 和 tmp_path；显式 dir=tmp_path，避免污染系统临时目录；
- 中文注释解释资源所有权、自动/手工清理和跨平台命名文件边界；
- 所有低层 fd/path 都用 try/finally 清理；
- 不调用不安全的 mktemp()，只在注释解释；
- 与 029/030 文件基础避免机械重复，侧重生命周期；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030 pathlib、031 os.path/目录遍历已完成标准库首轮编写。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 032 tempfile 生命周期；不要先运行 pytest。
