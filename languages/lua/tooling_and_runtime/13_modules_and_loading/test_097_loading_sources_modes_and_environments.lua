-- polyglot-covers: lua.modules.loading_sources_modes_and_environments

local t = require("support.assertions")
local path = t.temp_path("chunk.lua")
local file = assert(io.open(path, "w"))
assert(file:write("local value = ...; created = value * 2; return created, _ENV.marker\n"))
assert(file:close())

local environment = {marker = "custom"}
local loaded = assert(loadfile(path, "t", environment))
local result, marker = loaded(21)
t.equal(result, 42)
t.equal(marker, "custom")
t.equal(environment.created, 42)
t.equal(rawget(_G, "created"), nil)

local parts = {"return ", "40", " + ", "2"}
local index = 0
local from_reader = assert(load(function()
    index = index + 1
    return parts[index]
end, "reader-chunk", "t", {}))
t.equal(from_reader(), 42)
t.equal(index, #parts + 1)

local bytecode = string.dump(function() return "binary" end)
t.equal(assert(load(bytecode, "binary", "b"))(), "binary")
local rejected, message = load(bytecode, "binary-as-text", "t")
t.equal(rejected, nil)
t.equal(type(message), "string")

local plain = assert(io.open(path, "w"))
assert(plain:write("return 6 * 7\n"))
assert(plain:close())
t.equal(dofile(path), 42)
t.truth(os.remove(path))

-- load/loadfile 可注入独立 _ENV；dofile 则直接使用调用环境且不提供 mode/env 参数。
t.done()
