-- polyglot-covers: lua.luac.bytecode_compilation_and_loading

local t = require("support.assertions")
local source_path = t.temp_path("source.lua")
local bytecode_path = t.temp_path("source.luac")
local file = assert(io.open(source_path, "w"))
assert(file:write("return 6 * 7\n"))
assert(file:close())

t.truth(os.execute(string.format("luac -o %q %q", bytecode_path, source_path)))
local loaded = assert(loadfile(bytecode_path, "b", {}))
t.equal(loaded(), 42)

local rejected, message = loadfile(bytecode_path, "t", {})
t.equal(rejected, nil)
t.matches(message, "binary")

local binary = assert(io.open(bytecode_path, "rb"))
t.equal(binary:read(4), "\27Lua")
t.truth(binary:close())
t.truth(os.remove(source_path))
t.truth(os.remove(bytecode_path))

t.done()
