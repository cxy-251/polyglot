# Polyglot Standard Library by Example

Polyglot 用小而可运行的测试示例，展示多种编程语言中最值得学习的语言特性与标准库工作流。

项目固定覆盖七种语言：Python、C++、Node.js、Julia、R、Go、Rust。最终产品不是 API 清单，也不是生成提示词，而是 `languages/` 中可以直接运行、阅读和修改的示例。

## 当前阶段

仓库正在进入 `m1-foundation-examples`：先为每种语言建立最小测试入口和第一组代表性示例，再按学习价值扩展任务。

这次重置采用仓库原生协作方式：

- 对话直接修改仓库，不再经过 `chatgpt-sources/` 中转。
- `tasks.json` 保存任务范围、状态、资料、产物和验收条件。
- `AGENTS.md` 规定新对话如何读取状态、接续工作和完成任务。
- `project.json` 保存稳定的语言范围、测试框架和运行命令。
- 旧 checklist-first 实现保留在 Git 历史中，不再占据当前工作树。

## 快速开始

```bash
./tools/run.sh check
./tools/run.sh status
./tools/run.sh next
./tools/run.sh task python.collections-core
```

没有用户指定任务时，`next` 会优先返回未完成的 `in_progress` 项，否则返回第一个依赖已满足的 `todo` 项。

完成一个任务的标准流程：

1. 阅读任务的 `covers`、`cases`、`sources`、`files`、`acceptance` 和 `verify`。
2. 将示例直接写入 `languages/<language-id>/`。
3. 执行任务列出的验证命令。
4. 更新 `tasks.json` 状态，再运行 `./tools/run.sh check`。
5. 验收全部通过后提交一个本地 commit。

## 仓库结构

```text
AGENTS.md                         跨对话执行契约
README.md                         产品说明与入口
project.json                      稳定项目配置
tasks.json                        当前计划与接续状态
languages/<language-id>/          可运行示例（按任务逐步创建）
tools/project.py                  状态、任务选择和一致性检查
tools/run.sh                      统一验证入口
.github/workflows/repository.yml  仓库状态检查
```

`languages/` 不使用占位文件；对应语言的第一个任务完成时创建目录和最小运行配置。

## 任务状态

- `todo`：尚未验收。
- `in_progress`：已有实际工作，`handoff` 必须说明下一步。
- `blocked`：存在外部阻塞，`blocker` 必须说明证据和解除条件。
- `done`：产物存在，验收项与验证命令全部通过。

状态不是聊天记录摘要。所有接续所需的信息必须落在任务、代码、验证结果能说明的仓库状态中。

## 验证入口

```bash
./tools/run.sh python
./tools/run.sh cpp
./tools/run.sh nodejs
./tools/run.sh julia
./tools/run.sh r
./tools/run.sh go
./tools/run.sh rust
./tools/run.sh all
```

语言目录尚未建立时，对应入口会明确报错并提示先完成 foundation task。C++ 构建输出写到 `/tmp/polyglot-cpp-build`，其他工具也应避免把缓存和临时产物提交进仓库。

## 历史

重置前的 checklist、Dash 对象快照、审计脚本与 ChatGPT handoff source 截止于 commit `662e0d1`。需要参考旧判断或恢复某段资料时使用 Git 历史：

```bash
git log --oneline --all
git show 662e0d1:checklists/python/stdlib.tasks.json
```

历史内容只用于查证，不代表当前结构或工作流。
