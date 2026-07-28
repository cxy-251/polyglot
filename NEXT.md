# Next task

Status: `complete`

## Completed goal

Julia 1.12.6 已正式成为 Polyglot 第六门 active language；R 保持 `planned_paused`。
Julia 已具备完整纵向课程、现有横向概念覆盖、统一运行入口、精确版本检查、结构门禁和
最终验证结果。

## Completion record

- 纵向课程位于 `languages/julia/{language,standard_library,tooling_and_runtime}/`，
  共有 128 个独立测试文件，编号连续为 `001`–`128`，实际 `488 passed`、0 skipped。
- 横向层覆盖现有 10 个 family、49 个 topic 和 24 个多文件 topic，共 73 个 Julia
  测试入口，实际 `280 passed`、0 skipped；文件结构与既有语言逐 topic 镜像。
- `./tools/run.sh julia` 使用 Julia 1.12.6、标准库 `Test`、独立 `JULIA_DEPOT_PATH`、
  `--startup-file=no`、`--history-file=no`、`--depwarn=error` 和 `--check-bounds=yes`。
- 49/49 个 `concept NN_family/NN_topic` 精确验证通过；10/10 个 `family NN_family`
  聚合验证通过。
- `./tools/run.sh concepts` 六语言全量通过：Python 252、C++ 249、Node.js 255、
  Go 全部 package、Rust 73、Julia 73 个文件。
- `./tools/run.sh list-concepts` 实时统计为 49 个 topic、73 个 Julia 文件；
  `./tools/run.sh doctor` 精确报告 `julia version 1.12.6`。
- `./tools/run.sh check` 已验证六门课程连续编号、Julia 16 个问题域、128 个纵向文件、
  49 个 topic、73 个横向入口、元数据、真实关联路径、Julia Project 和 Unicode
  120 字符行宽；`git diff --check` 通过。

## Handoff

本任务已闭合，没有剩余实现或失败命令。所有提交均为本地提交，未 push；开始新阶段前，
由用户把本文件替换为新的单一 `ready` 任务。
