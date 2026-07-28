# Next task

Status: `in_progress`

## Current goal

将锁定的 Julia 1.12.6 正式接入 Polyglot，作为第六门 active language；R 保持
`planned_paused`。完成 Julia 纵向课程、现有 49 个横向 topic 的 73 个 Julia 测试入口、
统一运行器、精确版本检查、结构门禁、六语言内容复核和最终验证。

## Required scope

- 建立 `languages/julia/{language,standard_library,tooling_and_runtime}/`，纵向文件采用
  全局连续的 `test_NNN_topic.jl`，从 `001` 开始，每个文件包含 `polyglot-covers`。
- 固定 Julia 1.12.6 和标准库 `Test`；所有运行使用 `--startup-file=no`、
  `--history-file=no`、独立 `JULIA_DEPOT_PATH`、`--depwarn=error` 和
  `--check-bounds=yes`，普通课程不引入第三方 package、不联网、不读取用户配置。
- 纵向课程覆盖类型系统、`Nothing`/`Missing`、比较与哈希、转换与 promotion、作用域、
  闭包、函数与 multiple dispatch、method specificity/ambiguity、keyword/world age、
  struct/参数化类型、数组/view/迭代/broadcast、Unicode、异常与资源、模块与加载、宏、
  Task/Channel/Threads/同步、文件/流/进程、标准库、Pkg、反射、运行时、FFI/unsafe。
- 为现有 49 个 topic 增加
  `concepts/NN_family/NN_topic/julia/test_NN_name.jl`，镜像 24 个多文件 topic，
  最终形成 73 个 Julia 横向文件；标记和 `polyglot-related` 必须指向真实 Julia 课程。
- 增加 `./tools/run.sh julia`，并将 Julia 接入 `doctor`、`concept`、`family`、
  `concepts`、`list-concepts` 和 `check`；版本错误必须报告期望值、实际值和安装命令。
- 结构门禁检查 Julia 纵向目录、扩展名、连续编号、覆盖标记、横向完整性、局部编号、
  73 个入口、关联路径、Julia Project 和 Unicode 120 字符行宽。

## Delivery order

依次提交 Julia 测试骨架、语言核心、标准库、并发/Pkg/运行时、前半横向、后半横向、
active 运行器与门禁、最终验证与文档。纵向稳定后再编写横向；全部验证通过后才将 Julia
提升为 active 并把本文件改为 `complete`。任务没有授权 push，最终只建立本地提交。

## Handoff

当前处于启动审计阶段；工作树仅有本任务的 `NEXT.md` 状态变更。下一步唯一操作是核对
Julia 1.12.6 工具链、官方资料、现有运行器和 Rust/Go 课程组织，再建立 Julia 测试骨架。
