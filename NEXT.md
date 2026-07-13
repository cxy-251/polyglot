# Current Task

ID: `python.stdlib.os-path-and-directory-traversal`

Status: `ready`

Repository phase: `python-authoring-unverified`

## Goal

编写 Python 3.10 `os.path` 与 `os` 目录枚举测试套，展示低层路径字符串处理、PathLike 转换、broken symlink 判断以及 `listdir` / `scandir` / `walk` 的可控遍历工作流，并与 pathlib 的对象式接口形成对照。

## Covers

- `os.fspath()` / `fsencode()` / `fsdecode()` 与自定义 PathLike；
- os.path API 对 str/bytes 输入保持同类返回，禁止混合两者；
- `join()` 绝对片段覆盖、`normpath()` 纯词法规范化；
- `abspath()` / `realpath()` 与 cwd、symlink 的区别；
- `basename()` / `dirname()` / `split()` / `splitdrive()` / `splitext()`；
- `relpath()`、`commonpath()` 与字符级 `commonprefix()` 的差异；
- `expanduser()` / `expandvars()` 的环境替换边界；
- `exists()` / `lexists()` / `isfile()` / `isdir()` / `islink()` / `samefile()`；
- `getsize()` / `getmtime()` 等便捷 stat 查询；
- `os.listdir()` 返回名称、路径参数类型影响返回类型；
- `os.scandir()` 的 DirEntry name/path/is_file/is_dir/stat 和 context manager；
- `os.walk()` 的 topdown 顺序、原地裁剪 dirnames、bottom-up 删除顺序；
- `followlinks` 的循环风险和默认不跟随目录 symlink；
- `makedirs()` / `removedirs()` 的 parents/exist_ok 与逐层清理行为。

## Common Pitfalls To Explain

- 把 normpath/abspath 当作真实 symlink 解析或安全边界；
- 在一个 os.path 调用中混合 str 与 bytes；
- 用 commonprefix 判断共同目录，得到半截路径名；
- 混淆 exists 与 lexists，漏掉 broken symlink；
- 依赖 listdir/scandir/walk 的文件系统顺序；
- 在 topdown walk 中给 dirnames 重新绑定而非原地修改，导致无法裁剪；
- followlinks=True 未做 visited inode 防环；
- 认为 removedirs 只删除最后一级目录。

## Target File

`languages/python/stdlib/test_031_os_path_and_directory_traversal.py`

## Official Sources

- https://docs.python.org/3.10/library/os.html#file-names-command-line-arguments-and-environment-variables
- https://docs.python.org/3.10/library/os.html#files-and-directories
- https://docs.python.org/3.10/library/os.html#os.listdir
- https://docs.python.org/3.10/library/os.html#os.scandir
- https://docs.python.org/3.10/library/os.html#os.walk
- https://docs.python.org/3.10/library/os.path.html
- https://docs.python.org/3.10/library/os.path.html#os.path.commonpath

## Authoring Requirements

- 使用 pytest 和 `tmp_path` / `monkeypatch`，不遍历真实用户目录；
- 中文注释区分字符串规范化、磁盘查询和目录遍历；
- 所有枚举结果显式排序后断言；
- symlink 仅在 tmp_path 内创建，walk 不启用不受控 followlinks；
- 与 030 pathlib 避免机械重复，重点解释 os.path/DirEntry/walk 的独特语义；
- 文件顶部写 `polyglot-covers` 标记；
- 本阶段不运行测试。

## Handoff

001--029 已完成语言核心与内置层首轮编写；030 pathlib 已完成首轮编写并进入 `stdlib/`。编号在整个 Python 树全局连续。全部 Python 文件尚未运行。下一步直接编写 031 os.path 与目录遍历；不要先运行 pytest。
