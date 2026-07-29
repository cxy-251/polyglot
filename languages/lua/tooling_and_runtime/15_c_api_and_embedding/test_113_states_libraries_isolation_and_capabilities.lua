-- polyglot-covers: lua.c_api.states_libraries_isolation_and_capabilities

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("state"), "C API case passed: state")
t.matches(c_api.run("selected-libraries"), "C API case passed: selected%-libraries")
t.matches(c_api.run("state-isolation"), "C API case passed: state%-isolation")
t.matches(c_api.run("structured"), "C API case passed: structured")

-- 每个 lua_State 拥有独立 global environment、registry 与对象图。宿主选择标准库和
-- C function 能力，而不是默认把独立解释器的全部权限注入每个 state。
t.done()
