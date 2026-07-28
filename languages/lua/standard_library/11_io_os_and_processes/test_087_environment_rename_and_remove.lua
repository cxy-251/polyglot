-- polyglot-covers: lua.os.environment_and_files

local t = require("support.assertions")
local source = t.temp_path("source.txt")
local destination = t.temp_path("destination.txt")
local writer = assert(io.open(source, "w"))
assert(writer:write("payload"))
assert(writer:close())

t.equal(os.getenv("TZ"), "UTC")
t.equal(os.getenv("POLYGLOT_LUA_TEST_TMP"), assert(os.getenv("TMPDIR")))
t.truth(os.rename(source, destination))

local reader = assert(io.open(destination, "r"))
t.equal(reader:read("a"), "payload")
t.truth(reader:close())
t.truth(os.remove(destination))

local removed, message = os.remove(destination)
t.equal(removed, nil)
t.equal(type(message), "string")

t.done()
