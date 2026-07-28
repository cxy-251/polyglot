# Next task

Status: `complete`

## Completed goal

Rust 1.97.1 / edition 2024 已成为第五门 active language；Julia、R 保持
`planned_paused`。Rust 纵向课程包含 16 个问题域、`001`–`128` 连续测试文件；现有
10 个 family、49 个 topic、24 个多文件 topic 均已增加 Rust，共 73 个横向测试入口。

运行器、doctor、概念清单、结构门禁、`project.json` 和文档现已统一采用五语言状态。
Rust 纵向与横向使用独立 Cargo workspace，普通课程不引入第三方 crate。

## Final verification

- 五门纵向课程通过：Python `5025 passed, 39 skipped`；C++ `1409 passed, 15 skipped`；
  Node.js `935 passed`；Go `133 passed`；Rust `128 passed, 1 ignored`，另有 1 个 doc test。
- 五语言横向全量通过：Python `252 passed`；C++ `249 passed`；Node.js `255 passed`；
  Go `75 passed`；Rust `73 passed`。
- 10 个 `family` 命令逐一通过；代表性单 topic 命令确认五语言及 Rust 精确分派。
- `doctor`、`doctor planned`、`list-concepts`、结构与 Unicode 行宽门禁通过。
- Rust 纵向、横向均通过 rustfmt 与 Clippy `-D warnings`；Go 通过 `go vet`。

## Handoff

当前 goal 已完成，没有剩余开发步骤。下一阶段必须由用户为本文件指定一个新的单一任务。
