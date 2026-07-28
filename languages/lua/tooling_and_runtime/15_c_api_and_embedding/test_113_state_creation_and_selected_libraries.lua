-- polyglot-covers: lua.c_api.state_creation_and_selected_libraries

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("state"), "C API case passed: state")
t.matches(
    c_api.run("selected-libraries"),
    "C API case passed: selected%-libraries"
)

-- luaL_newstate 创建独立 state；宿主必须显式选择或打开标准库。
t.done()
