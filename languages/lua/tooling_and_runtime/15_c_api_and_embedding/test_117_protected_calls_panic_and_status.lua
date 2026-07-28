-- polyglot-covers: lua.c_api.protected_calls_panic_and_status

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("protected"), "C API case passed: protected")

local native = require("polyglot_native")
t.raises(function()
    native.fail("bad input")
end, "native failure: bad input")

-- panic handler 只用于未受保护的致命边界；课程安装并恢复它，不故意触发进程 abort。
t.done()
