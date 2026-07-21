# Next task

Status: `ready`

## Current task

启动 Julia 阶段。先审计 `ohdev` 容器是否已有 Julia 及其准确版本、路径和标准库，
再锁定相应官方资料、设计隔离执行方式，并建立最小容器测试入口与首个编号测试套。

## Official references

- 与最终锁定版本对应的 Julia 官方手册和 Base 文档
- Julia 官方 Standard Library 文档，测试框架以 `Test` 标准库文档为准
- 对应版本的 Julia release notes、源码 tag 和可复现的官方二进制发布信息
- 语言设计或版本演进只有在手册不足时才补充 JuliaLang issue、源码或官方博客

选定版本、固定 URL、归档校验值和必要的实现提交必须写入 `sources.lock`；不要建立
完整 Markdown、JSON、数据库或第三方对象快照清单。

## Target files

- `sources.lock`：新增 Julia 版本、实现组件、官方手册和标准库资料入口
- `tools/run.sh`、`tools/run-in-container.sh`：增加并验证统一的 Julia 容器入口
- `languages/julia/test_001_runtime_test_framework_and_execution_model.jl`：验证运行时、
  `Test`、失败报告、临时目录和清理边界的首个测试套
- `AGENTS.md`：基线确认后新增 Julia 内容来源和测试规范
- `project.json`：只在实际工具链与入口确定后补充更精确的 Julia 里程碑信息

## Coverage and cases

- 先只读确认容器内 `julia` 的实际路径、版本、系统镜像和 `Test` 标准库可用性；
  不从宿主机状态推断，也不先安装第三方测试框架。
- 明确 Julia 项目环境、depot、startup file、预编译缓存和环境变量的隔离策略，避免
  测试读取真实用户配置或把缓存写进仓库。
- 确认 `.jl` 文件的加载方式、模块边界、退出码和异常报告，再确定测试发现策略；
  宿主机仍只负责 VS Code 阅读和 `./tools/run.sh` 容器入口。
- 第一个测试套只验证测试框架与执行模型，并用少量案例确定中文注释、
  `polyglot-covers` ID、三位连续编号和资源清理规范；通过后再扩展语言语义。
- 文件继续按连贯学习主题组织，多个相关小设施可以合并；不为手册章节机械创建小文件。

## Handoff

1. Python 3.10 已验证：`001`–`178`，全量结果为 `5012 passed, 52 skipped`。
2. C++20 已验证：`001`–`160`，全量结果为 `1409 passed, 15 skipped`。
3. Node.js 24.18.0 已验证：`001`–`107`，`./tools/run.sh nodejs` 的结果为
   `935 passed`，没有失败或跳过；npm 11.16.0 工作流也包含在该基线中。
4. Node.js 最后一批 npm 测试是 `102`–`107`，本地提交为 `4173846`；整个 Node.js
   分区的版本和官方资料已在 `sources.lock` 锁定。
5. Julia 尚未开始。第一步是在 `ohdev` 中只读审计 `julia`，若缺失则记录证据，
   再设计可复现的容器供应方式；不要在宿主机安装 Julia。
6. 仓库虽然已连接远程，但用户只授权维护本地提交；不得 push、创建远程分支或 PR。
