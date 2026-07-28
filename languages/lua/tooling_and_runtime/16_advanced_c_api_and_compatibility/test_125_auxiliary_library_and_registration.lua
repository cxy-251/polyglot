-- polyglot-covers: lua.c_api.auxiliary_library_and_registration

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("auxiliary"), "C API case passed: auxiliary")

local native = require("polyglot_native")
t.equal(native.release, "Lua 5.5.0")
t.equal(native.add(20, 22), 42)

-- luaL_checkversion、luaL_gsub、luaL_ref、luaL_requiref 与 luaL_Reg 均由宿主执行。
t.done()
