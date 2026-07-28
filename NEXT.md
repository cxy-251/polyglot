# Next task

Status: `in_progress`

## Current goal

将锁定的 R 4.6.1 正式接入 Polyglot，作为第七门 active language。完成 R 纵向课程、
现有 49 个横向 topic 的 73 个 R 测试入口、隔离运行器、精确版本检查、本地 package 与
FFI 工作流、状态隔离门禁和最终验证。

## Required scope

- 建立 `languages/r/{language,standard_library,tooling_and_runtime}/`，纵向文件采用全局
  连续的 `test_NNN_topic.R`，从 `001` 开始，每个文件包含唯一 `polyglot-covers`。
- 固定 R 4.6.1，普通课程只使用 base、recommended packages 和随 R 发行的标准工具；
  所有测试使用 `Rscript --vanilla`、独立 `R_LIBS_USER`、`R_USER` 和临时目录。
- 纵向课程完整覆盖 R 数据模型、promise 与作用域、向量和集合、S3/S4/reference class、
  condition/restart、NSE/formula、namespace/package、标准库与运行时、parallel 和 FFI。
- 本地最小 source package 与 C 源码只在 `/tmp/polyglot-r-*` 构建，实际验证
  `R CMD build`、`R CMD INSTALL`、受控 `R CMD check`、native registration 和清理。
- 为现有 49 个 topic 增加 `concepts/NN_family/NN_topic/r/test_NN_name.R`，镜像现有
  多文件 stem，最终形成 73 个 R 横向文件，并关联真实 R 纵向课程。
- 增加 `./tools/run.sh r`，接入 `doctor`、`concept`、`family`、`concepts`、
  `list-concepts` 和 `check`；门禁验证版本、编号、标记、关联、工程、状态隔离和行宽。

## Delivery order

依次提交 R 隔离测试骨架、语言核心、对象系统与 conditions、标准库、package/parallel/FFI、
前半横向、后半横向、active 运行器与门禁、最终验证与文档。全部验证通过后才将 R
提升为 active 并把本文件改为 `complete`。

## Handoff

Julia 完成提交已推送到 `origin/main`。R 任务刚进入实现阶段；下一步唯一操作是确认
ohdev 中 R 4.6.1、recommended packages、编译工具和 `R CMD` 工作流，再建立隔离 runner
与首批测试骨架。
