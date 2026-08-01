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

- 已将项目阶段切换为 `behavioral-case-density-audit`，撤销课程与内容完成声明。
- 已删除 `project.json` 中将 49 topics、441 implementations、613 files 和每语言历史
  73 个入口当作当前完成事实的固定结果；结构门禁正在切换为动态完成契约。
- 当前语言：Ruby。尚未完成任何语言的四阶段审计。

## Handoff

下一步唯一操作：完成动态审计状态与结构门禁基础提交，然后实现 Ruby 命名 case 报告器；
在 Ruby 课程、概念、harness 全部具备可执行命名 case 并通过完整验证前，不开始 Lua。
