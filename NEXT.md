# Current Task

ID: `python.stdlib.glob-fnmatch-filecmp`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `fnmatch`、`glob`、`filecmp` 测试套，展示文件名模式、递归路径枚举和文件/目录树比较的正常工作流及浅比较陷阱。

## Covers

- `fnmatch()` 的平台 normcase、`fnmatchcase()` 的精确大小写；
- `filter()` 批量筛选、`translate()` 生成正则；
- shell-style `*` / `?` / `[seq]` / `[!seq]`，但不等于完整正则；
- fnmatch 中路径分隔符没有特殊语义，与 glob 的路径分段区别；
- `glob()` / `iglob()`、相对/绝对结果和显式排序；
- `*` 默认不匹配点开头名称、显式 dot pattern；
- `**` + `recursive=True`，多个 `**` 可能产生重复；
- Python 3.10 `root_dir` / `dir_fd` 与 cwd 隔离；
- `glob.escape()` 处理字面量元字符；
- `filecmp.cmp(shallow=True/False)`、stat 签名浅比较和缓存；
- `clear_cache()`；
- `cmpfiles()` 的 match/mismatch/errors 三组结果；
- `dircmp` 的 left_only/right_only/common/common_files/common_dirs；
- same_files/diff_files/funny_files、subdirs 和 report 系列定位；
- dircmp 是惰性属性计算，比较内容时应明确 shallow 限制。

## Common Pitfalls To Explain

- 把 fnmatch pattern 当正则表达式；
- 认为 fnmatch 的 `*` 不跨目录分隔符；
- 依赖 glob 返回顺序或忘记点文件规则；
- `**` 未传 recursive=True；
- 多个 `**` 模式未去重；
- 把 filecmp shallow=True 的“stat 相同”当内容已读取一致；
- 文件快速变化但缓存/stat 时间精度不足，未 clear_cache 或 deep compare；
- 认为 dircmp 默认递归深比较所有文件内容。

## Target File

`languages/python/stdlib/test_034_glob_fnmatch_filecmp.py`

## Official Sources

- https://docs.python.org/3.10/library/fnmatch.html
- https://docs.python.org/3.10/library/glob.html
- https://docs.python.org/3.10/library/filecmp.html

## Authoring Requirements

- 使用 pytest 和 tmp_path，模式数据全部在临时目录；
- 中文注释明确 filename pattern、path glob 和内容比较的层次差异；
- 所有 glob/list 结果先排序再断言；
- 不依赖宿主文件系统大小写规则，大小写差异用 fnmatchcase 明确验证；
- 与 030--033 避免机械重复；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030--033 已完成 pathlib、os.path/目录遍历、tempfile、shutil 标准库首轮编写。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 034 fnmatch/glob/filecmp；不要先运行 pytest。
