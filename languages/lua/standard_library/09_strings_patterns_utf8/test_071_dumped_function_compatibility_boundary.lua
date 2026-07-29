-- polyglot-covers: lua.strings.dumped_function_compatibility_boundary

local t = require("support.assertions")

local captured = 40
local function add(increment)
    return captured + increment
end
local bytecode = string.dump(add, true)
t.equal(type(bytecode), "string")
t.truth(#bytecode > 0)

local loaded = assert(load(bytecode, "dumped", "b"))
local upvalue_name = debug.getupvalue(loaded, 1)
t.truth(upvalue_name ~= nil)
t.truth(debug.setupvalue(loaded, 1, 40) ~= nil)
t.equal(loaded(2), 42)

local rejected, message = load(bytecode, "text-only", "t")
t.equal(rejected, nil)
t.equal(type(message), "string")

-- dump 不保存 closure 的 upvalue 值，strip 还可移除名字等调试信息；
-- binary chunk 也不是安全或跨版本发布格式。
t.done()
