# Next task

Status: `complete`

## Completed goal

R 4.6.1 已正式成为 Polyglot 第七门 active language。R 纵向课程、现有 49 个横向
topic 的 73 个 R 测试入口、统一运行器、精确版本检查、本地 package/FFI 工作流、
状态隔离门禁和最终验证均已闭环。

## Completion record

- 工具链：`doctor` 精确确认 R 与 Rscript 均为 `4.6.1`；R 已加入七门 active language。
- 纵向课程：`languages/r/` 共 128 个文件，编号连续为 `001`–`128`；
  `./tools/run.sh r` 实际结果为 `128/128` 通过。
- 横向课程：49 个 topic 全部存在 R 实现，共 73 个 `.R` 测试文件；逐 topic 精确验证
  49/49 通过，全量 R concepts 为 `73/73` 通过。
- family：10 个包含 R 的统一 `family` 命令全部通过；统一单 topic `concept` 入口通过。
- 全横向：`./tools/run.sh concepts` 七门语言全部通过，其中 R 为 73 个文件通过。
- package：本地 fixture 的 source、namespace、lifecycle、lazy-load cache、
  `R CMD build`、`R CMD INSTALL`、`R CMD check`、`tools::testInstalledPackage` 和
  native registration 共 8 个专项文件通过，`R CMD check` 为 `Status: OK`。
- FFI/并发：`.C`、`.Call`、注册表、SEXP、PROTECT/UNPROTECT、external pointer、
  long-vector 接口、NA/NaN、fork、PSOCK、随机数流、错误传播和 worker cleanup 全部通过。
- 门禁：`list-concepts` 实时列出 49 个 topic 且每个含 R；`doctor`、`check`、
  Unicode 120 字符行宽、R 状态泄漏探针和 `git diff --check` 全部通过。

## Handoff

Julia 完成提交已推送到 `origin/main`。R 接入任务已完成；当前没有未完成的实现步骤。
