-- polyglot-covers: lua.modules.loadfile_and_dofile

local t = require("support.assertions")
local path = t.temp_path("chunk.lua")
local file = assert(io.open(path, "w"))
assert(file:write("local value = ...; return value * 2, _ENV.marker\n"))
assert(file:close())

local environment = {marker = "custom"}
local loaded = assert(loadfile(path, "t", environment))
local result, marker = loaded(21)
t.equal(result, 42)
t.equal(marker, "custom")

local plain = assert(io.open(path, "w"))
assert(plain:write("return 6 * 7\n"))
assert(plain:close())
t.equal(dofile(path), 42)
t.truth(os.remove(path))

t.done()
