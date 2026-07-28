-- polyglot-covers: lua.c_api.multiple_state_isolation

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(
    c_api.run("state-isolation"),
    "C API case passed: state%-isolation"
)

-- 两个 Lua state 的 global environment、registry 与对象图相互隔离。
t.done()
