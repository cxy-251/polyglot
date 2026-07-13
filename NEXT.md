# Current Task

ID: `python.stdlib.pathlib`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `pathlib` 标准库测试套，先用 PurePath 展示纯词法路径语义，再用 pytest `tmp_path` 展示 Path 的安全文件系统工作流。

## Covers

- `PurePath` / `PurePosixPath` / `PureWindowsPath` 与具体 `Path` 的职责；
- 路径构造、`/` 拼接、绝对片段覆盖前缀及不同平台 flavor；
- `parts` / `drive` / `root` / `anchor` / `parents` / `parent`；
- `name` / `stem` / `suffix` / `suffixes` 与多后缀文件；
- `with_name()` / `with_stem()` / `with_suffix()`；
- `is_absolute()` / `is_reserved()` / `match()`；
- `relative_to()` / `is_relative_to()` 的词法包含关系与 ValueError；
- Path 不自动展开 `~`、规范化 `..` 或访问文件系统；
- `cwd()` / `home()` / `expanduser()` / `absolute()` / `resolve()` 的差异（避免依赖真实用户目录断言）；
- `mkdir()` 的 parents/exist_ok、`touch()`；
- `write_text()` / `read_text()` / `write_bytes()` / `read_bytes()` / `open()`；
- `exists()` / `is_file()` / `is_dir()` / `stat()` / `samefile()`；
- `iterdir()` / `glob()` / `rglob()`，结果顺序必须显式排序；
- `rename()` / `replace()`、`unlink(missing_ok=True)`、`rmdir()`；
- symlink 创建、`readlink()`、`resolve(strict=...)` 与 broken symlink；
- Path 的不可变/hashable 与 os.PathLike / `__fspath__` 互操作。

## Common Pitfalls To Explain

- 用当前平台 Path 解析另一平台路径，而未使用 PureWindowsPath/PurePosixPath；
- 认为 Path 构造或 `.parent` 会访问磁盘、折叠 `..` 或展开 `~`；
- 把 `relative_to()` 当成可产生任意 `../..` 的 `os.path.relpath()`；
- 混淆 suffix 与 suffixes，错误处理 `.tar.gz`；
- 依赖 iterdir/glob 返回顺序；
- 忘记 write_text 默认会覆盖、encoding 应显式指定；
- 对目录使用 unlink，或对非空目录使用 rmdir；
- 把 exists=False 等同于路径不存在，而忽略 broken symlink；
- 在测试中操作 cwd/home，而不是 tmp_path。

## Target File

`languages/python/stdlib/test_030_pathlib_paths_and_filesystem.py`

## Official Sources

- https://docs.python.org/3.10/library/pathlib.html
- https://docs.python.org/3.10/library/pathlib.html#pure-paths
- https://docs.python.org/3.10/library/pathlib.html#general-properties
- https://docs.python.org/3.10/library/pathlib.html#operators
- https://docs.python.org/3.10/library/pathlib.html#methods
- https://docs.python.org/3.10/library/pathlib.html#concrete-paths
- https://docs.python.org/3.10/library/os.html#os.PathLike

## Authoring Requirements

- 使用 pytest 和 `tmp_path`，不操作仓库外真实文件；
- 中文注释明确区分纯词法变换、磁盘查询和有副作用操作；
- 对文件系统枚举结果先排序再断言；
- symlink 案例只在 tmp_path 内创建相对链接，不依赖管理员权限；
- 与 029 的 built-in open 基础避免机械重复，侧重 pathlib API；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--018 位于 `language/`，019--029 位于 `builtins/`；内置类型和 Built-in Functions 已完成首轮覆盖。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步从 `stdlib/` 开始编写 030 pathlib；不要先运行 pytest。
