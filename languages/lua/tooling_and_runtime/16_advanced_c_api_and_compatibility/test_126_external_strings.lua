-- polyglot-covers: lua.c_api.external_strings

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(
    c_api.run("external-string"),
    "C API case passed: external%-string"
)

-- 5.5 external string 的 buffer 在 Lua 调用 falloc 前不可修改；宿主只释放一次。
t.done()
