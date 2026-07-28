-- polyglot-covers: lua.c_api.coroutine_continuations

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("continuation"), "C API case passed: continuation")

-- lua_yieldk 保存 context；第二次 lua_resume 把恢复参数交给 continuation 并得到 42。
t.done()
