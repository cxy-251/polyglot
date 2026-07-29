-- polyglot-covers: lua.c_api.allocator_and_warning_callbacks

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(
    c_api.run("allocator-warning"),
    "C API case passed: allocator%-warning"
)

-- Lua 5.5 lua_newstate 接受 allocator、opaque data 与字符串哈希 seed。
-- allocator 必须实现 realloc/free 合同；warning callback 可接收分片，但不能改变控制流。
t.done()
