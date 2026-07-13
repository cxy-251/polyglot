# Current Task

ID: `python.stdlib.shutil`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `shutil` 高层文件操作测试套，展示复制语义、目录树合并/忽略、移动与递归删除、可执行文件查找、磁盘空间和归档工作流。

## Covers

- `copyfileobj()` 的流复制、length 不是总量限制且不自动 rewind/flush；
- `copyfile()` 只复制内容、SameFileError 和返回目标路径；
- `copymode()` / `copystat()` 的权限与元数据范围；
- `copy()`（内容+mode）与 `copy2()`（尽量保留 metadata）；
- `copytree()`、`dirs_exist_ok=True`、`ignore_patterns()`、自定义 ignore callable；
- copytree 的 `symlinks`、`ignore_dangling_symlinks` 和 Error 聚合；
- `move()` 同文件系统重命名与目录目标行为；
- `rmtree()`、`ignore_errors` / `onerror` 回调和 symlink 防护边界；
- `disk_usage()` 的 total/used/free 关系；
- `which()` 的 PATH / mode 查找，使用 tmp_path 自建可执行文件；
- `make_archive()` / `unpack_archive()` / `get_archive_formats()`；
- `get_terminal_size()` 使用 fallback 的可测试路径。

## Common Pitfalls To Explain

- 认为 copy/copy2 会复制 owner、ACL、resource fork 等全部平台元数据；
- 忘记 copyfileobj 从当前流位置开始且不负责 flush；
- copytree 默认拒绝已存在目标，未理解 dirs_exist_ok 覆盖方向；
- 忽略 symlink 复制/跟随差异；
- 对不可信归档直接 unpack，产生路径穿越风险；
- 对 symlink 路径调用递归删除或依赖 onerror 掩盖真实失败；
- 依赖 which 查找当前目录或未显式控制 PATH。

## Target File

`languages/python/stdlib/test_033_shutil_high_level_file_operations.py`

## Official Sources

- https://docs.python.org/3.10/library/shutil.html
- https://docs.python.org/3.10/library/shutil.html#directory-and-files-operations
- https://docs.python.org/3.10/library/shutil.html#copytree-example
- https://docs.python.org/3.10/library/shutil.html#archiving-operations

## Authoring Requirements

- 使用 pytest 和 tmp_path，所有源/目标/归档均在临时目录；
- 中文注释明确内容、mode、metadata、symlink 和归档安全边界；
- 权限断言只检查 POSIX 容器中稳定的 mode 位，不依赖 owner/时间戳精度；
- 不解包不可信数据，不接触真实 PATH 外的可执行文件；
- 与 030--032 避免机械重复，侧重 shutil 的高层组合语义；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030 pathlib、031 os.path/目录遍历、032 tempfile 已完成标准库首轮编写。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 033 shutil；不要先运行 pytest。
