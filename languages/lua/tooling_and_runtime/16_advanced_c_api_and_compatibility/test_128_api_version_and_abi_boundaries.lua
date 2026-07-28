-- polyglot-covers: lua.c_api.version_and_abi_boundaries

local t = require("support.assertions")
local c_api = require("support.c_api")

t.matches(c_api.run("version-gc"), "C API case passed: version%-gc")

local native = require("polyglot_native")
t.equal(native.release, "Lua 5.5.0")
t.equal(_VERSION, "Lua 5.5")

local bytecode = string.dump(function()
    return 42
end)
t.equal(bytecode:sub(1, 4), "\27Lua")

-- 头文件 release、运行库、解释器需一起锁定；ABI、对象布局和 bytecode 不跨版本承诺兼容。
t.done()
