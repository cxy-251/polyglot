# Next task

Status: `in_progress`

## Goal

以 commit `3e18412` 为结构重构基线，审计低行为案例密度的六门课程：
`Ruby → Lua → R → Julia → Rust → Go`。本轮以可独立报告的命名行为案例为课程执行单位，
修正只有文件通过数、没有行为边界与失败定位能力的测试结构；Python、C++、Node.js 只作为
成熟测试框架的参照，除指标错误、语义错误或共同概念缺口外不修改。

## Audit contract

- `test file` 是隔离与组织边界；`behavior case` 是稳定命名、可独立报告失败的教学行为；
  `assertion` 是 case 内验证单个观察点的检查，三者不得混算。
- Ruby、Lua、R 分别使用仓库内 `case(name)` 报告器；同一文件中一个 case 失败后继续执行
  后续 case，失败报告包含文件、case 名、失败断言、expected、actual 和原始异常。
- Julia 以最内层具名教学 `@testset` 为 behavior case；Rust 以独立 `#[test]`、具名测试
  和独立 doctest 为 case；Go 以顶层 `Test*` 与具名 `t.Run` 为 case。
- 指标通过框架收集或真实执行生成；不能可靠取得 assertion 数时明确报告 `unavailable`，
  禁止通过源码文本搜索伪造断言数量。
- `./tools/run.sh metrics`、`metrics <language>`、`metrics concepts` 动态报告课程、概念和
  harness 的文件、case、assertion、skip 与 failure 结果，不把任何历史总数作为门禁。
- 课程、概念和 harness 分层保持不变；不新增语言，不追求统一文件数、case 数或断言数。

## Order and commits

每门语言严格依次完成以下四个职责单一的本地提交，前一门完整验证前不进入下一门：

1. `Add <language> named case reporting`
2. `Audit <language> course behavior cases`
3. `Audit <language> concept behavior cases`
4. `Record <language> case-density results`

语言顺序固定为 Ruby、Lua、R、Julia、Rust、Go。每门完成后验证纵向课程、harness、该语言
全部概念、逐 topic 精确入口、10 个 family、完整 concepts、动态 metrics、doctor、
结构门禁和 `git diff --check`。

## Current stage

- 已提交动态审计状态与结构门禁基础改造：`5611667 Reopen behavioral case-density audit`。
- 已提交 Ruby 命名 case 报告器与 6 个 harness 文件迁移：
  `4a9b701 Add Ruby named case reporting`；Ruby harness 全量 `6/6` 通过。
- 当前语言：Ruby。74 个纵向课程文件已经全部改为可独立报告的命名 behavior case，
  Ruby 纵向全量 `74/74` 通过；相关改动保存在当前课程审计提交中。
- Ruby 横向概念尚未开始，现有 72 个入口均待审计；动态 `metrics` 入口尚未实现；
  Lua、R、Julia、Rust、Go 均未开始。

## Handoff

按用户要求暂停，保持 `in_progress`，不开始 Ruby 概念或后续语言。

最后运行的组合命令是
`./tools/run.sh ruby && ./tools/run.sh ruby-harness && ./tools/run.sh check && git diff --check`：
Ruby 纵向 `74/74` 和 harness `6/6` 已完成并通过；命令在结构检查期间被主动中断，退出码
为 `130`，因此结构门禁与 `git diff --check` 没有形成最终通过结论。

恢复后的唯一下一步操作：运行 `./tools/run.sh check`，确认结构门禁后再决定是否继续
Ruby 横向概念审计。
