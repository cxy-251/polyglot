# Next task

Status: `complete`

## Current state

Python、C++、Node.js、Go 的双轴课程已经完成，没有待实现 topic：

- Go 1.26.5 纵向课程包含 16 个问题域、128 个连续编号测试文件；
- 10 个连续 family、49 个完成四语言内容终审的横向 topic；
- 每个 topic 均包含 Python、C++、Node.js、Go；
- 24 个高复杂度 topic 使用多个连续编号测试文件；
- 每门语言 73 个横向测试入口，Go 实现保持既有子问题结构；
- Go 接入终审已修正 doctor 语言状态、调度与初始化断言范围、Reader/Writer 契约及
  归档压缩资源处理；
- `languages/` 纵向课程未被迁移、拆分或混入横向验证。

本文件当前不指定新语言或新 topic。不要自动开始 Julia、R 或 Rust；下一阶段由用户在
课程审阅、深化既有主题或接入新语言中明确选择。

## Verified baseline

横向课程：

- `./tools/run.sh concepts`：Python `252 passed`、C++ `249 passed`、
  Node.js `255 passed`、Go `75 passed`；
- `./tools/run.sh list-concepts`：10 个 family、49 个 topic，每门语言各 73 个测试文件；
- 01–10 每个 family 的四语言独立验证均通过；
- `./tools/run.sh check` 与 `git diff --check` 均通过。

纵向课程：

- Python 3.10.12：`5025 passed, 39 skipped`；
- C++20 / GCC 11.4 / GoogleTest 1.16.0：`1409 passed, 15 skipped`；
- Node.js 24.18.0：`935 passed`；
- Go 1.26.5：128 个测试文件、`133 passed`，`go vet ./...` 通过。

## Handoff

1. `languages/go/` 是完整纵向课程；`concepts/*/*/go/` 是 49 个精简横向实现。
2. `go.work` 连接 `languages/go` 与 `concepts` 两个 module；Go 测试只在 `ohdev` 中运行。
3. 默认 `./tools/run.sh doctor` 只强制检查 active language；`doctor planned` 额外报告
   Julia、R、Rust，不把规划语言变成当前工程依赖。
4. `./tools/run.sh go` 固定使用 `-count=1` 并执行 `go vet`；concept、family 和 concepts
   命令统一遍历 `ACTIVE_LANGUAGES`，缺少对应语言运行器时立即失败。
5. active language 新增后必须先建立完整纵向课程，再覆盖现有全部 topic，并指向本语言
   纵向课程。
6. 当前 `content_review_complete` 为 true；终审表示四语言共同问题已经统一复核，不表示
   穷举未来版本的全部能力。
7. 后续优先维护现有 49 个 topic；新增 family、topic 或接入新语言必须由用户重新确定
   范围。
