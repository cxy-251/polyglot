-- polyglot-covers: lua.c_api.userdata_user_values_and_gc

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("userdata"), "C API case passed: userdata")

-- full userdata 的原始内存、两个 user value、metatable 和 __gc 都由宿主真实验证。
t.done()
