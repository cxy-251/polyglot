# Next task

Status: `ready`

## Current task

审计并试点“路径、文件、目录与元数据”跨语言概念。只处理 Python、C++、Node.js 已有
测试，继续暂停 Julia；先判断真实对照边界，再决定是否建立
`concepts/11_paths_files_directories_and_metadata/`。

## Official references

- Python 3.10 `pathlib`、`os.path`、`os`、`shutil`、`glob`、`stat` 官方文档；
- ISO C++20 filesystem 标准章节、WG21 工作草案及 libstdc++ 11.4 实现手册；
- Node.js 24.18.0 `path`、`url`、`fs` 官方 API 文档与对应源码；
- 三门语言的版本、规范入口和实现基线继续使用 `sources.lock`。

只用官方资料确认语义争议；不建立 Markdown/JSON 映射清单或数据库快照。

## Target files

- `languages/python/stdlib/030-035_file_and_directory_access/test_030_*.py` 至
  `test_035_*.py`
- `languages/cpp/standard_library/15_filesystem/test_135_*.cpp` 至 `test_140_*.cpp`
- `languages/nodejs/node_core/03_files_paths_and_urls/test_041_*.mjs` 至 `test_046_*.mjs`
- 若审计成立：`concepts/11_paths_files_directories_and_metadata/{python,cpp,nodejs}/`
- 必要时同步 `README.md`、`AGENTS.md`、CMake 与结构检查器

## Coverage and cases

- 区分纯词法路径操作与真实文件系统 I/O，不把同名 API 直接视为相同语义。
- 对照路径分解、规范化、相对/绝对路径、目录遍历、符号链接、状态与错误模型。
- 说明 Python exception、C++ `error_code` / exception、Node.js error-first callback /
  Promise 的迁移差异。
- 保留每门语言特有的 URL、归档、stream、watch 等内容；只有共同问题迁入概念目录。
- 移动优先使用 `git mv`，移动与内容修改分开提交；不改变现有编号和覆盖 ID。

## Handoff

1. 十个核心概念目录已经建立；71 个已有测试文件按真实对照价值迁入，未强求三语言齐全。
2. Python `001`–`178`、C++ `001`–`160`、Node.js `001`–`107` 的编号、覆盖标记和内容
   均保留；运行器、CMake、`.clangd` 与 `.gitignore` 已适配混合目录。
3. `./tools/run.sh check` 是统一结构与 Unicode 120 字符门禁。
4. 当前任务应先逐文件审计上述 18 个测试，不要直接整体迁移，也不要启动新语言。
5. 重组后全量结果：Python `5025 passed, 39 skipped`；C++ `1409 passed, 15 skipped`；
   Node.js `935 passed`。三门语言均无失败。
