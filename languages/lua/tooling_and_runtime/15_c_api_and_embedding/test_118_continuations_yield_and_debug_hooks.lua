-- polyglot-covers: lua.c_api.continuations_yield_and_debug_hooks

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("continuation"), "C API case passed: continuation")
t.matches(c_api.run("hook"), "C API case passed: hook")

-- 普通 C 调用不能跨边界任意 yield；lua_yieldk 保存 context，resume 后由 continuation
-- 重建 C 侧控制流。debug hook 使用事件/指令计数，课程不推断调度或耗时。
t.done()
