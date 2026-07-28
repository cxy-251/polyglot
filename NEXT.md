# Next task

Status: `in_progress`

## Goal

将锁定的 Lua 5.5.0 正式接入 Polyglot，成为第八门 active language。以已经完成 R
接入的当前 `main` 为基线，交付完整的 Lua 纵向课程、现有 49 个横向 topic 的 Lua
实现、统一运行入口、精确版本锁、标准库与模块工作流、C API 与嵌入式验证、结构门禁
和可复现的最终验证结果。

## Locked scope

- 工具链：从官方 `lua-5.5.0.tar.gz` 构建并安装到 `/opt/polyglot/lua-5.5.0`；
  SHA-256 为 `57ccc32bbbd005cab75bcc52444052535af691789dba2b9016d5c50640d68b3d`。
- 纵向课程：建立 `languages/lua/{language,standard_library,tooling_and_runtime}/`，
  固定为连续 `001`–`128` 共 128 个可独立执行的 `test_NNN_topic.lua`。
- 测试基础：采用标准 Lua 能力和仓库内最小断言库；每个文件在独立进程运行，并隔离
  Lua 初始化变量、模块路径、全局环境、模块缓存、hook、GC、随机数、locale 和 I/O。
- 内容范围：语言和值模型、表达式与多返回值、声明与作用域、闭包、table、metatable、
  错误与关闭协议、coroutine、GC、字符串与 UTF-8、模块加载、标准库、独立解释器、
  `luac`、5.4→5.5 变化，以及完整 C API、辅助库、嵌入宿主和 C module。
- 横向课程：为现有 49 个 topic 增加 Lua 实现，镜像既有局部 stem，共 73 个
  `concepts/NN_family/NN_topic/lua/test_NN_name.lua`。
- 门禁与验证：接入 `lua`、`doctor`、`concept`、`family`、`concepts`、
  `list-concepts` 和 `check`；最终逐 family 验证 10 个 family，并执行完整纵向、
  完整横向、C API、结构检查、Unicode 120 字符行宽和 `git diff --check`。

## Official sources

- Lua 5.5 Reference Manual：`https://www.lua.org/manual/5.5/manual.html`
- Lua 5.5.0 source archive：`https://www.lua.org/ftp/lua-5.5.0.tar.gz`
- Lua 5.5.0 source browser：`https://www.lua.org/source/5.5/`

## Current progress

- 已核对当前 R 完成基线、Docker `ohdev` 架构与 C 编译器。
- 正在建立 Lua bootstrap、精确版本检查、断言库、独立进程 runner 和 C API 骨架。

## Handoff

当前唯一下一步：完成并验证 Lua 5.5.0 工具链与最小测试骨架；不得在实际验证前记录
课程或横向通过数字，也不得在全部闭环前将状态改为 `complete`。
