-- polyglot-covers: lua.c_api.virtual_stack_and_indices

local t = require("support.assertions")
local c_api = require("support.c_api")

local output = c_api.run("stack")
t.matches(output, "C API case passed: stack")

-- 宿主覆盖正/负索引、lua_absindex、acceptable index、扩栈、类型和值转换。
-- 字符串留在 stack 可达期间，即使 stack 扩张和 GC，lua_tolstring 指针仍保持有效。
t.done()
