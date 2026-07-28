-- polyglot-covers: lua.c_api.allocator_and_warning_callbacks

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(
    c_api.run("allocator-warning"),
    "C API case passed: allocator%-warning"
)

-- Lua 5.5 lua_newstate 接受 allocator、opaque data 与字符串哈希 seed。
t.done()
