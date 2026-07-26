# Next task

Status: `complete`

## Current state

Python、C++、Node.js 的横向概念课程已经完成，没有待实现的 topic：

- 10 个连续 family；
- 49 个真实横向 topic；
- 每个 topic 均包含 Python、C++、Node.js；
- 每门语言 49 个 `test_NN_name` 概念测试入口；
- `languages/` 纵向课程未被迁移、拆分或混入横向验证。

本文件当前不指定新的实现任务。不要自动开始 Julia、R、Go、Rust，不要为了继续生产而
增加 topic 或 family；下一步由用户在课程审阅、深化现有主题、接入新语言或其他方向中
明确选择。

## Verified baseline

横向课程：

- `./tools/run.sh concepts`：Python `199 passed`、C++ `200 passed`、
  Node.js `196 passed`；
- `./tools/run.sh list-concepts`：10 个 family、49 个 topic，每个语言各 49 个测试文件；
- 01–10 每个 family 的独立验证均通过；
- `./tools/run.sh check` 与 `git diff --check` 均通过。

纵向课程：

- Python 3.10.12：`5025 passed, 39 skipped`；
- C++20 / GCC 11.4 / GoogleTest 1.16.0：`1409 passed, 15 skipped`；
- Node.js 24.18.0：`935 passed`。

## Handoff

1. `concepts/NN_family/NN_topic/<language>/test_NN_name.<ext>` 是稳定横向结构。
2. `concept`、`family`、`concepts` 分别运行单主题、单章节和整个横向层；
   `list-concepts` 从目录实时生成课程清单。
3. 主题允许多个连续编号测试文件以及必要的 `fixtures/`、`support/`；C++ 同主题
   `support/*.cpp` 会自动链接。
4. `polyglot-related+` 只用于续接过长的课程文件名，与前一行共同构成真实路径。
5. 后续优先深化现有 49 个 topic；新增 family 或接入新语言必须由用户重新确定范围。
