# Next task

Status: `ready`

## Current task

启动 Node.js 阶段。先审计 `ohdev` 容器已有的 Node.js/npm 工具链，锁定学习版本、
官方资料和模块模式，再建立不依赖宿主机运行时、普通执行不联网的最小测试入口。

## Official references

- 与锁定 Node.js 版本对应的 Node.js 官方 API 文档
- 与该运行时对应的 ECMAScript 语言规范版本
- Node.js 官方 `node:test`、模块系统和命令行文档
- 若官方规范不便于定位，可用 MDN 辅助发现主题，但语义争议回到 ECMAScript/Node.js
  官方资料

选定版本、固定 URL 和必要的实现提交必须写入 `sources.lock`；不要建立完整 Markdown、
JSON、数据库或第三方对象快照清单。

## Target files

- `sources.lock`：新增 Node.js、ECMAScript 和测试工具的锁定版本与官方入口
- `project.json`：记录 Node.js 基线、测试框架和稳定目录约定
- `tools/run.sh`、`tools/run-in-container.sh`：增加统一的 Node.js 容器入口
- `languages/nodejs/`：最小测试配置，以及工具链确认后才创建的首个编号测试套
- `AGENTS.md`：在基线确认后补充 Node.js 内容来源和测试规范

## Coverage and cases

- 先确认容器内 `node`、`npm` 的实际路径和版本，以及内置 `node:test` 是否满足基线；
  不要先假定需要 Jest、Vitest 或联网安装依赖。
- 明确 ECMAScript 版本、CommonJS/ES modules 的文件与包边界，以及严格模式策略。
- 宿主机只负责 VS Code 阅读和 `./tools/run.sh` 容器入口，不安装或直接运行
  Node.js/npm。
- 第一个测试套只在工具链、资料和编号规则锁定后编写，用来验证测试发现、失败报告、
  异步案例清理和中文注释风格；不要一开始批量生成语言案例。
- 文件按连贯主题组织，多个相关小设施可合在一个测试套；继续避免大量不足 100 行的
  小文件，并保持全局连续三位编号和唯一 `polyglot-covers` ID。

## Handoff

1. Python 3.10 已验证：`5012 passed, 52 skipped`。
2. C++20 已完成 `001`–`160`，全量 `./tools/run.sh cpp` 为
   `1409 passed, 15 skipped`；不要把已记录的工具链缺口误当成待修失败。
3. C++ 的权威资料、GCC/libstdc++、CMake 和 GoogleTest 版本已经在 `sources.lock`
   锁定；后续修改 C++ 时仍须先跑受影响类别，再跑全量。
4. Node.js 尚未开始，不要从宿主机版本推断容器版本。第一步是在 `ohdev` 中只读审计
   `node --version`、`npm --version`、可执行文件路径和 `node:test` 可用性。
5. 若容器缺少合适 Node.js，先记录证据并设计可复现的容器供应方式；不要把运行时或
   `node_modules` 复制进仓库，也不要让普通测试隐式联网下载。
