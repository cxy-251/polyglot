# Current Task

ID: `python.stdlib.fileinput-stat-linecache`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `fileinput`、`stat`、`linecache` 测试套，完成“文件和目录访问”类别中批量逐行输入、mode 位解释和按源码行缓存三个专门工作流。

## Covers

- `fileinput.input()` / `FileInput` 顺序遍历多个文件；
- `filename()` / `lineno()` / `filelineno()` / `isfirstline()` / `isstdin()`；
- `nextfile()` 跳过当前文件剩余行且总行号不计跳过内容；
- context manager、全局 active input 状态和嵌套调用限制；
- `openhook=fileinput.hook_encoded()` 与显式 UTF-8；
- `inplace=True`、backup 扩展名、stdout 重定向和异常时恢复边界；
- `stat.S_IMODE` / `S_IFMT`、`S_ISREG` / `S_ISDIR` / `S_ISLNK`；
- 用户/组/其他读写执行位和特殊位常量；
- `stat.filemode()` 的人类可读表示；
- `linecache.getline()` 的 1-based 行号、缺失返回空字符串；
- `getlines()` / cache、`checkcache()` 检测文件变化、`clearcache()`；
- `lazycache()` 与 module globals loader 场景只做受控演示。

## Common Pitfalls To Explain

- 忘记 fileinput 的行保留终止符；
- 混淆全局 lineno 与当前文件 filelineno；
- nextfile 跳过的行不增加累计行号；
- inplace 模式真实覆盖文件并临时重定向 stdout，不适合作为事务；
- 把 mode 整数直接与权限八进制比较而未先 S_IMODE；
- 把 ctime/权限位当跨平台完全一致；
- 认为 linecache 每次都读取最新文件，忘记 checkcache/clearcache；
- 把 getline 的空字符串当空白行，而它表示未找到。

## Target File

`languages/python/stdlib/test_035_fileinput_stat_linecache.py`

## Official Sources

- https://docs.python.org/3.10/library/fileinput.html
- https://docs.python.org/3.10/library/stat.html
- https://docs.python.org/3.10/library/linecache.html

## Authoring Requirements

- 使用 pytest 和 tmp_path，不读取仓库/用户真实文件；
- 中文注释区分批量输入状态、mode 类型/权限字段和缓存生命周期；
- inplace 案例必须保留 backup 并在 tmp_path 内验证；
- 不修改真实 stdin/stdout，必要时使用 monkeypatch/受控文件；
- 与 029--034 避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--034 已完成 pathlib、os.path/遍历、tempfile、shutil、fnmatch/glob/filecmp。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 035 fileinput/stat/linecache；不要先运行 pytest。
