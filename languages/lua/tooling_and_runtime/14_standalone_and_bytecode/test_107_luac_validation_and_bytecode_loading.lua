-- polyglot-covers: lua.luac.validation_and_bytecode_loading

local t = require("support.assertions")
local source_path = t.temp_path("source.lua")
local bytecode_path = t.temp_path("source.luac")
local file = assert(io.open(source_path, "w"))
assert(file:write("local value = 6 * 7\nreturn value\n"))
assert(file:close())

t.truth(os.execute(string.format("luac -p %q", source_path)))
t.truth(os.execute(string.format("luac -o %q %q", bytecode_path, source_path)))
local loaded = assert(loadfile(bytecode_path, "b", {}))
t.equal(loaded(), 42)

local rejected, message = loadfile(bytecode_path, "t", {})
t.equal(rejected, nil)
t.equal(type(message), "string")
t.truth(os.remove(source_path))
t.truth(os.remove(bytecode_path))

-- luac listing、opcode 名和 bytecode 布局是实现诊断；课程只验证公开命令工作流与加载边界。
t.done()
