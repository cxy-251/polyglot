-- polyglot-covers: lua.c_api.functions_closures_errors_and_registration

local t = require("support.assertions")
local c_api = require("support.c_api")
local native = require("polyglot_native")

t.matches(c_api.run("closures"), "C API case passed: closures")
t.matches(c_api.run("protected"), "C API case passed: protected")
t.matches(c_api.run("auxiliary"), "C API case passed: auxiliary")

local counter = native.counter(40)
t.equal(counter(), 41)
t.equal(counter(), 42)
t.equal(counter(8), 50)
t.raises(function() native.fail("bad input") end, "native failure: bad input")

-- C closure 的 upvalue 位于 pseudo-index；lua_pcall 把错误留在栈上。
-- panic 只处理未保护的致命边界，luaL_Reg/luaL_requiref 则建立受控 module API。
t.done()
