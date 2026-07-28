# Next task

Status: `complete`

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

## Completion

- 工具链：官方 Lua 5.5.0 源码归档校验、构建和幂等 bootstrap 通过；`lua`、`luac`、
  C headers 与 `liblua.a` 均由 `/opt/polyglot/lua-5.5.0` 提供，`doctor` 精确版本检查通过。
- 纵向课程：`languages/lua/` 的 `001`–`128` 连续编号与 128 个唯一
  `polyglot-covers` 通过结构检查；完整执行结果为 `128/128 files passed`。
- 横向课程：现有 `49/49 topics` 均有 Lua 实现，局部 stem 与其他 active language
  一致；完整执行结果为 `73/73 files passed`。
- family：`01_values_and_comparison` 至 `10_time_locale_and_runtime` 共 10 个 family
  已逐一通过八语言统一入口。
- C API：严格 C11 警告配置下，C host 的 16 个独立案例与动态 C module 构建、加载和
  清理通过；模块加载、standalone、`luac`、bytecode 与 C API 的 32 个课程文件独立复跑通过。
- 统一验证：单 topic、单 family、`lua`、`concepts`、`list-concepts`、`doctor`、
  `check` 和 `git diff --check` 全部通过；临时构建目录、模块、进程状态和测试沙箱均已清理。

## Handoff

Lua 5.5.0 已成为第八门 active language，本任务没有剩余实现步骤。后续任务必须由用户
重新指定 `NEXT.md`，不得从本完成记录自行扩张 topic、family 或语言范围。
